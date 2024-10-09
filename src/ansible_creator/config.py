"""Application configuration class for ansible-creator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ansible_creator.utils import expand_path


if TYPE_CHECKING:
    from pathlib import Path

    from ansible_creator.output import Output


@dataclass(frozen=True)
class Config:
    """The application configuration for ansible-creator.

    Attributes:
        creator_version: The version of ansible-creator.
        output: The output object to use for logging.
        subcommand: The subcommand to execute.
        collection: The collection name to scaffold.
        force: Whether to overwrite existing files.
        overwrite: To overwrite files in an existing directory.
        no_overwrite: To not overwrite files in an existing directory.
        init_path: The path to initialize the project.
        project: The type of project to scaffold.
        collection_name: The name of the collection.
        namespace: The namespace for the collection.
    """

    creator_version: str
    output: Output
    subcommand: str

    collection: str = ""
    force: bool = False
    overwrite: bool = False
    no_overwrite: bool = False
    init_path: str | Path = "./"
    project: str = ""
    collection_name: str | None = None
    namespace: str = ""

    def __post_init__(self: Config) -> None:
        """Post process config values."""
        if self.collection:
            fqcn = self.collection.split(".", maxsplit=1)
            object.__setattr__(self, "namespace", fqcn[0])
            object.__setattr__(self, "collection_name", fqcn[-1])

        if isinstance(self.init_path, str):
            object.__setattr__(self, "init_path", expand_path(self.init_path))
