"""Definitions for ansible-creator create action."""

from __future__ import annotations

import os

from importlib import import_module
from typing import TYPE_CHECKING

from yaml import parser, safe_load, scanner

from ansible_creator.config import ScaffolderConfig
from ansible_creator.exceptions import CreatorError
from ansible_creator.validators import SchemaValidator


if TYPE_CHECKING:
    from ansible_creator.config import Config
    from ansible_creator.output import Output


class Create:
    """Class representing ansible-creator create subcommand."""

    def __init__(self: Create, config: Config, output: Output) -> None:
        """Initialize the create action.

           Load and validate the content definition file.

        :param **args: A dictionary containing Create options.
        """
        self._file_path: str = config.file_path
        self.output: Output = output

    def run(self: Create) -> None:
        """Start scaffolding the specified content(s).

        Dispatch work to correct scaffolding class.

        :raises CreatorError: if scaffolder class cannot be loaded
        """
        self.output.debug("starting creator 'run'")

        content_def = self.load_config() or {}

        if not content_def.get("plugins"):
            self.output.critical("No content to scaffold. Exiting ansible-creator.")
        else:
            # validate loaded content definition against pre-defined schema
            self.validate_config(content_def)
            data = {
                "collection_path": content_def["collection"]["path"],
                "collection_name": content_def["collection"]["name"],
                "namespace": content_def["collection"]["namespace"],
            }

            for item in content_def["plugins"]:
                data.update(item)
                # start scaffolding plugins one by one
                if item["type"] not in ["action", "filter", "cache", "test"]:
                    try:
                        scaffolder_class = import_module(
                            f"ansible_creator.scaffolders.{item['type']}",
                        ).Scaffolder
                    except (AttributeError, ModuleNotFoundError) as exc:
                        msg = f"Unable to load scaffolder class for plugin type {item['type']}"
                        raise CreatorError(
                            msg,
                        ) from exc

                    self.output.debug(f"found scaffolder class {scaffolder_class}")

                    self.output.info(
                        f"scaffolding plugin {data['collection_name']}_{item['name']}"
                        f" of type {item['type']}",
                    )
                    scaffolder_class(
                        config=ScaffolderConfig(**data),
                        output=self.output,
                    ).run()

            self.output.note("all scaffolding tasks completed! \U0001f389")

    def load_config(self: Create) -> dict:
        """Load the content definition file.

        :returns: A dictionary of content(s) to scaffold.

        :raises CreatorError: If content definition file is missing or has errors.
        """
        content_def = {}
        file_path = os.path.abspath(
            os.path.expanduser(os.path.expandvars(self._file_path)),
        )

        self.output.info("attempting to load the content definition file {file_path}")
        try:
            with open(file_path, encoding="utf-8") as content_file:
                data = safe_load(content_file)
                content_def = data
        except FileNotFoundError as exc:
            msg = (
                "Could not detect the content definition file."
                f"\n{'':<9}Use -f to specify a different location for it."
            )
            raise CreatorError(
                msg,
            ) from exc
        except (parser.ParserError, scanner.ScannerError) as exc:
            msg = "Error occurred while parsing the content definition file:"
            raise CreatorError(
                msg,
            ) from exc

        return content_def

    def validate_config(self: Create, content_def: dict) -> None:
        """Validate the content definition against a pre-defined jsonschema.

        :param content_def: A dictionary of content(s) to scaffold.

        :raises CreatorError: If schema validation errors were found.
        """
        self.output.info("validating the loaded content definition")
        errors = SchemaValidator(data=content_def, criteria="content.json").validate()

        if errors:
            raise CreatorError(
                "The following errors were found while validating:\n\n"
                + "\n".join(errors),
            )
