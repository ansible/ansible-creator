"""A home for shared types."""

from __future__ import annotations

import re

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from ansible_creator.constants import GLOBAL_TEMPLATE_VARS
from ansible_creator.exceptions import CreatorError


if TYPE_CHECKING:
    from collections.abc import Sequence


# URL protocol prefixes for validation and Git URL collection detection.
# HTTP is intentionally supported for internal/private registries and Git servers.
HTTP_PROTOCOLS = ("https://", "http://")  # NOSONAR
GIT_URL_PREFIXES = ("https://", "http://", "git://", "ssh://", "file://", "git@")  # NOSONAR

COLLECTION_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$")
VALID_COLLECTION_TYPES = frozenset({"galaxy", "git", "url", "file", "dir"})


def validate_collection_name(name: str) -> None:
    """Validate that a collection name follows the namespace.name format.

    Args:
        name: The collection name to validate.

    Raises:
        CreatorError: If the name is invalid.
    """
    if not COLLECTION_NAME_RE.match(name):
        msg = (
            f"Invalid collection name '{name}'. "
            "Must be in format 'namespace.name' with lowercase letters, "
            "numbers, and underscores."
        )
        raise CreatorError(msg)


def validate_collection_type(col_type: str) -> str:
    """Validate and normalize a collection type string.

    Args:
        col_type: The collection type to validate.

    Returns:
        The normalized (lowercase) collection type.

    Raises:
        CreatorError: If the type is invalid.
    """
    normalized = col_type.lower()
    if normalized not in VALID_COLLECTION_TYPES:
        msg = (
            f"Invalid collection type '{col_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_COLLECTION_TYPES))}"
        )
        raise CreatorError(msg)
    return normalized


def validate_source_url(source: str) -> None:
    """Validate a source URL format if it is an HTTP(S) URL.

    Args:
        source: The source URL to validate.

    Raises:
        CreatorError: If the URL is malformed.
    """
    if source.startswith(HTTP_PROTOCOLS):  # NOSONAR
        parsed = urlparse(source)
        if not parsed.netloc:
            msg = f"Invalid source URL '{source}'. Must be a valid URL."
            raise CreatorError(msg)


@dataclass(frozen=True)
class EECollection:
    """A single Ansible collection entry for an execution environment.

    Attributes:
        name: Collection name (namespace.name) or a Git URL.
        version: Version constraint string.
        type: Collection type (galaxy, git, url, file, dir).
        source: Source URL for the collection.
    """

    name: str
    version: str = ""
    type: str = ""
    source: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> EECollection:
        """Create a validated EECollection from a raw dictionary.

        Args:
            data: Dictionary with collection fields.

        Returns:
            A validated EECollection instance.

        Raises:
            CreatorError: If required fields are missing or values are invalid.
        """
        if "name" not in data:
            msg = "Collection in config file must have a 'name' field"
            raise CreatorError(msg)

        name = data["name"]
        if not name.startswith(GIT_URL_PREFIXES):
            validate_collection_name(name)

        col_type = data.get("type", "")
        if col_type:
            col_type = validate_collection_type(col_type)

        source = data.get("source", "")
        if source:
            validate_source_url(source)

        return cls(
            name=name,
            version=data.get("version", ""),
            type=col_type,
            source=source,
        )

    def as_dict(self) -> dict[str, str]:
        """Convert to a plain dictionary for template rendering.

        Returns:
            Dictionary with only non-empty fields.
        """
        result: dict[str, str] = {"name": self.name}
        if self.version:
            result["version"] = self.version
        if self.type:
            result["type"] = self.type
        if self.source:
            result["source"] = self.source
        return result

    @classmethod
    def to_schema(cls) -> dict[str, Any]:
        """Return a JSON-Schema-like description of a collection entry.

        Returns:
            Schema dictionary.
        """
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Collection name (namespace.name) or Git URL",
                },
                "version": {
                    "type": "string",
                    "description": "Version constraint",
                    "default": "",
                },
                "type": {
                    "type": "string",
                    "description": "Collection type",
                    "enum": sorted(VALID_COLLECTION_TYPES),
                    "default": "",
                },
                "source": {
                    "type": "string",
                    "description": "Collection source URL",
                    "default": "",
                },
            },
            "required": ["name"],
        }


