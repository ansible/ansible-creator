"""Application configuration class for ansible-creator."""

from __future__ import annotations

from dataclasses import dataclass, field

from ansible_creator.utils import expand_path


@dataclass(frozen=True)
class Config:
    """The application configuration for ansible-creator."""

    creator_version: str
    json: bool
    log_append: bool
    log_file: str
    log_level: str
    no_ansi: bool
    subcommand: str
    verbose: int

    collection: str = ""
    force: bool = False
    init_path: str = "./"
    file_path: str = "./content.yaml"

    # TO-DO: Add instance variables for 'sample'

    collection_name: str = field(init=False)
    namespace: str = field(init=False)

    def __post_init__(self: Config) -> None:
        """Post process config values."""
        if self.collection:
            fqcn = self.collection.split(".", maxsplit=1)
            object.__setattr__(self, "namespace", fqcn[0])
            object.__setattr__(self, "collection_name", fqcn[-1])

        object.__setattr__(self, "init_path", expand_path(self.init_path))


@dataclass(frozen=True)
class ScaffolderConfig:
    """The configuration for Scaffolder classes."""

    collection_path: str
    collection_name: str
    namespace: str
    name: str
    type: str  # noqa: A003
    docstring: str = ""

    def __post_init__(self: ScaffolderConfig) -> None:
        """Post process config values."""
        object.__setattr__(
            self,
            "collection_path",
            f"{expand_path(self.collection_path)}/{self.namespace}/{self.collection_name}",
        )
        if self.docstring:
            object.__setattr__(
                self,
                "docstring",
                expand_path(self.docstring),
            )
