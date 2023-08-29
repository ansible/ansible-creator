"""A package containing all scaffolder classes supported by ansible-creator."""

from __future__ import annotations

import ast
import os

from abc import ABC, abstractmethod

import yaml

from black import format_str, mode

from ansible_creator.constants import (
    OPTION_CONDITIONALS,
    OPTION_METADATA,
    VALID_ANSIBLEMODULE_ARGS,
)
from ansible_creator.exceptions import CreatorError
from ansible_creator.templar import Templar
from ansible_creator.utils import copy_container


class ScaffolderBase(ABC):
    """Base class for all scaffolders."""

    def __init__(self: ScaffolderBase, **kwargs: str) -> None:
        """Instantiate an object of this class.

        :param **args: A dictionary containing target collection and plugin information.
        """
        self._templar: Templar = Templar()
        self.collection_path: str = os.path.abspath(
            os.path.expanduser(os.path.expandvars(kwargs["collection_path"])),
        )
        self.namespace: str = kwargs["collection_namespace"]
        self.collection_name: str = kwargs["collection_name"]
        self.plugin_name: str = kwargs["name"]
        self.plugin_type: str = kwargs["type"]
        self.path_to_docstring: str = kwargs.get("docstring", "")
        self.docstring: str = self.load_docstring()

    @abstractmethod
    def run(self: ScaffolderBase) -> None:
        """Start scaffolding a plugin type."""

    def load_docstring(self: ScaffolderBase) -> str:
        """Load docstring from a file or existing module and return.

        :returns: The docstring as a string.
        :raises CreatorError: When the docstring cannot be loaded.
        """
        docstring: str = ""

        if self.path_to_docstring:
            # attempt to load docstring from specified file (if provided)
            abs_docstring = os.path.abspath(
                os.path.expanduser(os.path.expandvars(self.path_to_docstring)),
            )
            # if path to docstring exists load and return its contents.
            try:
                with open(abs_docstring, encoding="utf-8") as ds_file:
                    docstring = ds_file.read()
            except FileNotFoundError as exc:
                msg = f"Could not detect the specified docstring file {abs_docstring}"
                raise CreatorError(
                    msg,
                ) from exc
        else:
            # check if plugin file already exists and attempt to read docstring from it
            module_path = (
                f"{self.collection_path}/plugins/modules/"
                f"{self.collection_name}_{self.plugin_name}.py"
            )
            if os.path.exists(module_path):
                with open(module_path, encoding="utf-8") as module_file:
                    module_content = module_file.read()
                for node in ast.walk(ast.parse(module_content)):
                    if (
                        isinstance(node, ast.Assign)
                        and getattr(node.targets[0], "id", "") == "DOCUMENTATION"
                    ):
                        docstring = getattr(node.value, "s", "").strip()
            else:
                msg = (
                    f"Unable to load docstring for plugin {self.plugin_name}.\n"
                    f"{'':<9}Path to a docstring not provided and plugin file does not "
                    "already exist."
                )
                raise CreatorError(msg)
        return docstring

    def generate_argspec(self: ScaffolderBase) -> str:
        """Convert docstring into Ansible plugin argspec.

        :returns: A black formatted string representing the argspec.
        """

        def build_argspec(doc_obj: dict, argspec: dict) -> None:
            """Recursively build argspec from doc obj.

            :param doc_obj: A dictionary representing YAML loaded documentation.
            :param argspec: A dictionary containing final argspec.
            """
            options_obj = doc_obj.get("options") or {}
            for okey, ovalue in options_obj.items():
                argspec[okey] = {}
                for metakey in list(ovalue):
                    if metakey == "suboptions":
                        argspec[okey].update({"options": {}})
                        suboptions_obj = {"options": ovalue["suboptions"]}
                        # recursively call build_argspec
                        build_argspec(
                            doc_obj=suboptions_obj,
                            argspec=argspec[okey]["options"],
                        )
                    elif metakey in OPTION_METADATA + OPTION_CONDITIONALS:
                        argspec[okey].update({metakey: ovalue[metakey]})

        argspec: dict = {}
        final_spec = {}
        doc_obj = yaml.safe_load(self.docstring)

        build_argspec(doc_obj, argspec)
        final_spec.update({"argument_spec": argspec})

        for item in doc_obj:
            if item in VALID_ANSIBLEMODULE_ARGS:
                final_spec.update({item: doc_obj[item]})

        return format_str(
            str(final_spec["argument_spec"]),
            mode=mode.Mode(
                target_versions={mode.TargetVersion.PY310},
            ),
        ).strip()


class NetworkScaffolderBase(ScaffolderBase):
    """Base scaffolder class for network content plugins."""

    def __init__(self: NetworkScaffolderBase, **kwargs: str) -> None:
        """Instantiate an object of this class.

        :param args: A dictionary containing scaffolding data.
        """
        super().__init__(**kwargs)
        self.import_path = (
            f"ansible_collections.{self.namespace}.{self.collection_name}."
            "plugins.module_utils.network"
        )
        self.template_data = {
            "argspec": str(self.generate_argspec()),
            "import_path": self.import_path,
            "namespace": self.namespace,
            "collection_name": self.collection_name,
            "resource": self.plugin_name,
            "network_os": self.collection_name,
            "documentation": self.docstring,
        }

    @abstractmethod
    def run(self: NetworkScaffolderBase) -> None:
        """Start scaffolding common dirs and files for network content plugins."""
        copy_container(
            source="module_network_base",
            dest=self.collection_path,
            templar=self._templar,
            template_data=self.template_data,
            allow_overwrite=[
                "plugins/module_utils/network/network_os/argspec/resource/resource.py.j2",
                "plugins/modules/network_os_resource.py.j2",
            ],
        )
