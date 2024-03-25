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
    # These are the same thing but init_path is a terrible name for non-init
    # commands
    init_path: str = "./"
    collection_path: str = "./"
    branch_name: str = "main"

    # TO-DO: Add instance variables for other 'create' and 'sample'

    collection_name: str = field(init=False)
    namespace: str = field(init=False)

    def __post_init__(self: Config) -> None:
        """Post process config values."""
        if self.collection:
            fqcn = self.collection.split(".", maxsplit=1)
            object.__setattr__(self, "namespace", fqcn[0])
            object.__setattr__(self, "collection_name", fqcn[-1])

        object.__setattr__(self, "init_path", expand_path(self.init_path))
