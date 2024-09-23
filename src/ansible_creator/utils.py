"""Re-usable utility functions used by this package."""

from __future__ import annotations

import copy
import os

from dataclasses import dataclass
from importlib import resources as impl_resources
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from ansible_creator.constants import SKIP_DIRS, SKIP_FILES_TYPES


if TYPE_CHECKING:
    from ansible_creator.compat import Traversable
    from ansible_creator.output import Output
    from ansible_creator.templar import Templar
    from ansible_creator.types import TemplateData


PATH_REPLACERS = {
    "project_org": "namespace",
    "project_repo": "collection_name",
}


@dataclass
class TermFeatures:
    """Terminal features.

    Attributes:
        color: Enable color output.
        links: Enable clickable links.
    """

    color: bool
    links: bool

    def any_enabled(self: TermFeatures) -> bool:
        """Return True if any features are enabled.

        Returns:
            bool: True if any features are enabled.
        """
        return any((self.color, self.links))


def expand_path(path: str) -> Path:
    """Resolve absolute path.

    Args:
        path: Path to expand.

    Returns:
        Expanded absolute path.
    """
    _path = Path(os.path.expandvars(path))
    _path = _path.expanduser()
    return _path.resolve()


@dataclass
class DestinationFile:
    """Container to hold information about a file to be copied.

    Attributes:
        source: The path of the original copy.
        dest: The path the file will be written to.
        template_data: A dictionary containing the customized data to render templates with.
    """

    source: Traversable
    dest: Path
    template_data: TemplateData

    def __str__(self) -> str:
        """Supports str() on DestinationFile.

        Returns:
            A string representation of the destination path.
        """
        return str(self.dest)

    @property
    def conflicts(self) -> bool:
        """Check for file conflicts.

        Returns:
            True if a conflict exists on the destination else False.
        """
        if not self.dest.exists():
            return False

        return not (self.dest.is_dir() and self.source.is_dir())

    @property
    def needs_templating(self) -> bool:
        """Check if templating is required.

        Returns:
            True if the file needs to be templated else False.
        """
        return self.source.name.endswith(".j2")

    def remove_existing(self) -> None:
        """Remove existing files or directories at destination path."""
        if self.dest.is_file():
            self.dest.unlink()
        elif self.dest.is_dir():
            self.dest.rmdir()


