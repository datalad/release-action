from __future__ import annotations
from dataclasses import dataclass
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import IO
import click
from ghrepo import GHRepo
from .client import Client, PullRequest
from .config import Config
from .versions import Bump, bump_version, get_highest_tag_version

log = logging.getLogger(__name__)


@dataclass
class DRA:
    config: Config
    client: Client


@click.group()
@click.option(
    "-c", "--config", type=click.File("r"), default=".datalad-release-action.yaml"
)
@click.argument("repo", type=GHRepo.parse)
@click.pass_context
def main(ctx: click.Context, config: IO[str], repo: GHRepo) -> None:
    logging.basicConfig(
        format="[%(levelname)-8s] %(message)s",
        level=logging.INFO,
    )
    cfg = Config.load_yaml(config)
    try:
        token = os.environ["GITHUB_TOKEN"]
    except KeyError:
        raise click.UsageError("GITHUB_TOKEN envvar not set")
    client = ctx.with_resource(Client(token=token, repo=repo))
    ctx.obj = DRA(config=cfg, client=client)


@main.command()
@click.argument("prnum", type=int)
@click.pass_obj
def add_changelog_snippet(dra: DRA, prnum: int) -> None:
    fragdir = dra.config.fragment_directory
    pr_snippet = fragdir / f"pr-{prnum}.md"
    added_snippets = [
        file
        for file in map(Path, dra.client.get_pr_added_files(prnum))
        if file.parent == fragdir and re.fullmatch(r".*[-_].*\.md", file.name)
    ]
    if len(added_snippets) == 0:
        log.info("No pre-existing changelog snippets found in PR; generating one")
        pr = dra.client.get_pr_info(prnum)
        fragdir.mkdir(parents=True, exist_ok=True)
        pr_snippet.write_text(pr.as_snippet(dra.config))
        log.info("Changelog snippet saved to %s", pr_snippet)
        subprocess.run(["git", "add", "--", str(pr_snippet)], check=True)
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                f"[release-action] Autogenerate changelog snippet for PR {prnum}",
            ],
            check=True,
        )
    elif pr_snippet in added_snippets:
        log.info("Changelog snippet %s already present; doing nothing", pr_snippet)
    elif len(added_snippets) == 1:
        log.info("Renaming changelog snippet %s to %s", added_snippets[0], pr_snippet)
        subprocess.run(
            ["git", "mv", "--", str(added_snippets[0]), str(pr_snippet)], check=True
        )
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                f"[release-action] Rename changelog snippet for PR {prnum}",
            ],
            check=True,
        )
    else:
        log.error(
            "Multiple changelog snippets found in PR, none of which is named %r: %s",
            str(pr_snippet),
            ", ".join(map(str, added_snippets)),
        )
        sys.exit(1)


@main.command()
@click.pass_obj
def release(dra: DRA) -> None:
    bump = Bump.PATCH
    prs: list[PullRequest] = []
    for p in dra.config.fragment_directory.iterdir():
        if p.is_file() and p.suffix in (".md", ".rst"):
            log.info("Processing snippet %s", p)
            m = re.fullmatch(r"pr-(\d+)(?:\.[a-z]+)?", p.name)
            if m:
                prnum = int(m[1])
                log.info("Fetching data for PR #%d", prnum)
                pr = dra.client.get_pr_info(prnum)
                b = pr.get_bump(dra.config)
                log.info("PR version bump level: %s", b.value)
                if b > bump:
                    bump = b
                prs.append(pr)
            else:
                log.warning("Cannot extract PR number from path %r", str(p))
    log.info("Version bump level for this release: %s", bump.value)
    prev_version = get_highest_tag_version()
    log.info("Previous released version: %s", prev_version)
    next_version = bump_version(prev_version, bump)
    log.info("New version: %s", next_version)
    for pr in prs:
        dra.client.make_release_comments(next_version, pr.number)
    with open(os.environ["GITHUB_OUTPUT"], "a") as fp:
        print(f"new-version={next_version}", file=fp)


if __name__ == "__main__":
    main()
