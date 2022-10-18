from __future__ import annotations
from pathlib import Path
from typing import IO, List, Optional
from pydantic import BaseModel, Field
from ruamel.yaml import YAML
from .versions import Bump


class Category(BaseModel):
    name: str
    bump: Bump = Bump.PATCH
    label: Optional[str] = None
    label_color: Optional[str] = Field(
        None, alias="label-color", regex=r"^[0-9A-Fa-f]{6}$"
    )
    label_description: Optional[str] = Field(None, alias="label-description")

    def get_label(self) -> Optional[Label]:
        if self.label is not None:
            return Label(
                name=self.label,
                color=self.label_color,
                description=self.label_description,
            )
        else:
            return None


class Label(BaseModel):
    name: str
    color: Optional[str] = Field(None, regex=r"^[0-9A-Fa-f]{6}$")
    description: Optional[str] = None


class Config(BaseModel):
    fragment_directory: Path = Path("changelog.d", alias="fragment-directory")
    categories: List[Category]
    extra_labels: List[Label] = Field(default_factory=list, alias="extra-labels")

    @classmethod
    def load_yaml(cls, infile: IO[str]) -> Config:
        return cls.parse_obj(YAML(typ="safe").load(infile))
