"""Definitions for ansible-creator add action."""

from __future__ import annotations

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

    common_resources = ("common.devfile",)

    def __init__(
        self: Add,
        config: Config,
    ) -> None:
        """Initialize the add action.

        Args:
            config: App configuration object.
        """

        self._resource_type: str = config.resource_type
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
        """Validate the provided add path."""
        if not self._add_path.exists():
            raise CreatorError(
                f"The path {self._add_path} does not exist. Please provide an existing directory.",
            )

    def _scaffold(self) -> None:
        """Scaffold the specified resource file."""
        self.output.debug(f"Started copying {self._project} resource to destination")

        # Set up template data
        template_data = TemplateData(
            resource_type=self._resource_type,
            creator_version=self._creator_version,
        )

        # Initialize Walker and Copier for file operations

        walker = Walker(
            resources=self.common_resources,
            resource_id="common.devfile",
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
            question = "Some files in the destination directory may be overwritten. Do you want to proceed?"
            if ask_yes_no(question):
                copier.copy_containers(paths)
            else:
                msg = (
                    "The destination directory contains files that will be overwritten."
                    " Please re-run ansible-creator with --overwrite to continue."
                )
                raise CreatorError(msg)

        self.output.note(f"Resource added to {self._add_path}")
