from __future__ import annotations
from dataclasses import dataclass
import logging
import os
import re
from typing import IO
import click
from ghrepo import GHRepo
from .client import Client
from .config import Config

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
    dra.config.snippets_dir.mkdir(parents=True, exist_ok=True)
    outfile = dra.config.snippets_dir / f"pr-{prnum}.md"
    outfile.write_text(pr.as_snippet(dra.config))
    log.info("Changelog snippet saved to %s", outfile)


@main.command()
@click.argument("release_tag")
@click.pass_obj
def release(dra: DRA, release_tag: str) -> None:
    for p in dra.config.snippets_dir.iterdir():
        if p.is_file() and p.suffix == ".md":
            log.info("Processing snippet %s", p)
            m = re.fullmatch(r"pr-(\d+)(?:\.[a-z]+)?", p.name)
            if m:
                dra.client.make_release_comments(release_tag, int(m[1]))
            else:
                log.warning("Cannot extract PR number from path %r", str(p))


if __name__ == "__main__":
    main()
