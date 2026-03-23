"""Definitions for ansible-creator init action."""

from __future__ import annotations

import dataclasses
import json
import shutil
import uuid

from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from ansible_creator.exceptions import CreatorError
from ansible_creator.templar import Templar
from ansible_creator.types import (
    EECollection,
    EEConfig,
    TemplateData,
    validate_collection_name,
    validate_collection_type,
    validate_source_url,
)
from ansible_creator.utils import Copier, Walker, ask_yes_no


if TYPE_CHECKING:
    from ansible_creator.config import Config
    from ansible_creator.output import Output

GIT_URL_PROTOCOLS = ("https://", "http://", "git://", "ssh://", "file://")  # NOSONAR


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

        # Build the canonical EEConfig from JSON, file, or defaults, then
        # layer CLI flag overrides on top.
        self._ee_config: EEConfig = self._build_ee_config(config)

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

    @staticmethod
    def _is_official_ee_image(image: str) -> bool:
        """Check if the image is an official Red Hat EE image.

        Official EE images have ansible-core/runner pre-installed and
        use microdnf as the package manager.

        Args:
            image: The container image name/URL.

        Returns:
            True if the image matches any official EE pattern.
        """
        from ansible_creator.types import OFFICIAL_EE_IMAGES  # noqa: PLC0415

        return any(entry.pattern in image for entry in OFFICIAL_EE_IMAGES)

    @staticmethod
    def _get_ee_python_path(image: str) -> str:
        """Get the Python interpreter path for a base image.

        For official EE images, returns the version-specific path
        (e.g. AAP 2.6 uses Python 3.12, AAP 2.4/2.5 uses 3.11).
        For non-official images, returns the generic ``/usr/bin/python3``.

        Args:
            image: The container image name/URL.

        Returns:
            The Python interpreter path for the image.
        """
        from ansible_creator.types import (  # noqa: PLC0415
            DEFAULT_PYTHON_PATH,
            OFFICIAL_EE_IMAGES,
        )

        for entry in OFFICIAL_EE_IMAGES:
            if entry.pattern in image:
                return entry.python_path
        return DEFAULT_PYTHON_PATH

    def _build_ee_config(self, config: Config) -> EEConfig:
        """Build the final EEConfig by merging JSON/file config with CLI flags.

        Args:
            config: The application configuration.

        Returns:
            A fully resolved EEConfig instance.
        """
        ee_cfg = self._resolve_ee_config(config)

        # CLI flags override values from config JSON/file.
        overrides: dict[str, Any] = {}
        if config.base_image != "quay.io/fedora/fedora:41":
            overrides["base_image"] = config.base_image
        if config.ee_name != "ansible_sample_ee":
            overrides["name"] = config.ee_name
        if config.ee_collections:
            overrides["collections"] = tuple(
                self._parse_single_collection(c) for c in config.ee_collections
            )
        if config.ee_python_deps:
            overrides["python_deps"] = tuple(config.ee_python_deps)
        if config.ee_system_packages:
            overrides["system_packages"] = tuple(config.ee_system_packages)

        if overrides:
            ee_cfg = dataclasses.replace(ee_cfg, **overrides)

        # Auto-detect official EE images and set microdnf as package manager.
        if "package_manager_path" not in ee_cfg.options and self._is_official_ee_image(
            ee_cfg.base_image
        ):
            updated_opts = {**ee_cfg.options, "package_manager_path": "/usr/bin/microdnf"}
            ee_cfg = dataclasses.replace(ee_cfg, options=updated_opts)

        return ee_cfg

    @staticmethod
    def _resolve_ee_config(config: Config) -> EEConfig:
        """Resolve EE configuration from inline JSON or a config file.

        Args:
            config: The application configuration.

        Returns:
            An EEConfig instance (empty defaults if neither source is provided).

        Raises:
            CreatorError: If both ee_config and ee_config_file are set.
        """
        if config.ee_config and config.ee_config_file:
            msg = "Cannot specify both --ee-config and --ee-config-file"
            raise CreatorError(msg)
        if config.ee_config:
            return Init._parse_ee_config_json(config.ee_config)
        if config.ee_config_file:
            return Init._load_ee_config_file(config.ee_config_file)
        return EEConfig()

    @staticmethod
    def _parse_ee_config_json(json_str: str) -> EEConfig:
        """Parse an inline JSON string into an EEConfig.

        Args:
            json_str: JSON string containing EE parameters.

        Returns:
            A validated EEConfig instance.

        Raises:
            CreatorError: If the JSON is invalid or not an object.
        """
        try:
            data: Any = json.loads(json_str)
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON in --ee-config: {e}"
            raise CreatorError(msg) from e
        if not isinstance(data, dict):
            msg = "--ee-config must be a JSON object, not a list or scalar"
            raise CreatorError(msg)
        return EEConfig.from_dict(data)

    @staticmethod
    def _load_ee_config_file(config_path: str) -> EEConfig:
        """Load EE configuration from a JSON or YAML file.

        Args:
            config_path: Path to the config file.

        Returns:
            A validated EEConfig instance.

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
                data: Any = json.loads(content)
            except json.JSONDecodeError as e:
                msg = f"Invalid JSON in EE config file {config_path}: {e}"
                raise CreatorError(msg) from e
            if not isinstance(data, dict):
                msg = (
                    f"EE config file {config_path} must contain a JSON object, not a list or scalar"
                )
                raise CreatorError(msg)
            return EEConfig.from_dict(data)
        try:
            yaml_data: Any = yaml.safe_load(content) or {}
        except yaml.YAMLError as e:
            msg = f"Invalid YAML in EE config file {config_path}: {e}"
            raise CreatorError(msg) from e
        if not isinstance(yaml_data, dict):
            msg = f"EE config file {config_path} must contain a YAML mapping, not a list or scalar"
            raise CreatorError(msg)
        return EEConfig.from_dict(yaml_data)

    def _is_git_url_collection(self, col: str) -> bool:
        """Check if a collection string is a Git URL.

        A Git URL collection is one where the collection name itself is a URL,
        not a standard namespace.name format with a URL as the source field.

        Args:
            col: Collection string to check.

        Returns:
            True if the string appears to be a Git URL collection name.
        """
        # URL protocols at the start of the string
        if col.startswith(GIT_URL_PROTOCOLS):
            return True
        # SSH-style git@host:path or git@host/path
        return bool(col.startswith("git@"))

    def _parse_single_collection(self, col: str) -> EECollection:
        """Parse a single collection string into an EECollection.

        Supports two formats:
        1. Standard: 'namespace.name[:version[:type[:source]]]'
        2. Git URL: 'https://...path/namespace.name[:version]:git'

        Args:
            col: Collection string to parse.

        Returns:
            A validated EECollection instance.
        """
        if self._is_git_url_collection(col):
            return self._parse_git_url_collection(col)

        parts = col.split(":", maxsplit=3)
        col_name = parts[0]

        validate_collection_name(col_name)
        version = ""
        col_type = ""
        source = ""

        if len(parts) > 1 and parts[1]:
            version = parts[1]

        if len(parts) > 2 and parts[2]:  # noqa: PLR2004
            col_type = validate_collection_type(parts[2])

        if len(parts) > 3 and parts[3]:  # noqa: PLR2004
            validate_source_url(parts[3])
            source = parts[3]

        return EECollection(name=col_name, version=version, type=col_type, source=source)

    def _parse_git_url_collection(self, col: str) -> EECollection:
        """Parse a Git URL collection string.

        Format: 'https://[token@]host/path/namespace.name[:version]:git'

        Args:
            col: Git URL collection string.

        Returns:
            An EECollection with the URL as the name and type=git.
        """
        parts = col.rsplit(":", maxsplit=2)
        last_part = parts[-1].lower()

        if last_part == "git":
            if len(parts) == 2:  # noqa: PLR2004
                return EECollection(name=parts[0], type="git")
            return EECollection(name=parts[0], version=parts[1], type="git")

        if len(parts) == 3 and not parts[-1].startswith("/"):  # noqa: PLR2004
            url = f"{parts[0]}:{parts[1]}"
            return EECollection(name=url, version=parts[-1], type="git")

        if len(parts) == 2 and parts[1].startswith("//"):  # noqa: PLR2004
            return EECollection(name=col, type="git")

        return EECollection(name=col, type="git")

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
        ec = self._ee_config
        template_data = TemplateData(
            namespace=self._namespace,
            collection_name=self._collection_name,
            creator_version=self._creator_version,
            dev_file_name=self.unique_name_in_devfile(),
            role_name=self._role_name,
            ee_base_image=ec.base_image,
            ee_collections=[c.as_dict() for c in ec.collections],
            ee_python_deps=list(ec.python_deps),
            ee_system_packages=list(ec.system_packages),
            ee_name=ec.name,
            ee_additional_build_files=list(ec.additional_build_files),
            ee_additional_build_steps=ec.additional_build_steps,
            ee_options=ec.options,
            ee_ansible_cfg=ec.ansible_cfg,
            is_official_ee=self._is_official_ee_image(ec.base_image),
            ee_python_path=self._get_ee_python_path(ec.base_image),
            ee_name_is_default=ec.name == "ansible_sample_ee",
            ee_automation_hub_url=ec.automation_hub_url,
            ee_private_hub_url=ec.private_hub_url,
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
        Respects the ``--no-overwrite`` / ``--overwrite`` flags.
        """
        if self._project != "execution_env":
            return

        ansible_cfg_path = self._init_path / "ansible.cfg"
        ansible_cfg_content: str | None = None

        if self._ee_config.ansible_cfg:
            ansible_cfg_content = self._ee_config.ansible_cfg
        elif self._is_official_ee_image(self._ee_config.base_image):
            ansible_cfg_content = self._render_ansible_cfg()

        if ansible_cfg_content is None:
            return

        if ansible_cfg_path.exists() and self._no_overwrite:
            self.output.warning(msg=f"Skipping existing {ansible_cfg_path} (--no-overwrite)")
            return

        ansible_cfg_path.write_text(ansible_cfg_content, encoding="utf-8")
        self.output.debug(msg=f"Writing to {ansible_cfg_path}")

    def _render_ansible_cfg(self) -> str:
        """Render an ansible.cfg with predefined galaxy server sections.

        Tokens are never written here — they are passed via environment
        variables (ANSIBLE_GALAXY_SERVER_<ID>_TOKEN) at build time.

        Returns:
            The rendered ansible.cfg content.
        """
        ec = self._ee_config
        has_private_hub = bool(ec.private_hub_url)

        server_list = ["automation_hub"]
        if has_private_hub:
            server_list.append("private_hub")
        server_list.append("galaxy")

        lines = [
            "[galaxy]",
            f"server_list = {', '.join(server_list)}",
            "",
            "[galaxy_server.automation_hub]",
            f"url = {ec.automation_hub_url}",
        ]

        if "console.redhat.com" in ec.automation_hub_url:
            lines.append(
                "auth_url = https://sso.redhat.com/auth/realms/redhat-external"
                "/protocol/openid-connect/token",
            )

        lines.append("")

        if has_private_hub:
            lines.extend(
                [
                    "[galaxy_server.private_hub]",
                    f"url = {ec.private_hub_url}",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    "# [galaxy_server.private_hub]",
                    "# Uncomment and set your Private Automation Hub URL, or pass",
                    "# private_hub_url via --ee-config to enable this section.",
                    "# url = https://your-pah.example.com/api/galaxy/content/published/",
                    "",
                ]
            )

        lines.extend(
            [
                "[galaxy_server.galaxy]",
                "url = https://galaxy.ansible.com/",
                "",
            ]
        )

        return "\n".join(lines)
