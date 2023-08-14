"""Definitions for ansible-creator create action."""

import os
from copy import deepcopy
from importlib import import_module

import yaml
from ansible_creator.validators import SchemaValidator
from ansible_creator.exceptions import CreatorError


class CreatorCreate:
    """Class representing ansible-creator create subcommand."""

    def __init__(self, **args):
        """Initialize the create action.

           Load and validate the content definition file.

        :param **args: A dictionary containing Create options.
        """
        self.file_path = args["file"]

    def run(self):
        """Start scaffolding the specified content(s).

           Dispatch work to correct scaffolding class.

        :raises CreatorError: If content definition is empty.
        """
        content_def = self.load_config()
        if not content_def.get("plugins"):
            raise CreatorError(
                "WARNING: No content to scaffold. Exiting ansible-creator."
            )

        # validate loaded content definition against pre-defined schema
        self.validate_config(content_def)

        for item in content_def["plugins"]:
            data = deepcopy(item)
            data.update({"collection": content_def["collection"]})
            # start scaffolding plugins one by one
            if item["type"] not in ["action", "filter", "cache", "test"]:
                scaffolder_class = getattr(
                    import_module(f"ansible_creator.scaffolders.{item['type']}"),
                    "Scaffolder",
                )
                scaffolder_class(**data).run()

    def load_config(self):
        """Load the content definition file.

        :returns: A dictionary of content(s) to scaffold.

        :raises CreatorError: If content definition file is missing or has errors.
        """
        content_def = {}
        file_path = os.path.abspath(
            os.path.expanduser(os.path.expandvars(self.file_path))
        )
        try:
            with open(file_path, encoding="utf-8") as content_file:
                data = yaml.safe_load(content_file)
                content_def = data
        except FileNotFoundError as exc:
            raise CreatorError(
                "Could not detect the content definition file. "
                "Use -f to specify a different location for it.\n"
            ) from exc
        except (yaml.parser.ParserError, yaml.scanner.ScannerError) as exc:
            raise CreatorError(
                "Error occurred while parsing the content definition file:\n"
            ) from exc

        return content_def

    def validate_config(self, content_def):
        """Validate the content definition against a pre-defined jsonschema.

        :param content_def: A dictionary of content(s) to scaffold.

        :raises CreatorError: If schema validation errors were found.
        """
        errors = SchemaValidator(data=content_def, criteria="content.json").validate()

        if errors:
            raise CreatorError(
                f"The following errors were found while validating {self.file_path}:\n\n"
                + "\n".join(errors)
            )
