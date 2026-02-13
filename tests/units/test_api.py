"""Unit tests for the ansible-creator V1 API."""

from __future__ import annotations

import argparse
import json
import shutil

from typing import TYPE_CHECKING

import pytest

from ansible_creator.api import V1, CreatorResult
from ansible_creator.config import Config
from ansible_creator.exceptions import CreatorError
from ansible_creator.output import Level, Output
from ansible_creator.schema import _extract_action_info
from ansible_creator.subcommands.init import Init
from ansible_creator.subcommands.schema import Schema
from ansible_creator.utils import TermFeatures


if TYPE_CHECKING:
    from pathlib import Path


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


# --- build_command tests ---


def test_build_command_init_collection(creator_api: V1) -> None:
    """Test argv for init collection.

    Args:
        creator_api: V1 API instance.
    """
    argv = creator_api.build_command(
        "init",
        "collection",
        collection="testns.testcol",
    )
    assert argv[:3] == ["init", "collection", "testns.testcol"]


def test_build_command_add_plugin_with_flags(creator_api: V1) -> None:
    """Test argv for add plugin with overwrite flag.

    Args:
        creator_api: V1 API instance.
    """
    argv = creator_api.build_command(
        "add",
        "plugin",
        "filter",
        plugin_name="my_filter",
        overwrite=True,
    )
    assert "add" in argv
    assert "plugin" in argv
    assert "filter" in argv
    assert "my_filter" in argv
    # The overwrite flag may use short form (-o) or long form (--overwrite)
    assert "-o" in argv or "--overwrite" in argv


def test_build_command_add_resource_simple(creator_api: V1) -> None:
    """Test argv for add resource devfile.

    Args:
        creator_api: V1 API instance.
    """
    argv = creator_api.build_command("add", "resource", "devfile")
    assert argv[:4] == ["add", "resource", "devfile"]


def test_build_command_init_execution_env(creator_api: V1, tmp_path: Path) -> None:
    """Test argv for init execution_env with explicit path.

    Args:
        creator_api: V1 API instance.
        tmp_path: Temporary directory path.
    """
    target = tmp_path / "ee"
    argv = creator_api.build_command(
        "init",
        "execution_env",
        init_path=str(target),
    )
    assert "init" in argv
    assert "execution_env" in argv
    assert str(target) in argv


def test_build_command_optional_string_arg(creator_api: V1, tmp_path: Path) -> None:
    """Test argv includes optional string arguments with flag prefix.

    Args:
        creator_api: V1 API instance.
        tmp_path: Temporary directory path.
    """
    log = tmp_path / "my.log"
    argv = creator_api.build_command(
        "init",
        "execution_env",
        log_file=str(log),
    )
    assert str(log) in argv


def test_build_command_store_true_false_value(creator_api: V1) -> None:
    """Test that store_true flags with False value are omitted from argv.

    Args:
        creator_api: V1 API instance.
    """
    argv = creator_api.build_command(
        "add",
        "plugin",
        "filter",
        plugin_name="my_filter",
        overwrite=False,
    )
    assert "-o" not in argv
    assert "--overwrite" not in argv


def test_build_command_routing_key_override_rejected(creator_api: V1) -> None:
    """Test that build_command rejects routing key overrides.

    Args:
        creator_api: V1 API instance.
    """
    with pytest.raises(TypeError, match="Cannot override routing keys"):
        creator_api.build_command("init", "collection", project="playbook")


def test_build_command_count_action_repeats_flag(creator_api: V1) -> None:
    """Test that count-action options repeat the flag N times.

    The ``-v`` / ``--verbosity`` argument uses ``action="count"``, so
    ``verbose=2`` should produce ``["-v", "-v"]`` rather than
    ``["-v", "2"]``.

    Args:
        creator_api: V1 API instance.
    """
    verbosity = 3
    argv = creator_api.build_command(
        "init",
        "collection",
        collection="ns.col",
        verbose=verbosity,
    )
    assert argv.count("-v") == verbosity
    # Should not include the numeric value as a separate token
    assert "3" not in argv


