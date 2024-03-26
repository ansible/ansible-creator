"""Definitions for ansible-creator docs action."""

from __future__ import annotations

import contextlib
import logging
import os

from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from ansible_creator.docs import (
    IGNORE_FILES,
    SUBDIRS,
    convert_descriptions,
    ensure_list,
    fragment_loader,
    handle_simple,
    jinja_environment,
    load_galaxy,
    plugin_docs,
    string_types,
    to_text,
    update_readme,
)
from ansible_creator.templar import Templar


if TYPE_CHECKING:
    from ansible_creator.config import Config
    from ansible_creator.output import Output


def process(
    collection: str,
    path: Path,
):  # pylint: disable-msg=too-many-locals,too-many-branches
    """Process the files in each subdirectory.

    :param collection: The collection name
    :type collection: str
    :param path: The path to the collection
    :type path: Path
    :return: A mapping of plugins to plugin types
    """
    template = jinja_environment()
    docs_path = Path(path, "docs")
    if docs_path.is_dir():
        logging.info("Purging existing rst files from directory %s", docs_path)
        for entry in docs_path.glob("*.rst"):
            entry.unlink()
    logging.info("Making docs directory %s", docs_path)
    Path(docs_path).mkdir(parents=True, exist_ok=True)

    content = {}

    for subdir in SUBDIRS:  # pylint: disable-msg=too-many-nested-blocks
        plugin_type = "module" if subdir == "modules" else subdir

        dirpath = Path(path, "plugins", subdir)
        if dirpath.is_dir():
            content[subdir] = {}
            logging.info("Process content in %s", dirpath)
            for filename in os.listdir(dirpath):
                if filename.endswith(".py") and filename not in IGNORE_FILES:
                    fullpath = Path(dirpath, filename)
                    logging.info("Processing %s", fullpath)
                    (
                        doc,
                        examples,
                        return_docs,
                        metadata,
                    ) = plugin_docs.get_docstring(to_text(fullpath), fragment_loader)
                    if doc is None and subdir in ["filter", "test"]:
                        name_only = filename.rsplit(".")[0]
                        combined_ptype = f"{name_only} {subdir}"
                        content[combined_ptype] = handle_simple(
                            collection,
                            fullpath,
                            subdir,
                        )
                    elif doc:
                        doc["plugin_type"] = plugin_type

                        if return_docs:
                            # Seems a recent change in devel makes this
                            # return a dict not a yaml string.
                            if isinstance(return_docs, dict):
                                doc["return_docs"] = return_docs
                            else:
                                doc["return_docs"] = yaml.safe_load(return_docs)
                            convert_descriptions(doc["return_docs"])

                        doc["metadata"] = (metadata,)
                        if isinstance(examples, string_types):
                            doc["plain_examples"] = examples.strip()
                        else:
                            doc["examples"] = examples

                        doc["module"] = f"{collection}." "{plugin_name}".format(
                            plugin_name=doc.get(plugin_type, doc.get("name")),
                        )
                        doc["author"] = ensure_list(doc["author"])
                        doc["description"] = ensure_list(doc["description"])
                        with contextlib.suppress(KeyError):
                            convert_descriptions(doc["options"])

                        module_rst_path = Path(
                            path,
                            "docs",
                            doc["module"] + f"_{plugin_type}" + ".rst",
                        )

                        with open(
                            module_rst_path,
                            "w",
                            encoding="utf8",
                        ) as doc_file:
                            doc_file.write(template.render(doc))
                        content[subdir][doc["module"]] = {
                            "has_rst": True,
                            "comment": doc["short_description"],
                        }
    return content


class Docs:
    """Class representing ansible-creator docs subcommand."""

    def __init__(
        self: Docs,
        config: Config,
        output: Output,
    ) -> None:
        """Initialize the docs action.

        :param kwargs: Arguments passed for the docs action
        """
        self._branch_name: str = config.branch_name
        self._collection_path: Path = Path(config.collection_path)
        self._creator_version = config.creator_version
        self._templar = Templar()
        self.output: Output = output

    def run(self: Docs) -> None:
        """Regenerate collection documentation from plugins."""
        col_path = Path(self._collection_path)
        self.output.debug(msg=f"final collection path set to {col_path}")

        galaxy = load_galaxy(path=col_path)
        gh_url = galaxy["repository"]
        self.output.debug(msg="Setting GitHub repository url to {gh_url}")
        namespace = galaxy["namespace"]
        collection_name = galaxy["name"]
        collection = f"{namespace}.{collection_name}"

        tempdir = None
        content = process(collection=collection, path=col_path)
        if tempdir is not None:
            tempdir.cleanup()

        update_readme(
            content=content,
            path=self._collection_path,
            gh_url=gh_url,
            branch_name=self._branch_name,
        )

        self.output.note(
            f"collection {namespace}.{collection_name} documentation updated at {self._collection_path}",
        )
