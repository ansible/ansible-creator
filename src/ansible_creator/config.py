"""Application configuration class for ansible-creator."""

from __future__ import annotations

from dataclasses import dataclass

from ansible_creator.exceptions import CreatorError
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
    project: str = ""
    scm_org: str = ""
    scm_project: str = ""

    # TO-DO: Add instance variables for other 'create' and 'sample'

    collection_name: str = ""
    namespace: str = ""

    def __post_init__(self: Config) -> None:
        """Post process config values."""
        # Show CreatorError if the required collection name is not provided
        if not self.collection and self.project == "collection":
            msg = "The collection name is required when scaffolding a collection."
            raise CreatorError(msg)

        if self.project == "ansible-project" and (
            self.scm_org is None or self.scm_project is None
        ):
            msg = (
                "Required parameters scm-org and scm-project to scaffold"
                " playbook adjacent collection within ansible-project."
            )
            raise CreatorError(msg)

        if self.collection:
            fqcn = self.collection.split(".", maxsplit=1)
            object.__setattr__(self, "namespace", fqcn[0])
            object.__setattr__(self, "collection_name", fqcn[-1])

        object.__setattr__(self, "init_path", expand_path(self.init_path))
