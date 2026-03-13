"""Definitions for ansible-creator init action."""

from __future__ import annotations

import json
import re
import shutil
import uuid

from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import yaml

from ansible_creator.exceptions import CreatorError
from ansible_creator.templar import Templar
from ansible_creator.types import TemplateData
from ansible_creator.utils import Copier, Walker, ask_yes_no


if TYPE_CHECKING:
    from ansible_creator.config import Config
    from ansible_creator.output import Output


class Init:
    """Class representing ansible-creator init subcommand.

    Attributes:
        common_resources: List of common resources to copy.
    """

    common_resources: tuple[str, ...] = (
        "common.devcontainer",
        "common.devfile",
        "common.gitignore",
        "common.vscode",
        "common.ai",
    )

    def __init__(
        self,
        config: Config,
    ) -> None:
        """Initialize the init action.

        Args:
            config: App configuration object.
        """
        self._namespace: str = config.namespace
        self._collection_name = config.collection_name or ""
        self._init_path: Path = Path(config.init_path)
        self._force = config.force
        self._overwrite = config.overwrite
        self._no_overwrite = config.no_overwrite
        self._creator_version = config.creator_version
        self._project = config.project
        self._templar = Templar()
        self.output: Output = config.output
        self._role_name: str = config.role_name

        # Load EE config from file if provided, then merge with CLI args
        ee_config = self._load_ee_config(config.ee_config) if config.ee_config else {}

        # CLI args override config file values
        self._ee_base_image: str = (
            config.base_image
            if config.base_image != "quay.io/fedora/fedora:41"
            else ee_config.get("base_image", config.base_image)
        )

        # For collections, merge CLI args with config file (CLI takes precedence)
        config_collections: list[str | dict[str, str]] = ee_config.get("collections", [])
        cli_collections: list[str | dict[str, str]] = list(config.ee_collections)
        collections_to_parse: list[str | dict[str, str]] = cli_collections or config_collections
        self._ee_collections: list[dict[str, str]] = self._parse_collections_from_config(
            collections_to_parse
        )

        # For deps/packages, merge CLI args with config file
        self._ee_python_deps: list[str] = (
            list(config.ee_python_deps)
            if config.ee_python_deps
            else ee_config.get("python_deps", [])
        )
        self._ee_system_packages: list[str] = (
            list(config.ee_system_packages)
            if config.ee_system_packages
            else ee_config.get("system_packages", [])
        )
        self._ee_name: str = (
            config.ee_name
            if config.ee_name != "ansible_sample_ee"
            else ee_config.get("name", config.ee_name)
        )

        # Additional EE config options (only from config file)
        self._ee_additional_build_files: list[dict[str, str]] = ee_config.get(
            "additional_build_files", []
        )
        self._ee_additional_build_steps: dict[str, list[str]] = ee_config.get(
            "additional_build_steps", {}
        )
        self._ee_options: dict[str, Any] = ee_config.get("options", {})
        self._ee_ansible_cfg: str = ee_config.get("ansible_cfg", "")

        # Auto-detect official EE images and set microdnf as package manager
        if "package_manager_path" not in self._ee_options and self._is_official_ee_image(
            self._ee_base_image
        ):
            self._ee_options["package_manager_path"] = "/usr/bin/microdnf"

    def run(self) -> None:
        """Start scaffolding skeleton."""
        self._construct_init_path()
        self.output.debug(msg=f"final destination path set to {self._init_path}")

        if self._init_path.exists():
            self.init_exists()
        self._init_path.mkdir(parents=True, exist_ok=True)

        self._scaffold()

    def _construct_init_path(self) -> None:
        """Construct the init path based on project type."""
        if self._project in {"playbook", "execution_env"}:
            return

        if (
            self._init_path.parts[-2:] == ("collections", "ansible_collections")
            and self._project == "collection"
            and isinstance(self._collection_name, str)
        ):
            self._init_path = self._init_path / self._namespace / self._collection_name

    def init_exists(self) -> None:
        """Handle existing init path.

        Raises:
            CreatorError: When init path is a file or not empty and --force is not provided.
        """
        # check if init_path already exists
        # init-path exists and is a file
        if self._init_path.is_file():
            msg = f"the path {self._init_path} already exists, but is a file - aborting"
            raise CreatorError(msg)
        if next(self._init_path.iterdir(), None) and self._force:
            # user requested --force, re-initializing existing directory
            self.output.warning(
                "The `force` flag is deprecated and will be removed soon. "
                "Please start using `overwrite` flag.",
            )
            self.output.warning(
                f"re-initializing existing directory {self._init_path}",
            )
            try:
                shutil.rmtree(self._init_path)
            except OSError as e:
                err = f"failed to remove existing directory {self._init_path}: {e}"
                raise CreatorError(err) from e

    def unique_name_in_devfile(self) -> str:
        """Use project specific name in devfile.

        Returns:
            Unique name entry.
        """
        final_name = f"{self._namespace}.{self._collection_name}"
        final_uuid = str(uuid.uuid4())[:8]
        return f"{final_name}-{final_uuid}"

    def _is_official_ee_image(self, image: str) -> bool:
        """Check if the image is an official Red Hat EE image requiring microdnf.

        Official EE images from Red Hat use microdnf as the package manager
        instead of dnf/yum due to their minimal RHEL base.

        Args:
            image: The container image name/URL.

        Returns:
            True if the image is an official EE image requiring microdnf.
        """
        official_ee_patterns = (
            "registry.redhat.io/ansible-automation-platform",
            "registry.redhat.io/aap",
            "ee-minimal-rhel",
            "ee-supported-rhel",
            "ee-29-rhel",
            "ee-dellos",
        )
        return any(pattern in image for pattern in official_ee_patterns)

    def _load_ee_config(self, config_path: str) -> dict[str, Any]:
        """Load EE configuration from a JSON or YAML file.

        Args:
            config_path: Path to the config file.

        Returns:
            Dictionary containing EE configuration.

        Raises:
            CreatorError: If the file cannot be read or parsed.
        """
        path = Path(config_path)
        if not path.exists():
            msg = f"EE config file not found: {config_path}"
            raise CreatorError(msg)

        content = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            try:
                data: dict[str, Any] = json.loads(content)
            except json.JSONDecodeError as e:
                msg = f"Invalid JSON in EE config file {config_path}: {e}"
                raise CreatorError(msg) from e
            return data
        # Default to YAML for .yml, .yaml, or unknown extensions
        try:
            yaml_data: dict[str, Any] = yaml.safe_load(content) or {}
        except yaml.YAMLError as e:
            msg = f"Invalid YAML in EE config file {config_path}: {e}"
            raise CreatorError(msg) from e
        return yaml_data

    def _parse_collections_from_config(
        self, collections: list[str | dict[str, str]]
    ) -> list[dict[str, str]]:
        """Parse collections from config file or CLI args.

        Handles both string format (from CLI) and dict format (from config file).

        Args:
            collections: List of collection strings or dicts.

        Returns:
            List of dictionaries with collection details.
        """
        parsed: list[dict[str, str]] = []
        for col in collections:
            if isinstance(col, dict):
                # Already a dict from config file, validate it
                self._validate_collection_dict(col)
                parsed.append(col)
            else:
                # String from CLI, parse it
                parsed.extend(self._parse_collections([col]))
        return parsed

    def _validate_collection_dict(self, col: dict[str, str]) -> None:
        """Validate a collection dictionary from config file.

        Args:
            col: Collection dictionary to validate.

        Raises:
            CreatorError: If the collection dict is invalid.
        """
        if "name" not in col:
            msg = "Collection in config file must have a 'name' field"
            raise CreatorError(msg)

        col_name = col["name"]
        # Skip namespace.name validation for Git URLs (they use the URL as the name)
        if not col_name.startswith(("https://", "http://")):
            self._validate_collection_name(col_name)

        if "type" in col:
            self._validate_collection_type(col["type"])

        if "source" in col:
            self._validate_source_url(col["source"])

    def _validate_collection_name(self, col_name: str) -> None:
        """Validate collection name format.

        Args:
            col_name: The collection name to validate.

        Raises:
            CreatorError: If the collection name is invalid.
        """
        name_pattern = re.compile(r"^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$")
        if not name_pattern.match(col_name):
            msg = (
                f"Invalid collection name '{col_name}'. "
                "Must be in format 'namespace.name' with lowercase letters, "
                "numbers, and underscores."
            )
            raise CreatorError(msg)

    def _validate_collection_type(self, col_type: str) -> str:
        """Validate and normalize collection type.

        Args:
            col_type: The collection type to validate.

        Returns:
            The normalized (lowercase) collection type.

        Raises:
            CreatorError: If the collection type is invalid.
        """
        valid_types = {"galaxy", "git", "url", "file", "dir"}
        normalized = col_type.lower()
        if normalized not in valid_types:
            msg = (
                f"Invalid collection type '{col_type}'. "
                f"Must be one of: {', '.join(sorted(valid_types))}"
            )
            raise CreatorError(msg)
        return normalized

    def _validate_source_url(self, source: str) -> None:
        """Validate source URL format if it's an HTTP(S) URL.

        Args:
            source: The source URL to validate.

        Raises:
            CreatorError: If the source URL is invalid.
        """
        # HTTP is intentionally supported for internal/private registries.
        # This only validates URL format; actual network security is handled by ansible-builder.
        if source.startswith(("https://", "http://")):  # NOSONAR
            parsed_url = urlparse(source)
            if not parsed_url.netloc:
                msg = f"Invalid source URL '{source}'. Must be a valid URL."
                raise CreatorError(msg)

    def _parse_single_collection(self, col: str) -> dict[str, str]:
        """Parse a single collection string into a dictionary.

        Supports two formats:
        1. Standard: 'namespace.name[:version[:type[:source]]]'
        2. Git URL: 'https://...path/namespace.name[:version]:git'

        Args:
            col: Collection string to parse.

        Returns:
            Dictionary with collection details.
        """
        # Check if this is a Git URL (starts with http:// or https://)
        if col.startswith(("https://", "http://")):
            return self._parse_git_url_collection(col)

        # Standard format: name[:version[:type[:source]]]
        parts = col.split(":", maxsplit=3)
        col_name = parts[0]

        self._validate_collection_name(col_name)
        col_dict: dict[str, str] = {"name": col_name}

        if len(parts) > 1 and parts[1]:
            col_dict["version"] = parts[1]

        if len(parts) > 2 and parts[2]:  # noqa: PLR2004
            col_dict["type"] = self._validate_collection_type(parts[2])

        if len(parts) > 3 and parts[3]:  # noqa: PLR2004
            self._validate_source_url(parts[3])
            col_dict["source"] = parts[3]

        return col_dict

    def _parse_git_url_collection(self, col: str) -> dict[str, str]:
        """Parse a Git URL collection string.

        Format: 'https://[token@]host/path/namespace.name[:version]:git'

        Args:
            col: Git URL collection string.

        Returns:
            Dictionary with name (URL), optional version, and type=git.
        """
        # Split from the right to handle URLs with colons
        # Expected format: URL[:version]:git
        parts = col.rsplit(":", maxsplit=2)

        if len(parts) < 2:  # noqa: PLR2004
            # Just a URL, no version or type specified
            return {"name": col, "type": "git"}

        last_part = parts[-1].lower()

        # Check if last part is a type indicator
        if last_part == "git":
            if len(parts) == 2:  # noqa: PLR2004
                # Format: URL followed by git type
                return {"name": parts[0], "type": "git"}
            # Format: URL followed by version and git type
            return {"name": parts[0], "version": parts[1], "type": "git"}

        # No type specified, assume git and treat second part as version
        if len(parts) == 2:  # noqa: PLR2004
            return {"name": parts[0], "version": parts[1], "type": "git"}

        # Fallback: treat entire string as the URL
        return {"name": col, "type": "git"}

    def _parse_collections(self, collections: list[str]) -> list[dict[str, str]]:
        """Parse collection strings into structured dictionaries.

        Supports formats:
        - 'name' -> {'name': 'name'}
        - 'name:version' -> {'name': 'name', 'version': 'version'}
        - 'name:version:type:source' -> dict with name, version, type, source

        Args:
            collections: List of collection strings to parse.

        Returns:
            List of dictionaries with collection details.
        """
        return [self._parse_single_collection(col) for col in collections]

    def _scaffold(self) -> None:
        """Scaffold an ansible project.

        Raises:
            CreatorError: When the destination directory contains files that will be overwritten and
                the user chooses not to proceed.
        """
        resources: tuple[str, ...]
        self.output.debug(
            msg=f"started copying {self._project} skeleton to destination",
        )
        template_data = TemplateData(
            namespace=self._namespace,
            collection_name=self._collection_name,
            creator_version=self._creator_version,
            dev_file_name=self.unique_name_in_devfile(),
            role_name=self._role_name,
            ee_base_image=self._ee_base_image,
            ee_collections=self._ee_collections,
            ee_python_deps=self._ee_python_deps,
            ee_system_packages=self._ee_system_packages,
            ee_name=self._ee_name,
            ee_additional_build_files=self._ee_additional_build_files,
            ee_additional_build_steps=self._ee_additional_build_steps,
            ee_options=self._ee_options,
            ee_ansible_cfg=self._ee_ansible_cfg,
        )

        if self._project == "execution_env":
            resources = (f"{self._project}_project", "common.ee-ci")
        elif self._project == "collection":
            self.common_resources = (*self.common_resources, "common.role")
            resources = (f"{self._project}_project", *self.common_resources)
        else:
            resources = (f"{self._project}_project", *self.common_resources)

        walker = Walker(
            resources=resources,
            resource_id=f"{self._project}_project",
            dest=self._init_path,
            output=self.output,
            templar=self._templar,
            template_data=template_data,
        )
        paths = walker.collect_paths()

        copier = Copier(
            output=self.output,
        )

        if self._no_overwrite and paths.has_conflicts():
            msg = (
                "The flag `--no-overwrite` restricts overwriting."
                "\nThe destination directory contains files that can be overwritten."
                "\nPlease re-run ansible-creator with --overwrite to continue."
            )
            raise CreatorError(msg)

        if not paths.has_conflicts() or self._force or self._overwrite:
            copier.copy_containers(paths)
            self._write_optional_files()
            self.output.note(f"{self._project} project created at {self._init_path}")
            return

        if not self._overwrite:  # pragma: no cover
            question = (
                "Files in the destination directory will be overwritten. Do you want to proceed?"
            )
            answer = ask_yes_no(question)
            if answer:
                copier.copy_containers(paths)
                self._write_optional_files()
            else:
                msg = (
                    "The destination directory contains files that will be overwritten."
                    " Please re-run ansible-creator with --overwrite to continue."
                )
                raise CreatorError(msg)

        self.output.note(f"{self._project} project created at {self._init_path}")

    def _write_optional_files(self) -> None:
        """Write optional files based on configuration.

        This method writes files that should only be created when specific
        configuration is provided, such as ansible.cfg for EE projects.
        """
        if self._project != "execution_env":
            return

        # Write ansible.cfg only if content was provided via config file
        if self._ee_ansible_cfg:
            ansible_cfg_path = self._init_path / "ansible.cfg"
            ansible_cfg_path.write_text(self._ee_ansible_cfg, encoding="utf-8")
            self.output.debug(msg=f"Writing to {ansible_cfg_path}")
