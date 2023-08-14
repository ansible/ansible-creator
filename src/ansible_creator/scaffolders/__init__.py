"""A package containing all scaffolder classes supported by ansible-creator."""

import os
from abc import ABC, abstractmethod

import black
import yaml

from ansible_creator.exceptions import CreatorError
from ansible_creator.constants import (
    OPTION_CONDITIONALS,
    OPTION_METADATA,
    VALID_ANSIBLEMODULE_ARGS,
)


class ScaffolderBase(ABC):
    """Base class for all scaffolders."""

    def __init__(self, **args):
        """Instantiate an object of this class.

        :param **args: A dictionary containing target collection and plugin information.
        """
        self.collection_path = args["collection"]["path"]
        self.namespace = args["collection"]["namespace"]
        self.collection_name = args["collection"]["name"]
        self.plugin_name = args["name"]
        self.plugin_type = args["type"]
        self.path_to_docstring = args.get("docstring", "")  # docstring is optional
        self.docstring = self.load_docstring()

    @abstractmethod
    def run(self):
        """Start scaffolding a plugin type."""

    def load_docstring(self):
        """Load docstring from a file or existing module and return.

        :returns: The docstring as a string.
        :raises CreatorError: When the docstring file cannot be found.
        """
        docstring = {}

        if self.path_to_docstring:
            # attempt to load docstring from specified file (if provided)
            abs_docstring = os.path.abspath(
                os.path.expanduser(os.path.expandvars(self.path_to_docstring))
            )
            # if path to docstring exists load and return its contents.
            try:
                with open(abs_docstring, encoding="utf-8") as ds_file:
                    docstring = ds_file.read()
            except FileNotFoundError as exc:
                raise CreatorError(
                    f"Could not detect the specified docstring file {abs_docstring}"
                ) from exc
        else:
            # TO-DO: check if plugin file already exists and attempt to read docstring from it
            raise CreatorError(
                f"Path to docstring is not provided for plugin {self.plugin_name} and\n"
                "loading docstring from existing plugin is not yet supported."
            )
        return docstring

    def generate_argspec(self):
        """Convert docstring into Ansible plugin argspec.

        :returns: A black formatted string representing the argspec.
        """

        def build_argspec(doc_obj, argspec):
            """Recursively build argspec from doc obj.

            :param doc_obj: A dictionary representing YAML loaded documentation.
            :param argspec: A dictionary containing final argspec.
            """
            options_obj = doc_obj.get("options")
            for okey, ovalue in options_obj.items():
                argspec[okey] = {}
                for metakey in list(ovalue):
                    if metakey == "suboptions":
                        argspec[okey].update({"options": {}})
                        suboptions_obj = {"options": ovalue["suboptions"]}
                        # recursively call build_argspec
                        build_argspec(
                            doc_obj=suboptions_obj, argspec=argspec[okey]["options"]
                        )
                    elif metakey in OPTION_METADATA + OPTION_CONDITIONALS:
                        argspec[okey].update({metakey: ovalue[metakey]})

        argspec = {}
        final_spec = {}
        doc_obj = yaml.safe_load(self.docstring)

        build_argspec(doc_obj, argspec)
        final_spec.update({"argument_spec": argspec})

        for item in doc_obj:
            if item in VALID_ANSIBLEMODULE_ARGS:
                final_spec.update({item: doc_obj[item]})

        return black.format_str(
            str(final_spec["argument_spec"]),
            mode=black.Mode(
                target_versions={black.TargetVersion.PY310},
            ),
        ).strip()