def test_build_command_unknown_kwarg_rejected(creator_api: V1) -> None:
    """Test that unknown kwargs raise TypeError.

    Args:
        creator_api: V1 API instance.
    """
    with pytest.raises(TypeError, match="Unknown parameters"):
        creator_api.build_command(
            "init",
            "collection",
            collection="ns.col",
            nonexistent_option="value",
        )


def test_run_unknown_kwarg_returns_error(creator_api: V1) -> None:
    """Test that run() surfaces unknown kwargs as an error result.

    Args:
        creator_api: V1 API instance.
    """
    result = creator_api.run(
        "init",
        "collection",
        collection="ns.col",
        totally_bogus="oops",
    )
    assert result.status == "error"
    assert "Unknown parameters" in result.message


# --- Schema tests ---


def test_schema_returns_dict(creator_api: V1) -> None:
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
    assert "schema" in result["subcommands"]


def test_schema_init_has_subcommands(creator_api: V1) -> None:
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


def test_schema_add_has_resource_and_plugin(creator_api: V1) -> None:
    """Test that add subcommand has resource and plugin subtrees.

    Args:
        creator_api: V1 API instance.
    """
    result = creator_api.schema()
    add_cmd = result["subcommands"]["add"]
    assert "subcommands" in add_cmd
    assert "resource" in add_cmd["subcommands"]
    assert "plugin" in add_cmd["subcommands"]


def test_schema_for_init_collection(creator_api: V1) -> None:
    """Test schema_for() returns correct subtree for init collection.

    Args:
        creator_api: V1 API instance.
    """
    result = creator_api.schema_for("init", "collection")
    assert result["name"] == "collection"
    assert "parameters" in result
    assert "collection" in result["parameters"]["properties"]


def test_schema_for_add_resource(creator_api: V1) -> None:
    """Test schema_for() returns correct subtree for add resource devfile.

    Args:
        creator_api: V1 API instance.
    """
    result = creator_api.schema_for("add", "resource", "devfile")
    assert result["name"] == "devfile"
    assert "parameters" in result


def test_schema_for_invalid_path(creator_api: V1) -> None:
    """Test schema_for() raises KeyError for invalid path.

    Args:
        creator_api: V1 API instance.
    """
    with pytest.raises(KeyError, match="not found"):
        creator_api.schema_for("init", "nonexistent")


def test_schema_for_empty_path(creator_api: V1) -> None:
    """Test schema_for() with no path returns the root schema.

    Args:
        creator_api: V1 API instance.
    """
    result = creator_api.schema_for()
    assert result["name"] == "ansible-creator"


# --- Init tests ---


def test_init_collection(creator_api: V1, tmp_path: Path) -> None:
    """Test scaffolding a collection project.

    Args:
        creator_api: V1 API instance.
        tmp_path: Temporary directory path.
    """
    target = tmp_path / "collection"
    target.mkdir()
    result = creator_api.run(
        "init",
        "collection",
        collection="testns.testcol",
        init_path=str(target),
    )
    assert result.status == "success", result.message
    assert result.path == target
    assert (target / "galaxy.yml").exists()
    assert (target / "plugins").is_dir()
    assert "collection project created" in result.message


def test_init_playbook(creator_api: V1, tmp_path: Path) -> None:
    """Test scaffolding a playbook project.

    Args:
        creator_api: V1 API instance.
        tmp_path: Temporary directory path.
    """
    target = tmp_path / "playbook"
    target.mkdir()
    result = creator_api.run(
        "init",
        "playbook",
        collection="testns.testcol",
        init_path=str(target),
    )
    assert result.status == "success", result.message
    assert result.path == target
    assert (target / "site.yml").exists()
    assert "playbook project created" in result.message


def test_init_execution_env(creator_api: V1, tmp_path: Path) -> None:
    """Test scaffolding an execution environment project.

    Args:
        creator_api: V1 API instance.
        tmp_path: Temporary directory path.
    """
    target = tmp_path / "ee"
    target.mkdir()
    result = creator_api.run("init", "execution_env", init_path=str(target))
    assert result.status == "success", result.message
    assert result.path == target
    assert (target / "execution-environment.yml").exists()
    assert "execution_env project created" in result.message


# --- Add resource tests ---


