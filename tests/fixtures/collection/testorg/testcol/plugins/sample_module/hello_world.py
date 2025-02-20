# hello_world.py - A custom module plugin for Ansible.
# Author: Your Name (@username)
# License: GPL-3.0-or-later

from __future__ import absolute_import, annotations, division, print_function


__metaclass__ = type  # pylint: disable=C0103

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from typing import Callable


DOCUMENTATION = """
    name: hello_world
    author: Your Name (@username)
    version_added: "1.0.0"
    short_description: A custom module plugin for Ansible.
    description:
      - This is a demo module plugin designed to return Hello message.
    options:
      name:
        description: Value specified here is appended to the Hello message.
        type: str
"""

EXAMPLES = """
# hello_world module example

- name: Display a hello message
  ansible.builtin.debug:
    msg: "{{ 'ansible-creator' | hello_world }}"
"""


def _hello_world(name: str) -> str:
    """Returns Hello message.

    Args:
        name: The name to greet.

    Returns:
        str: The greeting message.
    """
    return "Hello, " + name


class SampleModule:
    """module plugin."""

    def modules(self) -> dict[str, Callable[[str], str]]:
        """Map module plugin names to their functions.

        Returns:
            dict: The module plugin functions.
        """
        return {"hello_world": _hello_world}
