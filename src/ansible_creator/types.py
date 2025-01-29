# noqa: A005
"""A home for shared types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ansible_creator.constants import GLOBAL_TEMPLATE_VARS


if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass
class TemplateData:
    """Dataclass representing the template data.

    Attributes:
        resource_type: The type of resource to be scaffolded.
        plugin_type: The type of plugin to be scaffolded.
        plugin_name: The name of the plugin to be scaffolded.
        additions: A dictionary containing additional data to add to the gitignore.
        collection_name: The name of the collection.
        creator_version: The version of the creator.
        dev_container_image: The devcontainer image.
        dev_file_image: The devfile image.
        dev_file_name: The unique name entry in devfile.
        namespace: The namespace of the collection.
        execution_environment_image: The execution environment image.
        recommended_extensions: A list of recommended VsCode extensions.
    """

    resource_type: str = ""
    plugin_type: str = ""
    plugin_name: str = "hello_world"
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
