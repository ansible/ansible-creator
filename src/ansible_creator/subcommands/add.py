"""Definitions for ansible-creator add action."""

from __future__ import annotations

import uuid

from pathlib import Path
from typing import TYPE_CHECKING

from ansible_creator.exceptions import CreatorError
from ansible_creator.templar import Templar
from ansible_creator.types import TemplateData
from ansible_creator.utils import Copier, Walker, ask_yes_no


if TYPE_CHECKING:
    from ansible_creator.config import Config
    from ansible_creator.output import Output


class Add:
    """Class to handle the add subcommand."""

    def __init__(
        self,
        config: Config,
    ) -> None:
        """Initialize the add action.

        Args:
            config: App configuration object.
        """
        self._resource_type: str = config.resource_type
        self._resource_id: str = f"common.{self._resource_type}"
        self._add_path: Path = Path(config.path)
        self._force = config.force
        self._overwrite = config.overwrite
        self._no_overwrite = config.no_overwrite
        self._creator_version = config.creator_version
        self._project = config.project
        self.output: Output = config.output
        self.templar = Templar()

    def run(self) -> None:
        """Start scaffolding the resource file."""
        self._check_add_path()
        self.output.debug(msg=f"final collection path set to {self._add_path}")

        self._scaffold()

    def _check_add_path(self) -> None:
        """Validate the provided add path.

        Raises:
            CreatorError: If the add path does not exist.
        """
        if not self._add_path.exists():
            msg = f"The path {self._add_path} does not exist. Please provide an existing directory."
            raise CreatorError(msg)

    def unique_name_in_devfile(self) -> str:
        """Use project specific name in devfile.

        Returns:
            Unique name entry.
        """
        final_name = ".".join(self._add_path.parts[-2:])
        final_uuid = str(uuid.uuid4())[:8]
        return f"{final_name}-{final_uuid}"

    def _scaffold(self) -> None:
        """Scaffold the specified resource file based on the resource type.

        Raises:
            CreatorError: If unsupported resource type is given.
        """
        self.output.debug(f"Started copying {self._project} resource to destination")

        # Call the appropriate scaffolding function based on the resource type
        if self._resource_type == "devfile":
            template_data = self._get_devfile_template_data()

        else:
            msg = f"Unsupported resource type: {self._resource_type}"
            raise CreatorError(msg)

        self._perform_scaffold(template_data)

    def _perform_scaffold(self, template_data: TemplateData) -> None:
        """Perform the actual scaffolding process using the provided template data.

        Args:
            template_data: TemplateData

        Raises:
            CreatorError: If there are conflicts and overwriting is not allowed, or if the
                      destination directory contains files that will be overwritten.
        """
        walker = Walker(
            resources=(f"common.{self._resource_type}",),
            resource_id=self._resource_id,
            dest=self._add_path,
            output=self.output,
            template_data=template_data,
            templar=self.templar,
        )
        paths = walker.collect_paths()
        copier = Copier(output=self.output)

        if self._no_overwrite:
            msg = "The flag `--no-overwrite` restricts overwriting."
            if paths.has_conflicts():
                msg += (
                    "\nThe destination directory contains files that can be overwritten."
                    "\nPlease re-run ansible-creator with --overwrite to continue."
                )
            raise CreatorError(msg)

        if not paths.has_conflicts() or self._force or self._overwrite:
            copier.copy_containers(paths)
            self.output.note(f"Resource added to {self._add_path}")
            return

        if not self._overwrite:
            question = (
                "Files in the destination directory will be overwritten. Do you want to proceed?"
            )
            if ask_yes_no(question):
                copier.copy_containers(paths)
            else:
                msg = (
                    "The destination directory contains files that will be overwritten."
                    " Please re-run ansible-creator with --overwrite to continue."
                )
                raise CreatorError(msg)

        self.output.note(f"Resource added to {self._add_path}")

    def _get_devfile_template_data(self) -> TemplateData:
        """Get the template data for devfile resources.

        Returns:
            TemplateData: Data required for templating the devfile resource.
        """
        return TemplateData(
            resource_type=self._resource_type,
            creator_version=self._creator_version,
            dev_file_name=self.unique_name_in_devfile(),
        )
