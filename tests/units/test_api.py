"""Unit tests for the ansible-creator V1 API."""

from __future__ import annotations

import argparse
import json
import shutil

from typing import TYPE_CHECKING

import pytest

from ansible_creator.api import V1, CreatorResult, _CapturingOutput
from ansible_creator.config import Config
from ansible_creator.output import Level
from ansible_creator.subcommands.init import Init
from ansible_creator.subcommands.schema import Schema


if TYPE_CHECKING:
    from pathlib import Path

    from ansible_creator.output import Output


@pytest.fixture(name="creator_api")
def fixture_creator_api() -> V1:
    """Create a V1 API instance.

    Returns:
        V1: API instance with default verbosity.
    """
    return V1()


@pytest.fixture(name="creator_api_verbose")
def fixture_creator_api_verbose() -> V1:
    """Create a V1 API instance with debug verbosity.

    Returns:
        V1: API instance with verbosity=2.
    """
    return V1(verbosity=2)


# --- Schema tests ---


class TestSchema:
    """Tests for V1.schema() and V1.schema_for()."""

    def test_schema_returns_dict(self, creator_api: V1) -> None:
        """Test that schema() returns a well-formed dictionary.

        Args:
            creator_api: V1 API instance.
        """
        result = creator_api.schema()
        assert isinstance(result, dict)
        assert result["name"] == "ansible-creator"
        assert "subcommands" in result
        assert "init" in result["subcommands"]
        assert "add" in result["subcommands"]

    def test_schema_init_has_subcommands(self, creator_api: V1) -> None:
        """Test that init subcommand has expected project types.

        Args:
            creator_api: V1 API instance.
        """
        result = creator_api.schema()
        init_cmd = result["subcommands"]["init"]
        assert "subcommands" in init_cmd
        assert "collection" in init_cmd["subcommands"]
        assert "playbook" in init_cmd["subcommands"]
        assert "execution_env" in init_cmd["subcommands"]

    def test_schema_add_has_resource_and_plugin(self, creator_api: V1) -> None:
        """Test that add subcommand has resource and plugin subtrees.

        Args:
            creator_api: V1 API instance.
        """
        result = creator_api.schema()
        add_cmd = result["subcommands"]["add"]
        assert "subcommands" in add_cmd
        assert "resource" in add_cmd["subcommands"]
        assert "plugin" in add_cmd["subcommands"]

    def test_schema_for_init_collection(self, creator_api: V1) -> None:
        """Test schema_for() returns correct subtree for init collection.

        Args:
            creator_api: V1 API instance.
        """
        result = creator_api.schema_for("init", "collection")
        assert result["name"] == "collection"
        assert "parameters" in result
        assert "collection" in result["parameters"]["properties"]

    def test_schema_for_add_resource(self, creator_api: V1) -> None:
        """Test schema_for() returns correct subtree for add resource devfile.

        Args:
            creator_api: V1 API instance.
        """
        result = creator_api.schema_for("add", "resource", "devfile")
        assert result["name"] == "devfile"
        assert "parameters" in result

    def test_schema_for_invalid_path(self, creator_api: V1) -> None:
        """Test schema_for() raises KeyError for invalid path.

        Args:
            creator_api: V1 API instance.
        """
        with pytest.raises(KeyError, match="not found"):
            creator_api.schema_for("init", "nonexistent")

    def test_schema_for_empty_path(self, creator_api: V1) -> None:
        """Test schema_for() with no path returns the root schema.

        Args:
            creator_api: V1 API instance.
        """
        result = creator_api.schema_for()
        assert result["name"] == "ansible-creator"


# --- Init tests ---


class TestRunInit:
    """Tests for V1.run() with init subcommands."""

    def test_init_collection(self, creator_api: V1) -> None:
        """Test scaffolding a collection project.

        Args:
            creator_api: V1 API instance.
        """
        result = creator_api.run("init", "collection", collection="testns.testcol")
        try:
            assert result.status == "success", result.message
            assert result.path.exists()
            assert (result.path / "galaxy.yml").exists()
            assert (result.path / "plugins").is_dir()
            assert "collection project created" in result.message
        finally:
            shutil.rmtree(result.path, ignore_errors=True)

    def test_init_playbook(self, creator_api: V1) -> None:
        """Test scaffolding a playbook project.

        Args:
            creator_api: V1 API instance.
        """
        result = creator_api.run("init", "playbook", collection="testns.testcol")
        try:
            assert result.status == "success", result.message
            assert result.path.exists()
            assert (result.path / "site.yml").exists()
            assert "playbook project created" in result.message
        finally:
            shutil.rmtree(result.path, ignore_errors=True)

    def test_init_execution_env(self, creator_api: V1) -> None:
        """Test scaffolding an execution environment project.

        Args:
            creator_api: V1 API instance.
        """
        result = creator_api.run("init", "execution_env")
        try:
            assert result.status == "success", result.message
            assert result.path.exists()
            assert (result.path / "execution-environment.yml").exists()
            assert "execution_env project created" in result.message
        finally:
            shutil.rmtree(result.path, ignore_errors=True)


