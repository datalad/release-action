from __future__ import annotations
from dataclasses import dataclass
import logging
import os
import re
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
    pr = dra.client.get_pr_info(prnum)
    dra.config.fragment_directory.mkdir(parents=True, exist_ok=True)
    outfile = dra.config.fragment_directory / f"pr-{prnum}.md"
    outfile.write_text(pr.as_snippet(dra.config))
    log.info("Changelog snippet saved to %s", outfile)


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
    print(f"::set-output name=new-version::{next_version}")


if __name__ == "__main__":
    main()
