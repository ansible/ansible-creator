# sample_module.py - A custom module plugin for Ansible.
# Author: Your Name (@username)
# License: GPL-3.0-or-later

from __future__ import absolute_import, annotations, division, print_function


__metaclass__ = type  # pylint: disable=C0103

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from typing import Callable


DOCUMENTATION = """
    name: sample_module
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
# sample_module module example

- name: Display a hello message
  ansible.builtin.debug:
    msg: "{{ 'ansible-creator' | sample_module }}"
"""


def _sample_module(name: str) -> str:
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
        return {"sample_module": _sample_module}
