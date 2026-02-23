"""CLI subcommand for ``ansible-creator schema``.

Thin wrapper that delegates to :mod:`ansible_creator.schema` for the
actual schema logic.
"""

from __future__ import annotations

import json
import sys

from typing import TYPE_CHECKING

from ansible_creator.schema import as_dict


if TYPE_CHECKING:
    from ansible_creator.config import Config


class Schema:
    """CLI handler for the ``schema`` subcommand.

    The heavy lifting lives in :mod:`ansible_creator.schema`; this class
    only satisfies the subcommand dispatch protocol
    (``__init__(config)`` + ``run()``).
    """

    def __init__(self, config: Config) -> None:
        """Initialize the schema action.

        The *config* parameter is required by the subcommand dispatch
        protocol (``Cli.run`` instantiates every subcommand with
        ``cls(config=config)``), but the schema subcommand does not
        need any configuration.

        Args:
            config: App configuration object (unused).
        """

    def run(self) -> None:
        """Generate and output the CLI schema."""
        schema = as_dict()
        output = json.dumps(schema, indent=2, default=str)
        sys.stdout.write(output + "\n")
