from __future__ import annotations
from dataclasses import InitVar, dataclass, field
import json
import logging
import os
import sys
from typing import Any
from ghrepo import GHRepo
import requests
from .config import Config
from .versions import Bump

log = logging.getLogger(__name__)

GITHUB_API_URL = os.environ.get("GITHUB_API_URL", "https://api.github.com")

GRAPHQL_API_URL = os.environ.get("GITHUB_GRAPHQL_URL", "https://api.github.com/graphql")

PR_INFO_QUERY = (
    "query(\n"
    "  $repo_owner: String!,\n"
    "  $repo_name: String!,\n"
    "  $prnum: Int!,\n"
    "  $closing_cursor: String,\n"
    "  $label_cursor: String\n"
    ") {\n"
    "  repository(owner: $repo_owner, name: $repo_name) {\n"
    "    pullRequest(number: $prnum) {\n"
    "      title\n"
    "      number\n"
    "      url\n"
    "      author {\n"
    "        login\n"
    "        url\n"
    "      }\n"
    "      closingIssuesReferences(\n"
    "        first: 50,\n"
    "        orderBy: {field: CREATED_AT, direction:ASC},\n"
    "        after: $closing_cursor\n"
    "      ) {\n"
    "        nodes {\n"
    "          number\n"
    "          url\n"
    "        }\n"
    "        pageInfo {\n"
    "          endCursor\n"
    "          hasNextPage\n"
    "        }\n"
    "      }\n"
    "      labels(first: 50, after: $label_cursor) {\n"
    "        nodes {\n"
    "          name\n"
    "        }\n"
    "        pageInfo {\n"
    "          endCursor\n"
    "          hasNextPage\n"
    "        }\n"
    "      }\n"
    "    }\n"
    "  }\n"
    "}\n"
)


@dataclass
class Client:
    repo: GHRepo
    token: InitVar[str]
    session: requests.Session = field(init=False)

    def __post_init__(self, token: str) -> None:
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"bearer {token}"

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.session.close()

    def get_pr_info(self, prnum: int) -> PullRequest:
        variables = {
            "repo_owner": self.repo.owner,
            "repo_name": self.repo.name,
            "prnum": prnum,
            "closing_cursor": None,
            "label_cursor": None,
        }
        closed_issues: list[str] = []
        labels: set[str] = set()
        # We need to loop in order to get all pages of closed issues & labels.
        # The other PR details will be the same in every response, so we just
        # grab the last set of details once the pagination is done.
        while True:
            r = self.session.post(
                GRAPHQL_API_URL, json={"query": PR_INFO_QUERY, "variables": variables}
            )
            r.raise_for_status()
            resp = r.json()
            if resp.get("errors"):
                sys.exit(
                    "GraphQL API Error:\n" + json.dumps(resp, sort_keys=True, indent=4)
                )
            data = resp["data"]["repository"]["pullRequest"]
            issue_page = data["closingIssuesReferences"]
            closed_issues.extend(Issue(**n) for n in issue_page["nodes"])
            variables["closing_cursor"] = issue_page["pageInfo"]["endCursor"]
            label_page = data["labels"]
            labels.update([n["name"] for n in label_page["nodes"]])
            variables["label_cursor"] = label_page["pageInfo"]["endCursor"]
            if (
                not issue_page["pageInfo"]["hasNextPage"]
                and not label_page["pageInfo"]["hasNextPage"]
            ):
                return PullRequest(
                    title=data["title"],
                    number=data["number"],
                    url=data["url"],
                    author=Actor(**data["author"]),
                    closed_issues=closed_issues,
                    labels=labels,
                )

    def make_release_comments(self, release_tag: str, prnum: int) -> None:
        release_link = (
            f"[`{release_tag}`](https://github.com/{self.repo.owner}"
            f"/{self.repo.name}/releases/tag/{release_tag})"
        )
        log.info("Commenting on PR #%d", prnum)
        self.comment_on_issueoid(prnum, f"PR released in {release_link}")
        pr = self.get_pr_info(prnum)
        for issue in pr.closed_issues:
            log.info("Commenting on issue #%d", issue.number)
            self.comment_on_issueoid(issue.number, f"Issue fixed in {release_link}")

    def comment_on_issueoid(self, num: int, body: str) -> None:
        r = self.session.post(
            f"{GITHUB_API_URL}/repos/{self.repo.owner}/{self.repo.name}/issues/{num}/comments",
            json={"body": body},
            headers={"Accept": "application/vnd.github+json"},
        )
        r.raise_for_status()


@dataclass
class Actor:
    login: str
    url: str

    def as_link(self) -> str:
        return f"[@{self.login}]({self.url})"


@dataclass
class Issue:
    number: int
    url: str

    def as_link(self) -> str:
        return f"[#{self.number}]({self.url})"


@dataclass
class PullRequest:
    title: str
    number: int
    url: str
    author: Actor
    closed_issues: list[Issue]
    labels: set[str]

    def category(self, cfg: Config) -> str:
        for cat in cfg.categories:
            if cat.label is not None and cat.label in self.labels:
                return cat.name
        sys.exit("Pull request lacks semver labels")

    def get_bump(self, cfg: Config) -> Bump:
        return max(
            (
                cat.bump
                for cat in cfg.categories
                if cat.label is not None and cat.label in self.labels
            ),
            default=Bump.PATCH,
        )

    def as_link(self) -> str:
        return f"[PR #{self.number}]({self.url})"

    def as_snippet(self, cfg: Config) -> str:
        item = f"- {self.title.strip()}"
        if not item.endswith((".", "!", "?")):
            item += "."
        item += "  "
        if self.closed_issues:
            item += (
                "Fixes " + ", ".join(i.as_link() for i in self.closed_issues) + " via "
            )
        item += f"{self.as_link()} (by {self.author.as_link()})"
        return f"### {self.category(cfg)}\n\n{item}\n"