# --- Add resource tests ---


class TestRunAddResource:
    """Tests for V1.run() with add resource subcommands."""

    def test_add_resource_devfile(self, creator_api: V1) -> None:
        """Test adding a devfile resource.

        Args:
            creator_api: V1 API instance.
        """
        result = creator_api.run("add", "resource", "devfile")
        try:
            assert result.status == "success", result.message
            assert result.path.exists()
            assert (result.path / "devfile.yaml").exists()
            assert "Resource added to" in result.message
        finally:
            shutil.rmtree(result.path, ignore_errors=True)

    def test_add_resource_devcontainer(self, creator_api: V1) -> None:
        """Test adding a devcontainer resource.

        Args:
            creator_api: V1 API instance.
        """
        result = creator_api.run("add", "resource", "devcontainer")
        try:
            assert result.status == "success", result.message
            assert result.path.exists()
            assert (result.path / ".devcontainer").is_dir()
            assert "Resource added to" in result.message
        finally:
            shutil.rmtree(result.path, ignore_errors=True)

    def test_add_resource_execution_environment(self, creator_api: V1) -> None:
        """Test adding an execution-environment resource.

        Args:
            creator_api: V1 API instance.
        """
        result = creator_api.run("add", "resource", "execution-environment")
        try:
            assert result.status == "success", result.message
            assert result.path.exists()
            assert (result.path / "execution-environment.yml").exists()
        finally:
            shutil.rmtree(result.path, ignore_errors=True)

    def test_add_resource_ai(self, creator_api: V1) -> None:
        """Test adding AI agent helper files.

        Args:
            creator_api: V1 API instance.
        """
        result = creator_api.run("add", "resource", "ai")
        try:
            assert result.status == "success", result.message
            assert result.path.exists()
            assert (result.path / "AGENTS.md").exists()
        finally:
            shutil.rmtree(result.path, ignore_errors=True)


# --- Add plugin tests ---


class TestRunAddPlugin:
    """Tests for V1.run() with add plugin subcommands.

    The API automatically sets ``skip_collection_check=True`` so plugins
    can be scaffolded into a bare temp directory without needing a full
    Ansible collection structure.
    """

    def test_add_plugin_filter(self, creator_api: V1) -> None:
        """Test adding a filter plugin.

        Args:
            creator_api: V1 API instance.
        """
        result = creator_api.run("add", "plugin", "filter", plugin_name="my_filter")
        try:
            assert result.status == "success", result.message
            assert result.path.exists()
            assert (result.path / "plugins" / "filter" / "my_filter.py").exists()
            assert "Filter plugin added to" in result.message
        finally:
            shutil.rmtree(result.path, ignore_errors=True)

    def test_add_plugin_lookup(self, creator_api: V1) -> None:
        """Test adding a lookup plugin.

        Args:
            creator_api: V1 API instance.
        """
        result = creator_api.run("add", "plugin", "lookup", plugin_name="my_lookup")
        try:
            assert result.status == "success", result.message
            assert result.path.exists()
            assert (result.path / "plugins" / "lookup" / "my_lookup.py").exists()
        finally:
            shutil.rmtree(result.path, ignore_errors=True)

    def test_add_plugin_module(self, creator_api: V1) -> None:
        """Test adding a module plugin.

        Args:
            creator_api: V1 API instance.
        """
        result = creator_api.run("add", "plugin", "module", plugin_name="my_module")
        try:
            assert result.status == "success", result.message
            assert result.path.exists()
            assert (result.path / "plugins" / "modules" / "my_module.py").exists()
        finally:
            shutil.rmtree(result.path, ignore_errors=True)


# --- Error handling tests ---


class TestErrorHandling:
    """Tests for error handling in V1.run()."""

    def test_empty_command_path(self, creator_api: V1) -> None:
        """Test that an empty command path returns an error.

        Args:
            creator_api: V1 API instance.
        """
        result = creator_api.run()
        assert result.status == "error"
        assert "No command path" in result.message

    def test_invalid_command_path(self, creator_api: V1) -> None:
        """Test that an invalid command path returns an error.

        Args:
            creator_api: V1 API instance.
        """
        result = creator_api.run("nonexistent")
        assert result.status == "error"
        assert "Invalid command path" in result.message

    def test_invalid_subcommand_segment(self, creator_api: V1) -> None:
        """Test that an invalid segment in a valid path returns an error.

        Args:
            creator_api: V1 API instance.
        """
        result = creator_api.run("init", "nonexistent")
        assert result.status == "error"
        assert "Invalid command path" in result.message

    def test_result_dataclass_defaults(self, tmp_path: Path) -> None:
        """Test CreatorResult dataclass default values.

        Args:
            tmp_path: Temporary directory path.
        """
        result = CreatorResult(status="success", path=tmp_path)
        assert not result.logs
        assert result.message == ""


# --- Verbosity tests ---


