"""Re-usable utility functions used by this package."""

from __future__ import annotations

import os

from dataclasses import dataclass, field
from importlib import resources as impl_resources
from typing import TYPE_CHECKING

import yaml

from ansible_creator.constants import GLOBAL_TEMPLATE_VARS, SKIP_DIRS, SKIP_FILES_TYPES


if TYPE_CHECKING:
    from ansible_creator.compat import Traversable
    from ansible_creator.output import Output
    from ansible_creator.templar import Templar

PATH_REPLACERS = {
    "project_org": "scm_org",
    "project_repo": "scm_project",
}


@dataclass
class TermFeatures:
    """Terminal features."""

    color: bool
    links: bool

    def any_enabled(self: TermFeatures) -> bool:
        """Return True if any features are enabled."""
        return any((self.color, self.links))


def expand_path(path: str) -> str:
    """Resolve absolute path.

    :param path: Path to expand.
    :returns: Expanded absolute path.
    """
    return os.path.abspath(
        os.path.expanduser(os.path.expandvars(path)),
    )


@dataclass
class Copier:
    """Configuration for the Copier class."""

    resources: list[str]
    """ list of resource containers to copy"""
    resource_id: str
    """the id of the resource to copy"""
    dest: str
    """the destination path to copy resources to"""
    output: Output
    """an instance of the Output class"""
    allow_overwrite: list[str] | None = None
    """a list of paths that should be overwritten at destination"""
    index: int = 0
    """index of the current resource being copied"""
    resource_root: str = "ansible_creator.resources"
    """root path for the resources"""
    templar: Templar | None = None
    """an instance of the Templar class"""
    template_data: dict[str, str] = field(default_factory=dict)
    """a dictionary containing the original data to render templates with"""

    @property
    def resource(self: Copier) -> str:
        """Return the current resource being copied."""
        return self.resources[self.index]

    def _recursive_copy(
        self: Copier,
        root: Traversable,
        template_data: dict[str, str],
    ) -> None:
        """Recursively traverses a resource container and copies content to destination.

        :param root: A traversable object representing root of the container to copy.
        :param copier_config: Configuration for the Copier class.
        :param template_data: A dictionary containing current data to render templates with.
        """
        self.output.debug(msg=f"current root set to {root}")

        for obj in root.iterdir():
            overwrite = False
            # resource names may have a . but directories use / in the path
            dest_name = str(obj).split(
                self.resource.replace(".", "/") + "/",
                maxsplit=1,
            )[-1]
            dest_path = os.path.join(self.dest, dest_name)
            if (self.allow_overwrite) and (dest_name in self.allow_overwrite):
                overwrite = True
            # replace placeholders in destination path with real values
            for key, val in PATH_REPLACERS.items():
                if key in dest_path and template_data:
                    dest_path = dest_path.replace(key, template_data.get(val, ""))

            if obj.is_dir():
                if obj.name in SKIP_DIRS:
                    continue
                if not os.path.exists(dest_path):
                    os.makedirs(dest_path)

                # recursively copy the directory
                self._recursive_copy(
                    root=obj,
                    template_data=template_data,
                )

            elif obj.is_file():
                if obj.name.split(".")[-1] in SKIP_FILES_TYPES:
                    continue
                if obj.name == "__meta__.yml":
                    continue
                # remove .j2 suffix at destination
                dest_file = os.path.join(
                    self.dest,
                    dest_path.split(".j2", maxsplit=1)[0],
                )
                self.output.debug(msg=f"dest file is {dest_file}")

                # write at destination only if missing or belongs to overwrite list
                if not os.path.exists(dest_file) or overwrite:
                    content = obj.read_text(encoding="utf-8")
                    # only render as templates if both of these are provided
                    # templating is not mandatory
                    if self.templar and template_data:
                        content = self.templar.render_from_content(
                            template=content,
                            data=template_data,
                        )
                    with open(dest_file, "w", encoding="utf-8") as df_handle:
                        df_handle.write(content)

    def _per_container(self: Copier) -> None:
        """Copy files and directories from a possibly nested source to a destination.

        :param copier_config: Configuration for the Copier class.

        :raises CreatorError: if allow_overwrite is not a list.
        """
        self.output.debug(
            msg=f"starting recursive copy with source container '{self.resource}'",
        )
        self.output.debug(msg=f"allow_overwrite set to {self.allow_overwrite}")

        # Include the global template variables
        self.template_data.update(GLOBAL_TEMPLATE_VARS)

        # Copy the template data to not pollute the original
        template_data = self.template_data.copy()

        # Collect and template any resource specific variables
        meta_file = (
            impl_resources.files(f"{self.resource_root}.{self.resource}")
            / "__meta__.yml"
        )
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
                template_data.update({key: deserialized})
            else:
                template_data.update({key: value["value"]})

        self._recursive_copy(
            root=impl_resources.files(f"{self.resource_root}.{self.resource}"),
            template_data=template_data,
        )

    def copy_containers(
        self: Copier,
    ) -> None:
        """Copy multiple containers to destination.

        :param copier_config: Configuration for the Copier class.
        """
        for i in range(len(self.resources)):
            self.index = i
            self._per_container()
