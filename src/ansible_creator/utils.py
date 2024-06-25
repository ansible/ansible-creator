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
    "project_org": "scm_org",
    "project_repo": "scm_project",
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
class Copier:
    """Configuration for the Copier class.

    Attributes:
        resources: List of resource containers to copy.
        resource_id: The id of the resource to copy.
        dest: The destination path to copy resources to.
        output: An instance of the Output class.
        template_data: A dictionary containing the original data to render templates with.
        allow_overwrite: A list of paths that should be overwritten at destination.
        index: Index of the current resource being copied.
        resource_root: Root path for the resources.
        templar: An instance of the Templar class.
    """

    resources: list[str]
    resource_id: str
    dest: Path
    output: Output
    template_data: TemplateData
    allow_overwrite: list[str] | None = None
    index: int = 0
    resource_root: str = "ansible_creator.resources"
    templar: Templar | None = None

    @property
    def resource(self: Copier) -> str:
        """Return the current resource being copied."""
        return self.resources[self.index]

    def _recursive_copy(  # noqa: C901, PLR0912
        self: Copier,
        root: Traversable,
        template_data: TemplateData,
    ) -> None:
        """Recursively traverses a resource container and copies content to destination.

        Args:
            root: A traversable object representing root of the container to copy.
            template_data: A dictionary containing current data to render templates with.
        """
        self.output.debug(msg=f"current root set to {root}")

        for obj in root.iterdir():
            overwrite = False
            # resource names may have a . but directories use / in the path
            dest_name = str(obj).split(
                self.resource.replace(".", "/") + "/",
                maxsplit=1,
            )[-1]
            dest_path = self.dest / dest_name
            if self.allow_overwrite and (dest_name in self.allow_overwrite):
                overwrite = True
            # replace placeholders in destination path with real values
            for key, val in PATH_REPLACERS.items():
                if key in str(dest_path) and template_data:
                    str_dest_path = str(dest_path)
                    repl_val = getattr(template_data, val)
                    dest_path = Path(str_dest_path.replace(key, repl_val))

            if obj.is_dir():
                if obj.name in SKIP_DIRS:
                    continue
                if not dest_path.exists():
                    dest_path.mkdir(parents=True)

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
                needs_templating = False
                if dest_path.suffix == ".j2":
                    dest_path = dest_path.with_suffix("")
                    needs_templating = True
                dest_file = Path(self.dest) / dest_path
                self.output.debug(msg=f"dest file is {dest_file}")

                # write at destination only if missing or belongs to overwrite list
                if not dest_file.exists() or overwrite:
                    content = obj.read_text(encoding="utf-8")
                    # only render as templates if both of these are provided,
                    # and original file suffix was j2
                    if self.templar and template_data and needs_templating:
                        content = self.templar.render_from_content(
                            template=content,
                            data=template_data,
                        )
                    with dest_file.open("w", encoding="utf-8") as df_handle:
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

        # Cast the template data to not pollute the original
        template_data = copy.deepcopy(self.template_data)

        # Collect and template any resource specific variables
        meta_file = impl_resources.files(f"{self.resource_root}.{self.resource}") / "__meta__.yml"
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