@dataclass
class Walker:
    """Configuration for the Walker class.

    Attributes:
        resources: List of resource containers to copy.
        resource_id: The id of the resource to copy.
        dest: The destination path to copy resources to.
        output: An instance of the Output class.
        template_data: A dictionary containing the original data to render templates with.
        resource_root: Root path for the resources.
        templar: An instance of the Templar class.
    """

    resources: tuple[str, ...]
    resource_id: str
    dest: Path
    output: Output
    template_data: TemplateData
    resource_root: str = "ansible_creator.resources"
    templar: Templar | None = None

    def _recursive_walk(
        self,
        root: Traversable,
        resource: str,
        template_data: TemplateData,
    ) -> list[DestinationFile]:
        """Recursively traverses a resource container looking for content to copy.

        Args:
            root: A traversable object representing root of the container to copy.
            resource: The resource being scanned.
            template_data: A dictionary containing current data to render templates with.

        Returns:
            A list of paths to be written to.
        """
        self.output.debug(msg=f"current root set to {root}")

        file_list = []
        for obj in root.iterdir():
            file_list.extend(
                self.each_obj(
                    obj,
                    resource=resource,
                    template_data=template_data,
                ),
            )
        return file_list

    def each_obj(
        self,
        obj: Traversable,
        resource: str,
        template_data: TemplateData,
    ) -> list[DestinationFile]:
        """Recursively traverses a resource container and copies content to destination.

        Args:
            obj: A traversable object representing the root of the container to copy.
            resource: The resource to consult for path names.
            template_data: A dictionary containing current data to render templates with.

        Returns:
            A list of paths.
        """
        # resource names may have a . but directories use / in the path
        dest_name = str(obj).split(
            resource.replace(".", "/") + "/",
            maxsplit=1,
        )[-1]
        # replace placeholders in destination path with real values
        for key, val in PATH_REPLACERS.items():
            if key in dest_name:
                repl_val = getattr(template_data, val)
                dest_name = dest_name.replace(key, repl_val)
        dest_name = dest_name.removesuffix(".j2")

        dest_path = DestinationFile(
            dest=self.dest / dest_name,
            source=obj,
            template_data=template_data,
        )
        self.output.debug(f"Working on {dest_path}")

        if dest_path.conflicts:
            if dest_path.dest.is_dir():
                self.output.warning(f"{dest_path} already exists and is a directory!")
            elif obj.is_dir():
                self.output.warning(f"{dest_path} already exists and is a file!")
            else:
                self.output.warning(f"{dest_path} will be overwritten!")

        if obj.is_dir() and obj.name not in SKIP_DIRS:
            return [
                dest_path,
                *self._recursive_walk(root=obj, resource=resource, template_data=template_data),
            ]

        if (
            obj.is_file()
            and obj.name.split(".")[-1] not in SKIP_FILES_TYPES
            and obj.name != "__meta__.yml"
        ):
            return [dest_path]

        return []

    def _per_container(self, resource: str) -> list[DestinationFile]:
        """Generate a list of all paths that will be written to for a particular resource.

        Args:
            resource: The resource to search through.

        Returns:
            A list of paths to be written to.
        """
        msg = f"starting recursive walk with source container '{resource}'"
        self.output.debug(msg)

        # Cast the template data to not pollute the original
        template_data = copy.deepcopy(self.template_data)

        # Collect and template any resource specific variables
        meta_file = impl_resources.files(f"{self.resource_root}.{resource}") / "__meta__.yml"
        try:
            with meta_file.open("r", encoding="utf-8") as meta_fileh:
                self.output.debug(
                    msg=f"loading resource specific vars from {meta_file}",
                )
                meta = yaml.safe_load(meta_fileh.read())
        except FileNotFoundError:
            meta = {}
            self.output.debug(msg="no resource specific vars found")

        found = meta.get(self.resource_id, {})
        for key, value in found.items():
            if value["template"] and self.templar:
                serialized = yaml.dump(value["value"])
                templated = self.templar.render_from_content(
                    template=serialized,
                    data=template_data,
                )
                deserialized = yaml.safe_load(templated)
                setattr(template_data, key, deserialized)
            else:
                setattr(template_data, key, value["value"])

        return self._recursive_walk(
            impl_resources.files(f"{self.resource_root}.{resource}"),
            resource,
            template_data,
        )

    def collect_paths(self) -> list[DestinationFile]:
        """Determine paths that will be written to.

        Returns:
            A list of paths to be written to.
        """
        file_list = []
        for resource in self.resources:
            file_list.extend(self._per_container(resource))

        return file_list


@dataclass
class Copier:
    """Configuration for the Copier class.

    Attributes:
        output: An instance of the Output class.
        templar: An instance of the Templar class.
    """

    output: Output
    templar: Templar | None = None

    def _copy_file(
        self,
        dest_path: DestinationFile,
    ) -> None:
        """Copy a file to destination.

        Args:
            dest_path: The destination path to copy the file to.
        """
        # remove .j2 suffix at destination
        self.output.debug(msg=f"dest file is {dest_path}")

        content = dest_path.source.read_text(encoding="utf-8")
        # only render as templates if both of these are provided,
        # and original file suffix was j2
        if self.templar and dest_path.template_data and dest_path.needs_templating:
            content = self.templar.render_from_content(
                template=content,
                data=dest_path.template_data,
            )
        with dest_path.dest.open("w", encoding="utf-8") as df_handle:
            df_handle.write(content)

    def copy_containers(self: Copier, paths: list[DestinationFile]) -> None:
        """Copy multiple containers to destination.

        Args:
            paths: A list of paths to create in the destination.
        """
        for path in paths:
            if path.conflicts:
                path.remove_existing()

            if path.source.is_dir():
                path.dest.mkdir(parents=True, exist_ok=True)

            elif path.source.is_file():
                self._copy_file(path)
