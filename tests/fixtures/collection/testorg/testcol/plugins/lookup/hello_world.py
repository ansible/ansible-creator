"""A hello-world lookup plugin in testorg.testcol."""

from __future__ import absolute_import, annotations, division, print_function
from ansible.plugins.lookup import LookupBase

__metaclass__ = type  # pylint: disable=C0103

DOCUMENTATION = """
    name: hello_world
    author: Testorg Testcol
    version_added: "1.0.0"
    short_description: Demo lookup plugin that returns a Hello message.
    description:
      - This is a demo lookup plugin designed to return Hello message.
    options:
      name:
        description: Value specified here is appended to the Hello message.
        type: str
"""

EXAMPLES = """
# hello_world lookup example

- name: Display a hello message
  ansible.builtin.debug:
    msg: "{{ lookup('testorg.testcol.hello_world') }}"
"""

RETURN = """
_raw:
  description: Returns a Hello message with the specified name
  type: list
  elements: string
  sample: ["Hello, World!"]
"""


class LookupModule(LookupBase):
    """lookup plugin."""

    def run(self, terms: list, variables: dict = None, **kwargs) -> list:
        """Returns a simple Hello, World message.

        Parameters:
            terms: A list of terms passed to the function.
            variables: Additional variables for processing.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            list: The Hello message as a list.
        """
        return ["Hello, World!"]
