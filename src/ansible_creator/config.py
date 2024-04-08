"""Application configuration class for ansible-creator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ansible_creator.exceptions import CreatorError
from ansible_creator.utils import expand_path


if TYPE_CHECKING:
    from ansible_creator.output import Output


@dataclass(frozen=True)
class Config:
    """The application configuration for ansible-creator."""

    creator_version: str
    output: Output
    subcommand: str

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
        # Validation for: ansible-creator init
        if not self.collection and self.project == "collection":
            msg = "The argument 'collection' is required when scaffolding a collection."
            raise CreatorError(msg)

        # Validation for: ansible-creator init --project=ansible-project
        if self.project == "ansible-project" and (
            self.scm_org is None or self.scm_project is None
        ):
            msg = (
                "Parameters 'scm-org' and 'scm-project' are required when "
                "scaffolding an ansible-project."
            )
            raise CreatorError(msg)

        # Validation for: ansible-creator init testorg.testname --scm-org=weather
        # --scm-project=demo --project=collection
        if (self.scm_org or self.scm_project) and self.project != "ansible-project":
            msg = (
                "The parameters 'scm-org' and 'scm-project' have no effect when"
                " project is not set to ansible-project."
            )
            self.output.warning(msg)

        # Validation for: ansible-creator init testorg.testname --project=ansible-project
        # --scm-org weather --scm-project demo
        if self.collection and self.project != "collection":
            msg = (
                "Collection name has no effect when project is set to ansible-project."
            )
            self.output.warning(msg)

        if self.collection:
            fqcn = self.collection.split(".", maxsplit=1)
            object.__setattr__(self, "namespace", fqcn[0])
            object.__setattr__(self, "collection_name", fqcn[-1])

        object.__setattr__(self, "init_path", expand_path(self.init_path))
