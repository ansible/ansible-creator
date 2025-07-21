#!/usr/bin/python
# pylint: disable=E0401
# sample_module.py - A custom module plugin for Ansible.
# Author: Your Name (@username)
# License: GPL-3.0-or-later
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function


DOCUMENTATION = """
    module: sample_module
    author: Your Name (@username)
    version_added: "1.0.0"
    short_description: A custom module plugin for Ansible.
    description:
      - This is a demo module plugin designed to return Hello message.
    options:
      name:
        description: Value specified here is appended to the Hello message.
        type: str
        required: true
"""

EXAMPLES = """
- name: Run the module
  register: result
  sample_module:
    name: "ansible-creator"

- name: Display the message
  ansible.builtin.debug:
    msg: result.message
"""

RETURN = """
message:
  description:
  - A demo message.
  type: str
  returned: always
  sample: "Hello, ansible-creator"
"""


__metaclass__ = type  # pylint: disable=C0103

from typing import TYPE_CHECKING

from ansible.module_utils.basic import AnsibleModule  # type: ignore


if TYPE_CHECKING:
    from typing import Callable


def _sample_module(name: str) -> str:
    """Returns Hello message.

    Args:
        name: The name to greet.

    Returns:
        str: The greeting message.
    """
    return "Hello, " + name


def main() -> None:
    """Entry point for module execution"""
    argument_spec = dict(
        name=dict(type="str", required=True),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
    )

    message = _sample_module(module.params["name"])

    result = {
        "changed": False,
        "message": message,
    }
    module.exit_json(**result)


if __name__ == "__main__":
    main()
