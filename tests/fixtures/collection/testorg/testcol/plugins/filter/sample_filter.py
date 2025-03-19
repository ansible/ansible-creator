# sample_filter.py - A custom filter plugin for Ansible.
# Author: Your Name
# License: GPL-3.0-or-later

from __future__ import absolute_import, annotations, division, print_function


__metaclass__ = type  # pylint: disable=C0103

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from typing import Callable


DOCUMENTATION = """
    name: sample_filter
    author: Your Name
    version_added: "1.0.0"
    short_description: A custom filter plugin for Ansible.
    description:
      - This is a demo filter plugin designed to return Hello message.
    options:
      name:
        description: Value specified here is appended to the Hello message.
        type: str
"""

EXAMPLES = """
# sample_filter filter example

- name: Display a hello message
  ansible.builtin.debug:
    msg: "{{ 'ansible-creator' | sample_filter }}"
"""


def _sample_filter(name: str) -> str:
    """Returns Hello message.

    Args:
        name: The name to greet.

    Returns:
        str: The greeting message.
    """
    return "Hello, " + name


class FilterModule:
    """filter plugin."""

    def filters(self) -> dict[str, Callable[[str], str]]:
        """Map filter plugin names to their functions.

        Returns:
            dict: The filter plugin functions.
        """
        return {"sample_filter": _sample_filter}
