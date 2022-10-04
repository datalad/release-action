from __future__ import annotations
from pathlib import Path
from typing import IO, List, Optional
from pydantic import BaseModel
from ruamel.yaml import YAML
from .versions import Bump


class Category(BaseModel):
    name: str
    bump: Bump = Bump.PATCH
    label: Optional[str] = None


class Config(BaseModel):
    snippets_dir: Path = Path("changelog.d")
    categories: List[Category]

    @classmethod
    def load_yaml(cls, infile: IO[str]) -> Config:
        return cls.parse_obj(YAML(typ="safe").load(infile))
