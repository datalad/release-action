from __future__ import annotations
from dataclasses import dataclass
import os
from typing import IO
import click
from .client import Client
from .config import Config


@dataclass
class DRA:
    config: Config
    client: Client


@click.group()
@click.option(
    "-c", "--config", type=click.File("r"), default=".datalad-release-action.yaml"
)
@click.pass_context
def main(ctx: click.Context, config: IO[str]) -> None:
    cfg = Config.load_yaml(config)
    try:
        token = os.environ["GITHUB_TOKEN"]
    except KeyError:
        raise click.UsageError("GITHUB_TOKEN envvar not set")
    client = ctx.with_resource(Client(token))
    ctx.obj = DRA(config=cfg, client=client)


@main.command()
@click.argument("repo_owner")
@click.argument("repo_name")
@click.argument("prnum", type=int)
@click.pass_obj
def add_changelog_snippet(
    dra: DRA, repo_owner: str, repo_name: str, prnum: int
) -> None:
    pr = dra.client.get_pr_info(
        repo_owner=repo_owner,
        repo_name=repo_name,
        prnum=prnum,
    )
    dra.config.snippets_dir.mkdir(parents=True, exist_ok=True)
    outfile = dra.config.snippets_dir / f"pr-{prnum}.md"
    outfile.write_text(pr.as_snippet(dra.config))
    print("Changelog snippet saved to", outfile)


if __name__ == "__main__":
    main()
