"""A runpy entry point for ansible-creator.

This makes it possible to invoke CLI
via :command:`python3 -m ansible_creator`.
"""

from __future__ import annotations

from .cli import main


if __name__ == "__main__":
    main()