def test_add_resource_devfile(creator_api: V1, tmp_path: Path) -> None:
    """Test adding a devfile resource.

    Args:
        creator_api: V1 API instance.
        tmp_path: Temporary directory path.
    """
    target = tmp_path / "devfile"
    target.mkdir()
    result = creator_api.run("add", "resource", "devfile", path=str(target))
    assert result.status == "success", result.message
    assert result.path == target
    assert (target / "devfile.yaml").exists()
    assert "Resource added to" in result.message


def test_add_resource_devcontainer(creator_api: V1, tmp_path: Path) -> None:
    """Test adding a devcontainer resource.

    Args:
        creator_api: V1 API instance.
        tmp_path: Temporary directory path.
    """
    target = tmp_path / "devcontainer"
    target.mkdir()
    result = creator_api.run("add", "resource", "devcontainer", path=str(target))
    assert result.status == "success", result.message
    assert result.path == target
    assert (target / ".devcontainer").is_dir()
    assert "Resource added to" in result.message


def test_add_resource_execution_environment(creator_api: V1, tmp_path: Path) -> None:
    """Test adding an execution-environment resource.

    Args:
        creator_api: V1 API instance.
        tmp_path: Temporary directory path.
    """
    target = tmp_path / "ee"
    target.mkdir()
    result = creator_api.run(
        "add",
        "resource",
        "execution-environment",
        path=str(target),
    )
    assert result.status == "success", result.message
    assert result.path == target
    assert (target / "execution-environment.yml").exists()


def test_add_resource_ai(creator_api: V1, tmp_path: Path) -> None:
    """Test adding AI agent helper files.

    Args:
        creator_api: V1 API instance.
        tmp_path: Temporary directory path.
    """
    target = tmp_path / "ai"
    target.mkdir()
    result = creator_api.run("add", "resource", "ai", path=str(target))
    assert result.status == "success", result.message
    assert result.path == target
    assert (target / "AGENTS.md").exists()


# --- Add plugin tests ---


def test_add_plugin_filter(creator_api: V1, tmp_path: Path) -> None:
    """Test adding a filter plugin.

    The API automatically sets ``skip_collection_check=True`` so plugins
    can be scaffolded into a bare temp directory without needing a full
    Ansible collection structure.

    Args:
        creator_api: V1 API instance.
        tmp_path: Temporary directory path.
    """
    target = tmp_path / "filter"
    target.mkdir()
    result = creator_api.run(
        "add",
        "plugin",
        "filter",
        plugin_name="my_filter",
        path=str(target),
    )
    assert result.status == "success", result.message
    assert result.path == target
    assert (target / "plugins" / "filter" / "my_filter.py").exists()
    assert "Filter plugin added to" in result.message


def test_add_plugin_lookup(creator_api: V1, tmp_path: Path) -> None:
    """Test adding a lookup plugin.

    Args:
        creator_api: V1 API instance.
        tmp_path: Temporary directory path.
    """
    target = tmp_path / "lookup"
    target.mkdir()
    result = creator_api.run(
        "add",
        "plugin",
        "lookup",
        plugin_name="my_lookup",
        path=str(target),
    )
    assert result.status == "success", result.message
    assert result.path == target
    assert (target / "plugins" / "lookup" / "my_lookup.py").exists()


def test_add_plugin_module(creator_api: V1, tmp_path: Path) -> None:
    """Test adding a module plugin.

    Args:
        creator_api: V1 API instance.
        tmp_path: Temporary directory path.
    """
    target = tmp_path / "module"
    target.mkdir()
    result = creator_api.run(
        "add",
        "plugin",
        "module",
        plugin_name="my_module",
        path=str(target),
    )
    assert result.status == "success", result.message
    assert result.path == target
    assert (target / "plugins" / "modules" / "my_module.py").exists()


# --- Error handling tests ---


def test_empty_command_path(creator_api: V1) -> None:
    """Test that an empty command path returns an error with no temp dir.

    Args:
        creator_api: V1 API instance.
    """
    result = creator_api.run()
    assert result.status == "error"
    assert "No command path" in result.message
    assert result.path is None


def test_invalid_command_path(creator_api: V1) -> None:
    """Test that an invalid command path returns an error with no temp dir.

    Args:
        creator_api: V1 API instance.
    """
    result = creator_api.run("nonexistent")
    assert result.status == "error"
    assert "Invalid arguments" in result.message
    assert result.path is None