@dataclass(frozen=True)
class EEConfig:
    """Canonical representation of execution environment configuration.

    Used by both ``--ee-config`` (inline JSON) and ``--ee-config-file``
    (YAML/JSON file).  The schema generator exposes its structure so
    that consumers (e.g. the ADT server) know the payload shape.

    Attributes:
        name: Name/tag for the EE image.
        base_image: Base container image.
        collections: Ansible collections to include.
        python_deps: Python package dependencies.
        system_packages: System packages to install.
        additional_build_files: Extra files for the build context.
        additional_build_steps: Custom build steps keyed by phase.
        options: Build options (e.g. package_manager_path).
        ansible_cfg: Content for an ansible.cfg file.
        ee_file_name: Name of the EE definition file (default: execution-environment.yml).
    """

    name: str = "ansible_sample_ee"
    base_image: str = "quay.io/fedora/fedora:41"
    collections: tuple[EECollection, ...] = ()
    python_deps: tuple[str, ...] = ()
    system_packages: tuple[str, ...] = ()
    additional_build_files: tuple[dict[str, str], ...] = ()
    additional_build_steps: dict[str, list[str]] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
    ansible_cfg: str = ""
    ee_file_name: str = "execution-environment.yml"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EEConfig:
        """Create a validated EEConfig from a raw dictionary.

        Dictionaries in the ``collections`` list are converted to
        ``EECollection`` instances with full validation.

        Args:
            data: Raw configuration dictionary (from JSON or YAML).

        Returns:
            A validated EEConfig instance.
        """
        raw_collections = data.get("collections", [])
        collections = tuple(
            EECollection.from_dict(c if isinstance(c, dict) else {"name": c})
            for c in raw_collections
        )
        return cls(
            name=data.get("name", "ansible_sample_ee"),
            base_image=data.get("base_image", "quay.io/fedora/fedora:41"),
            collections=collections,
            python_deps=tuple(data.get("python_deps", [])),
            system_packages=tuple(data.get("system_packages", [])),
            additional_build_files=tuple(data.get("additional_build_files", [])),
            additional_build_steps=data.get("additional_build_steps", {}),
            options=dict(data.get("options", {})),
            ansible_cfg=data.get("ansible_cfg", ""),
            ee_file_name=cls._validate_ee_file_name(
                data.get("ee_file_name", "execution-environment.yml"),
            ),
        )

    @staticmethod
    def _validate_ee_file_name(name: str) -> str:
        """Validate ee_file_name is a safe basename with a YAML extension.

        Args:
            name: The proposed EE definition file name.

        Returns:
            The validated file name.

        Raises:
            ValueError: If the name contains path separators or has an
                invalid extension.
        """
        if "/" in name or "\\" in name or ".." in name:
            msg = f"ee_file_name must be a plain filename, not a path: {name!r}"
            raise ValueError(msg)
        if not name.endswith((".yml", ".yaml")):
            msg = f"ee_file_name must end with .yml or .yaml: {name!r}"
            raise ValueError(msg)
        return name

    @classmethod
    def to_schema(cls) -> dict[str, Any]:
        """Return a JSON-Schema-like description of the EE config object.

        Returns:
            Schema dictionary describing all fields, types, and defaults.
        """
        return {
            "type": "object",
            "description": (
                "EE configuration (pass as JSON via --ee-config "
                "or as a YAML/JSON file via --ee-config-file)"
            ),
            "properties": {
                "name": {
                    "type": "string",
                    "default": "ansible_sample_ee",
                    "description": "Name/tag for the EE image",
                },
                "base_image": {
                    "type": "string",
                    "default": "quay.io/fedora/fedora:41",
                    "description": "Base container image",
                },
                "collections": {
                    "type": "array",
                    "items": EECollection.to_schema(),
                    "description": "Ansible collections to include",
                },
                "python_deps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Python package dependencies",
                },
                "system_packages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "System packages to install",
                },
                "additional_build_files": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Extra files for the build context",
                },
                "additional_build_steps": {
                    "type": "object",
                    "description": "Custom build steps (prepend_base, append_base, etc.)",
                },
                "options": {
                    "type": "object",
                    "description": "Build options (e.g. package_manager_path)",
                },
                "ansible_cfg": {
                    "type": "string",
                    "description": "Content for ansible.cfg file",
                    "default": "",
                },
                "ee_file_name": {
                    "type": "string",
                    "description": "Name of the EE definition file",
                    "default": "execution-environment.yml",
                },
            },
        }


@dataclass(frozen=True)
class OfficialEEImage:
    """An official Red Hat EE base image pattern and its Python interpreter.

    Attributes:
        pattern: Substring matched against the container image name/URL.
        python_path: Absolute path to the Python interpreter in the image.
    """

    pattern: str
    python_path: str


