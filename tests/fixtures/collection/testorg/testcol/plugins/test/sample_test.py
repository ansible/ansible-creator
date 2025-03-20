# sample_test.py - A custom test plugin for Ansible.
# Author: Your Name
# License: GPL-3.0-or-later

from __future__ import absolute_import, annotations, division, print_function


__metaclass__ = type  # pylint: disable=C0103

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from typing import Callable


DOCUMENTATION = """
    name: sample_test
    author: Your Name
    version_added: "1.0.0"
    short_description: A custom test plugin for Ansible.
    description:
      - This is a demo test plugin designed to return Hello message.
    options:
      name:
        description: Value specified here is appended to the Hello message.
        type: str
"""

EXAMPLES = """
# sample_test test example

- name: Display a hello message
  ansible.builtin.debug:
    msg: "{{ 50 | sample_test }}"
"""


def _hello_world(val: int) -> bool:
    """Returns Hello message.

    Args:
        val: The value to test.

    Returns:
        bool: The result.
    """
    return val > 42


class TestModule:
    """test plugin."""

    def tests(self) -> dict[str, Callable[[int], bool]]:
        """Map test plugin names to their functions.

        Returns:
            dict: The test plugin functions.
        """
        return {"sample_test": _hello_world}
