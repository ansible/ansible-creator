"""Definitions for ansible-creator create action."""

import os
import yaml

from ..utils import creator_exit
from ..validators import JSONSchemaValidator


class AnsibleCreatorCreate:
    """Class representing ansible-creator create subcommand."""

    def __init__(self, **args):
        """Initialize the create action.

           Load and validate the content definition file.

        :param **args: Arguments passed for the create action
        """
        self.file_path = args["file"]
        self.content_def = self.load_config(self.file_path)
        if not self.content_def:
            creator_exit(
                status="WARNING",
                message=(
                    "The content definition file seems to be empty. No content to scaffold."
                ),
            )
        else:
            # fail early is schema validation fails for any reason
            self.validate_config(self.content_def)

    def run(self):
        """Start scaffolding the specified content(s)."""

    def load_config(self, file_path):
        """Load the content definition file.

        :param file_path: Path to the content definition file.
        :returns: A dictionary of content(s) to scaffold.
        """
        content_def = {}
        file_path = os.path.abspath(os.path.expanduser(os.path.expandvars(file_path)))
        try:
            with open(file_path, encoding="utf-8") as content_file:
                data = yaml.safe_load(content_file)
                content_def = data
        except FileNotFoundError:
            creator_exit(
                status="FAILURE",
                message=(
                    f"Could not detect '{file_path}' file in this directory.\n"
                    "Use -f to specify a different location for the content definition file."
                ),
            )
        except (yaml.parser.ParserError, yaml.scanner.ScannerError) as exc:
            creator_exit(
                status="FAILURE",
                message=f"Error occurred while parsing the definition file:\n{str(exc)}",
            )

        return content_def

    def validate_config(self, content_def):
        """Validate the content definition against a pre-defined jsonschema.

        :param content_def: A dictionary of content(s) to scaffold.
        :returns: True if no validation exceptions occur else False
        """
        try:
            errors = JSONSchemaValidator(
                data=content_def, criteria="manifest.json"
            ).validate()
        except Exception as exc:
            creator_exit(status="FAILURE", message=f"{exc}")

        if errors:
            creator_exit(
                status="FAILURE",
                message="The following schema validation errors were found:\n\n"
                + "\n".join(errors),
            )