# Single source of truth for official EE image detection and Python paths.
# Ordered most-specific first so versioned patterns match before broad ones.
# Update this tuple when new AAP versions ship with different Python versions.
OFFICIAL_EE_IMAGES: tuple[OfficialEEImage, ...] = (
    # AAP 2.6 uses Python 3.12
    OfficialEEImage("ansible-automation-platform-26", "/usr/bin/python3.12"),
    OfficialEEImage("aap-26", "/usr/bin/python3.12"),
    # AAP 2.4/2.5 uses Python 3.11
    OfficialEEImage("ansible-automation-platform-25", "/usr/bin/python3.11"),
    OfficialEEImage("aap-25", "/usr/bin/python3.11"),
    OfficialEEImage("ansible-automation-platform-24", "/usr/bin/python3.11"),
    OfficialEEImage("aap-24", "/usr/bin/python3.11"),
    # Broad registry prefixes (catch-all for unversioned official images)
    OfficialEEImage("registry.redhat.io/ansible-automation-platform", "/usr/bin/python3.11"),
    OfficialEEImage("registry.redhat.io/aap", "/usr/bin/python3.11"),
    # Named official EE images
    OfficialEEImage("ee-minimal-rhel", "/usr/bin/python3.11"),
    OfficialEEImage("ee-supported-rhel", "/usr/bin/python3.11"),
    OfficialEEImage("ee-29-rhel", "/usr/bin/python3.11"),
    OfficialEEImage("ee-dellos", "/usr/bin/python3.11"),
)

DEFAULT_PYTHON_PATH = "/usr/bin/python3"


@dataclass
class TemplateData:
    """Dataclass representing the template data.

    Attributes:
        resource_type: The type of resource to be scaffolded.
        plugin_type: The type of plugin to be scaffolded.
        plugin_name: The name of the plugin to be scaffolded.
        role_name: The name of the role to be scaffolded.
        additions: A dictionary containing additional data to add to the gitignore.
        collection_name: The name of the collection.
        creator_version: The version of the creator.
        dev_container_image: The devcontainer image.
        dev_file_image: The devfile image.
        dev_file_name: The unique name entry in devfile.
        namespace: The namespace of the collection.
        execution_environment_image: The execution environment image.
        recommended_extensions: A list of recommended VsCode extensions.
        ee_base_image: Base image for execution environment.
        ee_collections: List of Ansible collections for execution environment (dicts with name,
            version, type, source).
        ee_python_deps: List of Python dependencies for execution environment.
        ee_system_packages: List of system packages for execution environment.
        ee_name: Name/tag for the execution environment image.
        ee_additional_build_files: List of additional files to include in the EE build context.
        ee_additional_build_steps: Dict with prepend_base, append_base, prepend_final,
            append_final steps.
        ee_options: Dict of EE build options (e.g., package_manager_path).
        ee_ansible_cfg: Content for ansible.cfg file (for Automation Hub auth).
        is_official_ee: Whether the base image is an official Red Hat EE image.
        ee_python_path: Python interpreter path for the EE (varies by AAP version).
        ee_name_is_default: Whether ee_name is the unchanged default value.
        ee_file_name: Name of the EE definition file.
    """

    resource_type: str = ""
    plugin_type: str = ""
    plugin_name: str = ""
    role_name: str = ""
    additions: dict[str, dict[str, dict[str, str | bool]]] = field(default_factory=dict)
    collection_name: str = ""
    creator_version: str = ""
    dev_container_image: Sequence[str] = GLOBAL_TEMPLATE_VARS["DEV_CONTAINER_IMAGE"]
    dev_file_image: Sequence[str] = GLOBAL_TEMPLATE_VARS["DEV_FILE_IMAGE"]
    dev_file_name: str = ""
    namespace: str = ""
    execution_environment_image: Sequence[str] = GLOBAL_TEMPLATE_VARS[
        "EXECUTION_ENVIRONMENT_DEFAULT_IMAGE"
    ]
    recommended_extensions: Sequence[str] = field(
        default_factory=lambda: GLOBAL_TEMPLATE_VARS["RECOMMENDED_EXTENSIONS"],
    )
    ee_base_image: str = "quay.io/fedora/fedora:41"
    ee_collections: Sequence[dict[str, str]] = field(default_factory=list)
    ee_python_deps: Sequence[str] = field(default_factory=list)
    ee_system_packages: Sequence[str] = field(default_factory=list)
    ee_name: str = "ansible_sample_ee"
    ee_additional_build_files: Sequence[dict[str, str]] = field(default_factory=list)
    ee_additional_build_steps: dict[str, list[str]] = field(default_factory=dict)
    ee_options: dict[str, Any] = field(default_factory=dict)
    ee_ansible_cfg: str = ""
    is_official_ee: bool = False
    ee_python_path: str = DEFAULT_PYTHON_PATH
    ee_name_is_default: bool = True
    ee_file_name: str = "execution-environment.yml"
