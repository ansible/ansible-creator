"""Application configuration class for ansible-creator."""

from __future__ import annotations

import re

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ansible_creator.constants import MIN_COLLECTION_NAME_LEN
from ansible_creator.exceptions import CreatorError
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
        init_path: The path to initialize the project.
        project: The type of project to scaffold.
        scm_org: The SCM organization for the project.
        scm_project: The SCM project for the project.
        collection_name: The name of the collection.
        namespace: The namespace for the collection.
    """

    creator_version: str
    output: Output
    subcommand: str

    collection: str = ""
    force: bool = False
    init_path: str | Path = "./"
    project: str = ""
    scm_org: str | None = None
    scm_project: str | None = None

    # TO-DO: Add instance variables for other 'create' and 'sample'

    collection_name: str | None = None
    namespace: str = ""

    def __post_init__(self: Config) -> None:
        """Post process config values.

        Raises:
            CreatorError: When required values are missing or invalid.
        """
        # Validation for: ansible-creator init
        if not self.collection and self.project == "collection":
            msg = "The argument 'collection' is required when scaffolding a collection."
            raise CreatorError(msg)

        # Validation for: ansible-creator init --project=ansible-project
        if self.project == "ansible-project" and (self.scm_org is None or self.scm_project is None):
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
            msg = "Collection name has no effect when project is set to ansible-project."
            self.output.warning(msg)

        # Validation for collection name according to Ansible requirements
        if self.collection:
            fqcn = self.collection.split(".", maxsplit=1)
            name_filter = re.compile(r"^(?!_)[a-z0-9_]+$")

            if not name_filter.match(fqcn[0]) or not name_filter.match(fqcn[-1]):
                msg = (
                    "Collection name can only contain lower case letters, underscores, and numbers"
                    " and cannot begin with an underscore."
                )
                raise CreatorError(msg)

            if len(fqcn[0]) <= MIN_COLLECTION_NAME_LEN or len(fqcn[-1]) <= MIN_COLLECTION_NAME_LEN:
                msg = "Collection namespace and name must be longer than 2 characters."
                raise CreatorError(msg)

            object.__setattr__(self, "namespace", fqcn[0])
            object.__setattr__(self, "collection_name", fqcn[-1])

        if isinstance(self.init_path, str):
            object.__setattr__(self, "init_path", expand_path(self.init_path))
