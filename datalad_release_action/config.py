from __future__ import annotations
from pathlib import Path
from typing import IO, List, Optional
from pydantic import BaseModel, Field
from ruamel.yaml import YAML
from .versions import Bump


class GitAuthor(BaseModel):
    name: str = "DataLad Bot"
    email: str = "bot@datalad.org"


class Category(BaseModel):
    name: str
    bump: Bump = Bump.PATCH
    label: Optional[str] = None


class Config(BaseModel):
    git_author: GitAuthor = Field(default_factory=GitAuthor)

    ### apt_depends
    ### pip_depends
    ### pre_tag

    snippets_dir: Path = Path("changelog.d")
    categories: List[Category]

    @classmethod
    def load_yaml(cls, infile: IO[str]) -> Config:
        return cls.parse_obj(YAML(typ="safe").load(infile))
