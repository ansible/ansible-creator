"""Unit tests for ansible-creator init."""

from __future__ import annotations

import re
import sys
from textwrap import dedent


def test_run_init_no_input(cli):
    result = cli("ansible-creator init")
    assert result.returncode != 0
    assert (
        "Error: The argument 'collection' is required when scaffolding a collection"
        in result.stderr
    )


def test_run_init_basic(cli, tmp_path):
    final_dest = f"{tmp_path}/collections/ansible_collections"
    cli(f"mkdir -p {final_dest}")

    result = cli(
        f"ansible-creator init testorg.testcol --init-path {final_dest}",
    )
    assert result.returncode == 0

    # check stdout
    assert (
        re.search("Note: collection testorg.testcol created at", result.stdout)
        is not None
    )

    # fail to override existing collection with force=false (default)
    result = cli(
        f"ansible-creator init testorg.testcol --init-path {final_dest}",
    )

    assert result.returncode != 0

    # this is required to handle random line breaks in CI, especially with macos runners
    mod_stderr = "".join([line.strip() for line in result.stderr.splitlines()])
    assert (
        re.search(
            rf"Error:\s*The\s*directory\s*{final_dest}/testorg/testcol\s*is\s*not\s*empty.",
            mod_stderr,
        )
        is not None
    )
    assert "You can use --force to re-initialize this directory." in result.stderr
    assert "However it will delete ALL existing contents in it." in result.stderr

    # override existing collection with force=true
    result = cli(f"ansible-creator init testorg.testcol --init-path {tmp_path} --force")
    assert result.returncode == 0
    assert (
        re.search("Warning: re-initializing existing directory", result.stdout)
        is not None
    )
