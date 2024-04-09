"""Definitions for ansible-creator docs action."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ansible_creator.docs import load_galaxy, process, update_readme
from ansible_creator.templar import Templar


if TYPE_CHECKING:
    from ansible_creator.config import Config
    from ansible_creator.output import Output


class Docs:
    """Class representing ansible-creator docs subcommand."""

    def __init__(
        self: Docs,
        config: Config,
    ) -> None:
        """Initialize the docs action.

        :param config: App configuration object.
        """
        self._branch_name: str = config.branch_name
        self._collection_path: Path = Path(config.collection_path)
        self._creator_version = config.creator_version
        self._templar = Templar()
        self.output: Output = config.output

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
            f"collection {namespace}.{collection_name} "
            f"documentation updated at {self._collection_path}",
        )
