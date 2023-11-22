"""Utility methods for unit tests."""
import contextlib
import filecmp
import io


def run_diff(a, b):  # noqa: ANN201, ANN001
    """Recursively compare a and b."""
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        filecmp.dircmp(a, b).report_full_closure()
    return stdout.getvalue()