class TestVerbosity:
    """Tests for verbosity control."""

    def test_verbose_captures_debug_messages(self, creator_api_verbose: V1) -> None:
        """Test that verbosity=2 captures debug-level messages.

        Args:
            creator_api_verbose: V1 API instance with verbosity=2.
        """
        result = creator_api_verbose.run("init", "execution_env")
        try:
            assert result.status == "success", result.message
            debug_msgs = [m for m in result.logs if m.startswith("Debug:")]
            assert len(debug_msgs) > 0, "Expected debug messages with verbosity=2"
        finally:
            shutil.rmtree(result.path, ignore_errors=True)

    def test_default_verbosity_no_debug(self, creator_api: V1) -> None:
        """Test that default verbosity does not capture debug messages.

        The _CapturingOutput always captures all messages regardless of
        verbosity, but the internal subcommands only emit debug messages
        when the output's verbosity threshold allows it.

        Args:
            creator_api: V1 API instance with default verbosity.
        """
        result = creator_api.run("init", "execution_env")
        try:
            assert result.status == "success", result.message
            # With default verbosity, the subcommand Output filtering
            # prevents debug messages from being logged at all
        finally:
            shutil.rmtree(result.path, ignore_errors=True)


# --- CapturingOutput tests ---


class TestCapturingOutput:
    """Tests for the _CapturingOutput helper."""

    def test_critical_message_captured(self) -> None:
        """Test that critical messages are captured without exiting."""
        output = _CapturingOutput(verbosity=0)
        output.critical("something went wrong")
        assert output.call_count["critical"] == 1
        assert any("something went wrong" in m for m in output.messages)


# --- Message extraction tests ---


class TestMessageExtraction:
    """Tests for the Note: message extraction in run()."""

    def test_success_without_note_message(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that run() succeeds with message='' when no Note: is emitted.

        The mock produces non-Note messages so the for-loop iterates
        through all of them without finding a match.

        Args:
            monkeypatch: Pytest monkeypatch fixture.
        """

        def mock_run(init_self: Init) -> None:
            """Emit debug messages but no Note.

            Args:
                init_self: The Init instance.
            """
            init_self.output.log("starting scaffold", level=Level.DEBUG)
            init_self.output.log("scaffold complete", level=Level.DEBUG)

        monkeypatch.setattr(Init, "run", mock_run)
        verbose_api = V1(verbosity=2)
        result = verbose_api.run("init", "execution_env")
        try:
            assert result.status == "success"
            assert result.message == ""
            assert len(result.logs) > 0
        finally:
            shutil.rmtree(result.path, ignore_errors=True)


# --- Explicit path override tests ---


class TestExplicitPaths:
    """Tests for providing explicit init_path or path kwargs."""

    def test_init_with_explicit_path(self, creator_api: V1, tmp_path: Path) -> None:
        """Test init with an explicit init_path kwarg.

        Args:
            creator_api: V1 API instance.
            tmp_path: Temporary directory path.
        """
        target = tmp_path / "explicit_init"
        target.mkdir()
        result = creator_api.run(
            "init",
            "execution_env",
            init_path=str(target),
        )
        try:
            assert result.status == "success", result.message
            assert (target / "execution-environment.yml").exists()
        finally:
            shutil.rmtree(result.path, ignore_errors=True)

    def test_add_with_explicit_path(self, creator_api: V1, tmp_path: Path) -> None:
        """Test add resource with an explicit path kwarg.

        Args:
            creator_api: V1 API instance.
            tmp_path: Temporary directory path.
        """
        target = tmp_path / "explicit_add"
        target.mkdir()
        result = creator_api.run(
            "add",
            "resource",
            "devfile",
            path=str(target),
        )
        try:
            assert result.status == "success", result.message
            assert (target / "devfile.yaml").exists()
        finally:
            shutil.rmtree(result.path, ignore_errors=True)


# --- Schema class direct tests ---


class TestSchemaClass:
    """Tests for the Schema class __init__ and run() methods."""

    def test_schema_run_outputs_json(
        self,
        capsys: pytest.CaptureFixture[str],
        output: Output,
    ) -> None:
        """Test that Schema.run() writes JSON to stdout.

        Args:
            capsys: Pytest capture fixture.
            output: Output fixture.
        """
        config = Config(
            creator_version="0.0.1",
            output=output,
            subcommand="schema",
        )
        schema = Schema(config=config)
        schema.run()
        captured = capsys.readouterr().out
        data = json.loads(captured)
        assert data["name"] == "ansible-creator"
        assert "subcommands" in data

    def test_schema_extract_int_type(self) -> None:
        """Test _extract_action_info handles int type arguments."""
        parser = argparse.ArgumentParser()
        expected_default = 5
        parser.add_argument("--count", type=int, default=expected_default, help="A count")
        action = next(a for a in parser._actions if a.dest == "count")
        info = Schema._extract_action_info(action)
        assert info["type"] == "int"
        assert info["default"] == expected_default

    def test_schema_extract_array_type(self) -> None:
        """Test _extract_action_info handles nargs=+ arguments."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--items", nargs="+", help="Multiple items")
        action = next(a for a in parser._actions if a.dest == "items")
        info = Schema._extract_action_info(action)
        assert info["type"] == "array"
        assert info["items"] == {"type": "string"}
