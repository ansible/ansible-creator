"""A home for shared types."""

from __future__ import annotations

import re

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar
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
        _KNOWN_KEYS: Accepted dictionary keys for from_dict validation.
        name: Collection name (namespace.name) or a Git URL.
        version: Version constraint string.
        type: Collection type (galaxy, git, url, file, dir).
        source: Source URL for the collection.
    """

    _KNOWN_KEYS: ClassVar[frozenset[str]] = frozenset({"name", "version", "type", "source"})

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
        unknown = set(data) - cls._KNOWN_KEYS
        if unknown:
            msg = f"Unknown key(s) in collection entry: {', '.join(sorted(unknown))}"
            raise CreatorError(msg)

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


GALAXY_SERVER_ID_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
ENV_VAR_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


@dataclass(frozen=True)
class GalaxyServer:
    """A single Ansible Galaxy server entry for ansible.cfg.

    Attributes:
        id: Server identifier used in ``[galaxy_server.<id>]`` and the
            ``ANSIBLE_GALAXY_SERVER_<ID>_TOKEN`` env-var convention.
        url: Galaxy server content URL.
        auth_url: SSO/OAuth token endpoint (for Red Hat SSO-backed servers).
        token_required: Whether this server needs a token at build time.
        validate_certs: Whether to verify TLS certificates for this Galaxy/AH server.
            When ``False``, ``validate_certs = false`` is written to ``ansible.cfg``
            for that ``[galaxy_server.<id>]`` section (e.g. private hubs with a
            CA not present in the EE image).
    """

    id: str
    url: str
    auth_url: str = ""
    token_required: bool = False
    validate_certs: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GalaxyServer:
        """Create a validated GalaxyServer from a raw dictionary.

        Args:
            data: Dictionary with server fields.

        Returns:
            A validated GalaxyServer instance.

        Raises:
            CreatorError: If required fields are missing or values are invalid.
        """
        if "id" not in data:
            msg = "Galaxy server entry must have an 'id' field"
            raise CreatorError(msg)
        server_id = data["id"]
        if not GALAXY_SERVER_ID_RE.match(server_id):
            msg = (
                f"Invalid galaxy server id '{server_id}'. "
                "Must be lowercase letters, numbers, and underscores."
            )
            raise CreatorError(msg)

        if "url" not in data:
            msg = f"Galaxy server '{server_id}' must have a 'url' field"
            raise CreatorError(msg)

        return cls(
            id=server_id,
            url=data["url"],
            auth_url=data.get("auth_url", ""),
            token_required=data.get("token_required", False),
            validate_certs=data.get("validate_certs", True),
        )

    def as_dict(self) -> dict[str, Any]:
        """Convert to a plain dictionary for template rendering.

        Includes a derived ``token_env_var`` field for convenience.

        Returns:
            Dictionary with all fields plus ``token_env_var``.
        """
        result: dict[str, Any] = {
            "id": self.id,
            "url": self.url,
            "token_required": self.token_required,
            "validate_certs": self.validate_certs,
            "token_env_var": f"ANSIBLE_GALAXY_SERVER_{self.id.upper()}_TOKEN",
        }
        if self.auth_url:
            result["auth_url"] = self.auth_url
        return result

    @classmethod
    def to_schema(cls) -> dict[str, Any]:
        """Return a JSON-Schema-like description of a galaxy server entry.

        Returns:
            Schema dictionary.
        """
        return {
            "type": "object",
            "required": ["id", "url"],
            "properties": {
                "id": {
                    "type": "string",
                    "description": (
                        "Server identifier (e.g. automation_hub, private_hub, galaxy). "
                        "Used in [galaxy_server.<id>] and "
                        "ANSIBLE_GALAXY_SERVER_<ID>_TOKEN env var."
                    ),
                },
                "url": {
                    "type": "string",
                    "description": "Galaxy server content URL",
                },
                "auth_url": {
                    "type": "string",
                    "default": "",
                    "description": "SSO/OAuth token endpoint",
                },
                "token_required": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether this server needs a token at build time",
                },
                "validate_certs": {
                    "type": "boolean",
                    "default": True,
                    "description": (
                        "Whether to verify TLS for this Galaxy/AH server. "
                        "Set to false for Automation hubs with private CAs when the EE image "
                        "does not trust that CA."
                    ),
                },
            },
        }


@dataclass(frozen=True)
class ScmServer:
    """A single SCM server entry for private Git collection repositories.

    Attributes:
        id: Server identifier (e.g. ``github_org1``, ``internal_gitlab``).
        hostname: Git server hostname (e.g. ``github.com``, ``gitlab.internal.io``).
        token_env_var: Environment variable name holding the access token.
            Must be uppercase letters, digits, and underscores.
    """

    id: str
    hostname: str
    token_env_var: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScmServer:
        """Create a validated ScmServer from a raw dictionary.

        Args:
            data: Dictionary with server fields.

        Returns:
            A validated ScmServer instance.

        Raises:
            CreatorError: If required fields are missing or values are invalid.
        """
        if "id" not in data:
            msg = "SCM server entry must have an 'id' field"
            raise CreatorError(msg)
        server_id = data["id"]
        if not GALAXY_SERVER_ID_RE.match(server_id):
            msg = (
                f"Invalid SCM server id '{server_id}'. "
                "Must be lowercase letters, numbers, and underscores."
            )
            raise CreatorError(msg)

        if "hostname" not in data:
            msg = f"SCM server '{server_id}' must have a 'hostname' field"
            raise CreatorError(msg)

        if "token_env_var" not in data:
            msg = f"SCM server '{server_id}' must have a 'token_env_var' field"
            raise CreatorError(msg)
        token_env_var = data["token_env_var"]
        if not ENV_VAR_RE.match(token_env_var):
            msg = (
                f"Invalid token_env_var '{token_env_var}' for SCM server '{server_id}'. "
                "Must be uppercase letters, digits, and underscores (e.g. GITHUB_ORG1_TOKEN)."
            )
            raise CreatorError(msg)

        return cls(
            id=server_id,
            hostname=data["hostname"],
            token_env_var=token_env_var,
        )

    def as_dict(self) -> dict[str, str]:
        """Convert to a plain dictionary for template rendering.

        Returns:
            Dictionary with all fields.
        """
        return {
            "id": self.id,
            "hostname": self.hostname,
            "token_env_var": self.token_env_var,
        }

    @classmethod
    def to_schema(cls) -> dict[str, Any]:
        """Return a JSON-Schema-like description of an SCM server entry.

        Returns:
            Schema dictionary.
        """
        return {
            "type": "object",
            "required": ["id", "hostname", "token_env_var"],
            "properties": {
                "id": {
                    "type": "string",
                    "description": (
                        "Server identifier (e.g. github_org1, internal_gitlab). "
                        "Must be lowercase letters, numbers, and underscores."
                    ),
                },
                "hostname": {
                    "type": "string",
                    "description": "Git server hostname (e.g. github.com)",
                },
                "token_env_var": {
                    "type": "string",
                    "description": (
                        "Environment variable name for the access token. "
                        "Must be uppercase (e.g. GITHUB_ORG1_TOKEN). "
                        "This name is used as the GitHub Actions secret name."
                    ),
                },
            },
        }


@dataclass(frozen=True)
class EEConfig:
    """Canonical representation of execution environment configuration.

    Used by both ``--ee-config`` (inline JSON) and ``--ee-config-file``
    (YAML/JSON file).  The schema generator exposes its structure so
    that consumers (e.g. the ADT server) know the payload shape.

    Attributes:
        _KNOWN_KEYS: Accepted dictionary keys for from_dict validation.
        ee_name: Name/tag for the EE image.
        base_image: Base container image.
        registry: Container registry hostname for the CI workflow (e.g. ghcr.io, quay.io).
        registry_tls_verify: Whether to verify TLS certificates when accessing
            container registries (login, pull, push, and image builds).
        image_name: Image name for the CI workflow (e.g. my-org/my-ee).
        collections: Ansible collections to include.
        python_deps: Python package dependencies.
        system_packages: System packages to install.
        additional_build_files: Extra files for the build context.
        additional_build_steps: Custom build steps keyed by phase.
        options: Build options (e.g. package_manager_path).
        build_arg_defaults: Default ARG values for the container build (e.g.
            ANSIBLE_GALAXY_CLI_COLLECTION_OPTS).
        ansible_cfg: Content for an ansible.cfg file.
        galaxy_servers: Galaxy server entries for ansible.cfg generation and
            workflow token plumbing.
        scm_servers: SCM server entries for private Git collection repositories.
        ee_file_name: Name of the EE definition file (default: execution-environment.yml).
    """

    _KNOWN_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "ee_name",
            "name",  # legacy alias for ee_name
            "base_image",
            "registry",
            "registry_tls_verify",
            "image_name",
            "collections",
            "python_deps",
            "system_packages",
            "additional_build_files",
            "additional_build_steps",
            "options",
            "build_arg_defaults",
            "ansible_cfg",
            "galaxy_servers",
            "scm_servers",
            "ee_file_name",
        }
    )

    ee_name: str = "ansible_sample_ee"
    base_image: str = "quay.io/fedora/fedora:41"
    registry: str = "ghcr.io"
    registry_tls_verify: bool = True
    image_name: str = ""
    collections: tuple[EECollection, ...] = ()
    python_deps: tuple[str, ...] = ()
    system_packages: tuple[str, ...] = ()
    additional_build_files: tuple[dict[str, str], ...] = ()
    additional_build_steps: dict[str, list[str]] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
    build_arg_defaults: dict[str, str] = field(default_factory=dict)
    ansible_cfg: str = ""
    galaxy_servers: tuple[GalaxyServer, ...] = ()
    scm_servers: tuple[ScmServer, ...] = ()
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

        Raises:
            CreatorError: If unknown keys are present.
        """
        unknown = set(data) - cls._KNOWN_KEYS
        if unknown:
            msg = f"Unknown key(s) in EE config: {', '.join(sorted(unknown))}"
            raise CreatorError(msg)

        raw_collections = data.get("collections", [])
        collections = tuple(
            EECollection.from_dict(c if isinstance(c, dict) else {"name": c})
            for c in raw_collections
        )
        raw_build_args = data.get("build_arg_defaults", {})
        if not isinstance(raw_build_args, dict):
            msg = "build_arg_defaults must be a mapping of string keys to string values"
            raise CreatorError(msg)
        build_arg_defaults: dict[str, str] = {}
        for bk, bv in raw_build_args.items():
            if not isinstance(bk, str) or not isinstance(bv, str):
                msg = "build_arg_defaults must be a mapping of string keys to string values"
                raise CreatorError(msg)
            build_arg_defaults[bk] = bv
        registry = data.get("registry", "ghcr.io")
        if "://" in registry:
            msg = f"Invalid registry '{registry}'. Provide a hostname (e.g. 'ghcr.io'), not a URL."
            raise CreatorError(msg)

        raw_servers = data.get("galaxy_servers", [])
        galaxy_servers = tuple(GalaxyServer.from_dict(s) for s in raw_servers)
        raw_scm = data.get("scm_servers", [])
        scm_servers = tuple(ScmServer.from_dict(s) for s in raw_scm)
        return cls(
            ee_name=data.get("ee_name", data.get("name", "ansible_sample_ee")),
            base_image=data.get("base_image", "quay.io/fedora/fedora:41"),
            registry=registry,
            registry_tls_verify=data.get("registry_tls_verify", True),
            image_name=data.get("image_name", ""),
            collections=collections,
            python_deps=tuple(data.get("python_deps", [])),
            system_packages=tuple(data.get("system_packages", [])),
            additional_build_files=tuple(data.get("additional_build_files", [])),
            additional_build_steps=data.get("additional_build_steps", {}),
            options=dict(data.get("options", {})),
            build_arg_defaults=build_arg_defaults,
            ansible_cfg=data.get("ansible_cfg", ""),
            galaxy_servers=galaxy_servers,
            scm_servers=scm_servers,
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
                "ee_name": {
                    "type": "string",
                    "default": "ansible_sample_ee",
                    "description": "Name/tag for the EE image",
                },
                "base_image": {
                    "type": "string",
                    "default": "quay.io/fedora/fedora:41",
                    "description": "Base container image",
                },
                "registry": {
                    "type": "string",
                    "default": "ghcr.io",
                    "description": (
                        "Container registry hostname for the CI workflow (e.g. ghcr.io, quay.io)"
                    ),
                },
                "registry_tls_verify": {
                    "type": "boolean",
                    "default": True,
                    "description": (
                        "Whether to verify TLS certificates when accessing "
                        "container registries (login, pull, push, and image builds)"
                    ),
                },
                "image_name": {
                    "type": "string",
                    "default": "",
                    "description": (
                        "Image name for the CI workflow "
                        "(e.g. my-org/my-ee). Defaults to github.repository"
                    ),
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
                "build_arg_defaults": {
                    "type": "object",
                    "description": (
                        "Default ARG values for the EE image build "
                        "(e.g. ANSIBLE_GALAXY_CLI_COLLECTION_OPTS)"
                    ),
                    "additionalProperties": {"type": "string"},
                },
                "ansible_cfg": {
                    "type": "string",
                    "description": "Content for ansible.cfg file",
                    "default": "",
                },
                "galaxy_servers": {
                    "type": "array",
                    "items": GalaxyServer.to_schema(),
                    "description": (
                        "Galaxy server entries for ansible.cfg generation "
                        "and workflow token plumbing"
                    ),
                },
                "scm_servers": {
                    "type": "array",
                    "items": ScmServer.to_schema(),
                    "description": (
                        "SCM server entries for private Git collection "
                        "repositories and workflow token plumbing"
                    ),
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
_PY312 = "/usr/bin/python3.12"
_PY311 = "/usr/bin/python3.11"

OFFICIAL_EE_IMAGES: tuple[OfficialEEImage, ...] = (
    # AAP 2.5/2.6 uses Python 3.12
    OfficialEEImage("ansible-automation-platform-26", _PY312),
    OfficialEEImage("aap-26", _PY312),
    OfficialEEImage("ansible-automation-platform-25", _PY312),
    OfficialEEImage("aap-25", _PY311),
    # AAP 2.4 uses Python 3.11
    OfficialEEImage("ansible-automation-platform-24", _PY311),
    OfficialEEImage("aap-24", _PY311),
    # Broad registry prefixes (catch-all for unversioned official images)
    OfficialEEImage("registry.redhat.io/ansible-automation-platform", _PY312),
    OfficialEEImage("registry.redhat.io/aap", _PY311),
    # Named official EE images
    OfficialEEImage("ee-minimal-rhel", _PY311),
    OfficialEEImage("ee-supported-rhel", _PY311),
    OfficialEEImage("ee-29-rhel", _PY311),
    OfficialEEImage("ee-dellos", _PY311),
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
        ee_build_arg_defaults: Default ARG values for the EE container build.
        ee_ansible_cfg: Content for ansible.cfg file (for Automation Hub auth).
        is_official_ee: Whether the base image is an official Red Hat EE image.
        ee_python_path: Python interpreter path for the EE (varies by AAP version).
        ee_name_is_default: Whether ee_name is the unchanged default value.
        ee_registry: Container registry hostname for the CI workflow.
        ee_registry_tls_verify: Whether to verify TLS for container registry operations
            (login, pull, push, and image builds).
        ee_image_name: Image name for the CI workflow.
        ee_galaxy_servers: Galaxy server entries (list of dicts from GalaxyServer.as_dict()).
        ee_galaxy_token_vars: Pre-computed list of token env var names for servers
            with token_required=True.
        ee_scm_servers: SCM server entries (list of dicts from ScmServer.as_dict()).
        ee_scm_token_vars: Pre-computed list of token env var names from scm_servers.
        ee_file_name: Name of the EE definition file.
        scm_provider: SCM provider for documentation templates (github or gitlab).
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
    ee_build_arg_defaults: dict[str, str] = field(default_factory=dict)
    ee_ansible_cfg: str = ""
    is_official_ee: bool = False
    ee_python_path: str = DEFAULT_PYTHON_PATH
    ee_name_is_default: bool = True
    ee_registry: str = "ghcr.io"
    ee_registry_tls_verify: bool = True
    ee_image_name: str = ""
    ee_galaxy_servers: Sequence[dict[str, Any]] = field(default_factory=list)
    ee_galaxy_token_vars: Sequence[str] = field(default_factory=list)
    ee_scm_servers: Sequence[dict[str, Any]] = field(default_factory=list)
    ee_scm_token_vars: Sequence[str] = field(default_factory=list)
    ee_file_name: str = "execution-environment.yml"
    scm_provider: str = "github"
