"""Migrate subcommand argument parsing for ansible-creator."""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    import argparse

    from ansible_creator.arg_parser import SubParser


class MigrateParserMixin:
    """Mixin providing migrate subcommand parsers.

    Attributes:
        migrate_parser: Parser for the migrate subcommand.
    """

    migrate_parser: argparse.ArgumentParser | None

    def _add_args_common(self, parser: argparse.ArgumentParser) -> None:
        """Add common arguments to the parser.

        Args:
            parser: The parser to add common arguments to
        """

    def _add_overwrite(self, parser: argparse.ArgumentParser) -> None:
        """Add overwrite arguments to the parser.

        Args:
            parser: The parser to add overwrite arguments to
        """

    def _migrate(self, subparser: SubParser[argparse.ArgumentParser]) -> None:
        """Migrate existing Ansible content into newer layouts.

        Args:
            subparser: The subparser to add migrate to
        """
        parser = subparser.add_parser(
            "migrate",
            help="Migrate existing Ansible content into newer layouts.",
        )
        self.migrate_parser = parser
        migrate_sub = parser.add_subparsers(
            dest="migrate_type",
            metavar="migrate-type",
            required=False,
        )
        self._migrate_molecule(subparser=migrate_sub)

    def _migrate_molecule(self, subparser: SubParser[argparse.ArgumentParser]) -> None:
        """Migrate ansible-test integration targets into Molecule scenarios.

        Args:
            subparser: The subparser to add molecule migrate to
        """
        parser = subparser.add_parser(
            "molecule",
            help=(
                "Move ansible-test integration targets under "
                "extensions/molecule/ as real Molecule scenarios."
            ),
        )
        parser.add_argument(
            "target_name",
            nargs="?",
            default="",
            help=(
                "Integration target name under tests/integration/targets/. Omit when using --all."
            ),
        )
        parser.add_argument(
            "--path",
            "-p",
            default="./",
            dest="path",
            metavar="path",
            help=(
                "The path to the Ansible collection. The default is the current working directory."
            ),
        )
        parser.add_argument(
            "--all",
            dest="migrate_all",
            default=False,
            action="store_true",
            help="Migrate all role-shaped integration targets.",
        )
        parser.add_argument(
            "--keep-targets",
            dest="keep_targets",
            default=False,
            action="store_true",
            help=(
                "Copy targets into scenarios instead of moving them "
                "(keeps ansible-test paths for hybrid use)."
            ),
        )
        self._add_overwrite(parser)
        self._add_args_common(parser)
