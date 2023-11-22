"""A hello-world filter plugin in testorg.testcol."""


def _hello_world(name):
    """Returns Hello message."""
    return "Hello, " + name


class FilterModule:
    """filter plugin."""

    def filters(self):
        """Filter plugin."""
        return {"hello_world": _hello_world}