def test_invalid_subcommand_segment(creator_api: V1) -> None:
    """Test that an invalid segment in a valid path returns an error.

    Args:
        creator_api: V1 API instance.
    """
    result = creator_api.run("init", "nonexistent")
    assert result.status == "error"
    assert result.path is None


def test_routing_key_override_rejected(creator_api: V1) -> None:
    """Test that kwargs conflicting with routing keys are rejected.

    Routing keys (subcommand, project, etc.) are derived from the
    command path and must not be overridden by caller kwargs.

    Args:
        creator_api: V1 API instance.
    """
    result = creator_api.run("init", "collection", project="playbook")
    assert result.status == "error"
    assert "Cannot override routing keys" in result.message
    assert result.path is None


def test_runtime_error_returns_temp_dir(
    creator_api: V1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that a runtime error during execution returns an error result.

    When command resolution succeeds but the subcommand raises
    ``CreatorError``, the result should contain the output directory
    and the error message.  This test intentionally lets V1.run() create
    its own temp dir so we verify the internal-temp-dir-on-error path.

    Args:
        creator_api: V1 API instance.
        monkeypatch: Pytest monkeypatch fixture.
    """

    def _boom(_self: Init) -> None:
        msg = "boom"
        raise CreatorError(msg)

    monkeypatch.setattr(Init, "run", _boom)
    result = creator_api.run("init", "execution_env")
    try:
        assert result.status == "error"
        assert result.message == "boom"
        assert result.path is not None
        assert result.path.exists()
    finally:
        if result.path is not None:
            shutil.rmtree(result.path, ignore_errors=True)


def test_result_dataclass_defaults(tmp_path: Path) -> None:
    """Test CreatorResult dataclass default values.

    Args:
        tmp_path: Temporary directory path.
    """
    result = CreatorResult(status="success", path=tmp_path)
    assert not result.logs
    assert result.message == ""


# --- Verbosity tests ---


def test_verbose_captures_debug_messages(
    creator_api_verbose: V1,
    tmp_path: Path,
) -> None:
    """Test that verbosity=2 captures debug-level messages.

    Args:
        creator_api_verbose: V1 API instance with verbosity=2.
        tmp_path: Temporary directory path.
    """
    target = tmp_path / "ee"
    target.mkdir()
    result = creator_api_verbose.run("init", "execution_env", init_path=str(target))
    assert result.status == "success", result.message
    assert result.path == target
    debug_msgs = [m for m in result.logs if m.startswith("Debug:")]
    assert len(debug_msgs) > 0, "Expected debug messages with verbosity=2"


def test_default_verbosity_no_debug(creator_api: V1, tmp_path: Path) -> None:
    """Test that default verbosity does not capture debug messages.

    Args:
        creator_api: V1 API instance with default verbosity.
        tmp_path: Temporary directory path.
    """
    target = tmp_path / "ee"
    target.mkdir()
    result = creator_api.run("init", "execution_env", init_path=str(target))
    assert result.status == "success", result.message
    assert result.path == target
    debug_msgs = [m for m in result.logs if m.startswith("Debug:")]
    assert not debug_msgs, f"Unexpected debug messages: {debug_msgs}"


# --- Output capture mode tests ---


def test_capture_mode_collects_messages() -> None:
    """Test that captured_messages collects log output."""
    messages: list[str] = []
    output = Output(
        log_file="",
        log_level="notset",
        log_append="true",
        term_features=TermFeatures(color=False, links=False),
        verbosity=2,
        captured_messages=messages,
    )
    output.note("a note")
    output.debug("a debug")
    expected_messages = 2
    assert len(messages) == expected_messages
    assert any("a note" in m for m in messages)
    assert any("a debug" in m for m in messages)


def test_capture_mode_critical_raises() -> None:
    """Test that critical() raises CreatorError in capture mode."""
    messages: list[str] = []
    output = Output(
        log_file="",
        log_level="notset",
        log_append="true",
        term_features=TermFeatures(color=False, links=False),
        verbosity=0,
        captured_messages=messages,
    )
    with pytest.raises(CreatorError, match="something went wrong"):
        output.critical("something went wrong")
    assert output.call_count["critical"] == 1
    assert any("something went wrong" in m for m in messages)


def test_capture_mode_respects_verbosity() -> None:
    """Test that captured_messages respects verbosity thresholds."""
    messages: list[str] = []
    output = Output(
        log_file="",
        log_level="notset",
        log_append="true",
        term_features=TermFeatures(color=False, links=False),
        verbosity=0,
        captured_messages=messages,
    )
    output.debug("should be filtered")
    output.note("should be captured")
    assert len(messages) == 1
    assert "should be captured" in messages[0]


def test_capture_mode_with_file_logging(tmp_path: Path) -> None:
    """Test that file logging works alongside capture mode.

    Args:
        tmp_path: Temporary directory path.
    """
    log_file = tmp_path / "test.log"
    messages: list[str] = []
    output = Output(
        log_file=str(log_file),
        log_level="debug",
        log_append="true",
        term_features=TermFeatures(color=False, links=False),
        verbosity=2,
        captured_messages=messages,
    )
    output.note("captured and logged")
    assert len(messages) == 1
    assert log_file.exists()
    log_content = log_file.read_text()
    assert "captured and logged" in log_content


def test_normal_mode_no_capture() -> None:
    """Test that without captured_messages, Output works normally."""
    output = Output(
        log_file="",
        log_level="notset",
        log_append="true",
        term_features=TermFeatures(color=False, links=False),
        verbosity=0,
    )
    # _captured_messages should be None
    assert output._captured_messages is None


# --- Message extraction tests ---


def test_success_without_note_message(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that run() succeeds with message='' when no Note: is emitted.

    The mock produces non-Note messages so the for-loop iterates
    through all of them without finding a match.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Temporary directory path.
    """

    def mock_run(init_self: Init) -> None:
        """Emit debug messages but no Note.

        Args:
            init_self: The Init instance.
        """
        init_self.output.log("starting scaffold", level=Level.DEBUG)
        init_self.output.log("scaffold complete", level=Level.DEBUG)

    monkeypatch.setattr(Init, "run", mock_run)
    target = tmp_path / "ee"
    target.mkdir()
    verbose_api = V1(verbosity=2)
    result = verbose_api.run("init", "execution_env", init_path=str(target))
    assert result.status == "success"
    assert result.path == target
    assert result.message == ""
    assert len(result.logs) > 0


# --- Explicit path override tests ---


def test_init_with_explicit_path(creator_api: V1, tmp_path: Path) -> None:
    """Test init with an explicit init_path kwarg.

    When an explicit path is provided, result.path should point to
    that directory (no unused temp dir).

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
    assert result.status == "success", result.message
    assert result.path == target
    assert (target / "execution-environment.yml").exists()


def test_add_with_explicit_path(creator_api: V1, tmp_path: Path) -> None:
    """Test add resource with an explicit path kwarg.

    When an explicit path is provided, result.path should point to
    that directory (no unused temp dir).

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
    assert result.status == "success", result.message
    assert result.path == target
    assert (target / "devfile.yaml").exists()


def test_run_schema_subcommand(creator_api: V1) -> None:
    """Test running the schema subcommand via V1.run().

    The schema subcommand is neither ``init`` nor ``add``, so this
    exercises the branch where no output directory is configured.

    Args:
        creator_api: V1 API instance.
    """
    result = creator_api.run("schema")
    assert result.status == "success"
    assert result.path is None  # schema doesn't produce output files


# --- Schema class direct tests ---


def test_schema_run_outputs_json(
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
    assert "schema" in data["subcommands"]


def test_schema_extract_int_type() -> None:
    """Test _extract_action_info handles int type arguments."""
    parser = argparse.ArgumentParser()
    expected_default = 5
    parser.add_argument("--count", type=int, default=expected_default, help="A count")
    action = next(a for a in parser._actions if a.dest == "count")
    info = _extract_action_info(action)
    assert info["type"] == "int"
    assert info["default"] == expected_default


def test_schema_extract_array_type() -> None:
    """Test _extract_action_info handles nargs=+ arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--items", nargs="+", help="Multiple items")
    action = next(a for a in parser._actions if a.dest == "items")
    info = _extract_action_info(action)
    assert info["type"] == "array"
    assert info["items"] == {"type": "string"}
