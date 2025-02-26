"""Definitions for ansible-creator add action."""

from __future__ import annotations

import uuid

from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from ansible_creator.constants import GLOBAL_TEMPLATE_VARS
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
        self._plugin_type: str = config.plugin_type
        self._resource_id: str = f"common.{self._resource_type}"
        self._plugin_id: str = f"collection_project.plugins.{self._plugin_type}"
        self._plugin_name: str = config.plugin_name
        self._add_path: Path = Path(config.path)
        self._force = config.force
        self._overwrite = config.overwrite
        self._no_overwrite = config.no_overwrite
        self._creator_version = config.creator_version
        self._project = config.project
        self._dev_container_image = config.image
        self.output: Output = config.output
        self.templar = Templar()

    def run(self) -> None:
        """Start scaffolding the resource file."""
        self._check_path_exists()
        self.output.debug(msg=f"final collection path set to {self._add_path}")
        if self._resource_type:
            self._resource_scaffold()
        elif self._plugin_type:
            self._check_collection_path()
            plugin_path = self._add_path / "plugins" / self._plugin_type
            plugin_path.mkdir(parents=True, exist_ok=True)
            self._plugin_scaffold(plugin_path)

    def _check_path_exists(self) -> None:
        """Validate the provided add path.

        Raises:
            CreatorError: If the add path does not exist.
        """
        if not self._add_path.exists():
            msg = f"The path {self._add_path} does not exist. Please provide an existing directory."
            raise CreatorError(msg)

    def _check_collection_path(self) -> None:
        """Validates if the provided path is an Ansible collection.

        Raises:
            CreatorError: If the path is not a collection path.
        """
        galaxy_file_path = self._add_path / "galaxy.yml"
        if not Path.is_file(galaxy_file_path):
            msg = (
                f"The path {self._add_path} is not a valid Ansible collection path. "
                "Please provide the root path of a valid ansible collection."
            )
            raise CreatorError(msg)

    def unique_name_in_devfile(self) -> str:
        """Use project specific name in devfile.

        Returns:
            Unique name entry.
        """
        final_name = ".".join(self._add_path.parts[-2:])
        final_uuid = str(uuid.uuid4())[:8]
        return f"{final_name}-{final_uuid}"

    def update_galaxy_dependency(self) -> None:
        """Update galaxy.yml file with the required dependency."""
        galaxy_file = self._add_path / "galaxy.yml"

        # Load the galaxy.yml file
        with galaxy_file.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        # Ensure the dependencies key exists
        if "dependencies" not in data:
            data["dependencies"] = {"ansible.utils": "*"}

        # Empty dependencies key or dependencies key without ansible.utils
        elif not data["dependencies"] or "ansible.utils" not in data["dependencies"]:
            data["dependencies"]["ansible.utils"] = "*"

        # Save the updated YAML back to the file
        with galaxy_file.open("w", encoding="utf-8") as file:
            yaml.dump(data, file, sort_keys=False)

    def _resource_scaffold(self) -> None:
        """Scaffold the specified resource file based on the resource type.

        Raises:
            CreatorError: If unsupported resource type is given.
        """
        self.output.debug(f"Started adding {self._resource_type} to destination")

        # Call the appropriate scaffolding function based on the resource type
        if self._resource_type == "devfile":
            template_data = self._get_devfile_template_data()
        elif self._resource_type == "devcontainer":
            template_data = self._get_devcontainer_template_data()
        elif self._resource_type == "execution-environment":
            template_data = self._get_ee_template_data()
        else:
            msg = f"Unsupported resource type: {self._resource_type}"
            raise CreatorError(msg)

        self._perform_resource_scaffold(template_data)

    def _perform_resource_scaffold(self, template_data: TemplateData) -> None:
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

        if self._no_overwrite and paths.has_conflicts():
            msg = (
                "The flag `--no-overwrite` restricts overwriting."
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

    def _plugin_scaffold(self, plugin_path: Path) -> None:
        """Scaffold the specified plugin file based on the plugin type.

        Args:
            plugin_path: Path where the plugin will be scaffolded.

        Raises:
            CreatorError: If unsupported plugin type is given.
        """
        self.output.debug(f"Started adding {self._plugin_type} plugin to destination")

        # Call the appropriate scaffolding function based on the plugin type
        if self._plugin_type == "action":
            self.update_galaxy_dependency()
            template_data = self._get_plugin_template_data()
            self._perform_action_plugin_scaffold(template_data, plugin_path)

        elif self._plugin_type == "filter":
            template_data = self._get_plugin_template_data()
            self._perform_filter_plugin_scaffold(template_data, plugin_path)

        elif self._plugin_type == "lookup":
            template_data = self._get_plugin_template_data()
            self._perform_lookup_plugin_scaffold(template_data, plugin_path)

        elif self._plugin_type == "module":
            template_data = self._get_plugin_template_data()
            plugin_path = self._add_path / "plugins" / "sample_module"
            plugin_path.mkdir(parents=True, exist_ok=True)
            self._perform_module_plugin_scaffold(template_data, plugin_path)
        else:
            msg = f"Unsupported plugin type: {self._plugin_type}"
            raise CreatorError(msg)

    def _perform_action_plugin_scaffold(
        self,
        template_data: TemplateData,
        plugin_path: Path,
    ) -> None:
        resources = (
            f"collection_project.plugins.{self._plugin_type}",
            "collection_project.plugins.modules",
        )
        module_path = self._add_path / "plugins" / "modules"
        module_path.mkdir(parents=True, exist_ok=True)
        final_plugin_path = [plugin_path, module_path]
        self._perform_plugin_scaffold(resources, template_data, final_plugin_path)

    def _perform_filter_plugin_scaffold(
        self,
        template_data: TemplateData,
        plugin_path: Path,
    ) -> None:
        resources = (f"collection_project.plugins.{self._plugin_type}",)
        self._perform_plugin_scaffold(resources, template_data, plugin_path)

    def _perform_lookup_plugin_scaffold(
        self,
        template_data: TemplateData,
        plugin_path: Path,
    ) -> None:
        resources = (f"collection_project.plugins.{self._plugin_type}",)
        self._perform_plugin_scaffold(resources, template_data, plugin_path)

    def _perform_module_plugin_scaffold(
        self,
        template_data: TemplateData,
        plugin_path: Path,
    ) -> None:
        resources = ("collection_project.plugins.sample_module",)
        self._perform_plugin_scaffold(resources, template_data, plugin_path)

    def _perform_plugin_scaffold(
        self,
        resources: tuple[str, ...],
        template_data: TemplateData,
        plugin_path: Path | list[Path],
    ) -> None:
        """Perform the actual scaffolding process using the provided template data.

        Args:
            resources: Tuple of resources.
            template_data: TemplateData
            plugin_path: Path where the plugin will be scaffolded.

        Raises:
            CreatorError: If there are conflicts and overwriting is not allowed, or if the
                      destination directory contains files that will be overwritten.
        """
        walker = Walker(
            resources=resources,
            resource_id=self._plugin_id,
            dest=plugin_path,
            output=self.output,
            template_data=template_data,
            templar=self.templar,
        )
        paths = walker.collect_paths()
        copier = Copier(output=self.output)

        if self._no_overwrite and paths.has_conflicts():
            msg = (
                "The flag `--no-overwrite` restricts overwriting."
                "\nThe destination directory contains files that can be overwritten."
                "\nPlease re-run ansible-creator with --overwrite to continue."
            )
            raise CreatorError(msg)

        # This check is for action plugins (having module file as an additional path)
        if isinstance(plugin_path, list):
            plugin_path = plugin_path[0]

        if not paths.has_conflicts() or self._force or self._overwrite:
            copier.copy_containers(paths)
            self.output.note(f"{self._plugin_type.capitalize()} plugin added to {plugin_path}")
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

        self.output.note(f"{self._plugin_type.capitalize()} plugin added to {plugin_path}")

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

    def _get_devcontainer_template_data(self) -> TemplateData:
        """Get the template data for devcontainer resources.

        Returns:
            TemplateData: Data required for templating the devcontainer resource.
        """
        image_mapping = {
            "auto": GLOBAL_TEMPLATE_VARS["DEV_CONTAINER_IMAGE"],
            "upstream": GLOBAL_TEMPLATE_VARS["DEV_CONTAINER_UPSTREAM_IMAGE"],
            "aap": GLOBAL_TEMPLATE_VARS["DEV_CONTAINER_DOWNSTREAM_IMAGE"],
        }

        dev_container_image = image_mapping.get(
            self._dev_container_image,
            self._dev_container_image,
        )

        return TemplateData(
            resource_type=self._resource_type,
            creator_version=self._creator_version,
            dev_file_name=self.unique_name_in_devfile(),
            dev_container_image=dev_container_image,
        )

    def _get_plugin_template_data(self) -> TemplateData:
        """Get the template data for plugin.

        Returns:
            TemplateData: Data required for templating the plugin.
        """
        return TemplateData(
            plugin_type=self._plugin_type,
            plugin_name=self._plugin_name,
            creator_version=self._creator_version,
        )

    def _get_ee_template_data(self) -> TemplateData:
        """Get the template data for plugin.

        Returns:
            TemplateData: Data required for templating the plugin.
        """
        return TemplateData(
            resource_type=self._resource_type,
            creator_version=self._creator_version,
        )
