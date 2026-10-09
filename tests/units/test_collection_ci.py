"""Tests for the CI workflow scaffolded into a collection project.

The tests read the golden fixture, which test_init compares to the rendered template.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.defaults import FIXTURES_DIR


CI_WORKFLOW = (
    FIXTURES_DIR / "collection" / "testorg" / "testcol" / ".github" / "workflows" / "tests.yml"
)
NEEDS_RESULT = re.compile(r"\$\{\{ needs\.([\w-]+)\.result \}\}")
WORKFLOW: dict[str, Any] = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
ALL_GREEN: dict[str, Any] = WORKFLOW["jobs"]["all_green"]
ALL_GREEN_RUN: str = ALL_GREEN["steps"][0]["run"]


def run_all_green(results: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run the all_green step's command in a shell with the test interpreter as python.

    Args:
        results: Result to set for each named job.
            Every other job the step checks is set to success.

    Returns:
        The completed process of the all_green step.
    """
    command = NEEDS_RESULT.sub(
        lambda match: results.get(match.group(1), "success"),
        ALL_GREEN_RUN,
    )
    env = {key: value for key, value in os.environ.items() if key != "PYTHONOPTIMIZE"}
    env["PATH"] = os.pathsep.join((str(Path(sys.executable).parent), env.get("PATH", "")))
    return subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_all_green_checks_every_needed_job() -> None:
    """Test the all_green step needs every other job and checks each result."""
    checked = NEEDS_RESULT.findall(ALL_GREEN_RUN)
    assert sorted(checked) == sorted(ALL_GREEN["needs"])
    assert set(ALL_GREEN["needs"]) == set(WORKFLOW["jobs"]) - {"all_green"}


def test_all_green_passes_when_all_jobs_succeed() -> None:
    """Test the all_green step passes when every needed job succeeds."""
    result = run_all_green(results={})
    assert result.returncode == 0, result.stderr


def test_all_green_passes_when_changelog_is_skipped() -> None:
    """Test the all_green step passes when changelog is skipped outside a pull request."""
    assert WORKFLOW["jobs"]["changelog"]["if"] == "github.event_name == 'pull_request'"
    result = run_all_green(results={"changelog": "skipped"})
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("failed_job", tuple(ALL_GREEN["needs"]))
def test_all_green_fails_when_a_job_fails(failed_job: str) -> None:
    """Test the all_green step fails when any needed job fails.

    Args:
        failed_job: Name of the job whose result is set to failure.
    """
    result = run_all_green(results={failed_job: "failure"})
    assert result.returncode != 0, f"all_green passed with {failed_job} failed"
    assert "AssertionError" in result.stderr, result.stderr


@pytest.mark.parametrize("cancelled_job", tuple(ALL_GREEN["needs"]))
def test_all_green_fails_when_a_job_is_cancelled(cancelled_job: str) -> None:
    """Test the all_green step fails when any needed job is cancelled.

    Args:
        cancelled_job: Name of the job whose result is set to cancelled.
    """
    result = run_all_green(results={cancelled_job: "cancelled"})
    assert result.returncode != 0, f"all_green passed with {cancelled_job} cancelled"
    assert "AssertionError" in result.stderr, result.stderr
