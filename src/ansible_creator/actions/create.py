"""Definitions for ansible-creator create action."""

from __future__ import annotations

import logging
import os

from copy import deepcopy
from importlib import import_module

from yaml import parser, safe_load, scanner

from ansible_creator.constants import MessageColors
from ansible_creator.exceptions import CreatorError
from ansible_creator.validators import SchemaValidator


logger = logging.getLogger("ansible-creator")


class CreatorCreate:
    """Class representing ansible-creator create subcommand."""

    def __init__(self: CreatorCreate, **kwargs: str) -> None:
        """Initialize the create action.

           Load and validate the content definition file.

        :param **args: A dictionary containing Create options.
        """
        self.file_path: str = kwargs["file"]

    def run(self: CreatorCreate) -> None:
        """Start scaffolding the specified content(s).

        Dispatch work to correct scaffolding class.

        :raises CreatorError: if scaffolder class cannot be loaded
        """
        logger.debug("starting creator 'run'")

        content_def = self.load_config() or {}

        if not content_def.get("plugins"):
            logger.critical("No content to scaffold. Exiting ansible-creator.")
        else:
            # validate loaded content definition against pre-defined schema
            self.validate_config(content_def)

            for item in content_def["plugins"]:
                data = deepcopy(item)
                data.update(
                    {
                        "collection_" + k: v
                        for k, v in content_def["collection"].items()
                    },
                )
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

                    logger.debug("found scaffolder class %s", scaffolder_class)

                    plugin_name = (
                        f"{MessageColors['OKGREEN']}"
                        f"{data['collection_name']}_{item['name']}"
                        f"{MessageColors['ENDC']}"
                    )

                    logger.info(
                        "scaffolding plugin %s of type %s",
                        plugin_name,
                        item["type"],
                    )
                    scaffolder_class(**data).run()

            logger.info("all scaffolding tasks completed! \U0001f389")

    def load_config(self: CreatorCreate) -> dict:
        """Load the content definition file.

        :returns: A dictionary of content(s) to scaffold.

        :raises CreatorError: If content definition file is missing or has errors.
        """
        content_def = {}
        file_path = os.path.abspath(
            os.path.expanduser(os.path.expandvars(self.file_path)),
        )

        logger.info("attempting to load the content definition file %s", file_path)
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

    def validate_config(self: CreatorCreate, content_def: dict) -> None:
        """Validate the content definition against a pre-defined jsonschema.

        :param content_def: A dictionary of content(s) to scaffold.

        :raises CreatorError: If schema validation errors were found.
        """
        logger.info("validating the loaded content definition")
        errors = SchemaValidator(data=content_def, criteria="content.json").validate()

        if errors:
            raise CreatorError(
                "The following errors were found while validating:\n\n"
                + "\n".join(errors),
            )
