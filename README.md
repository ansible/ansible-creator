[![codecov](https://codecov.io/github/ansible/ansible-creator/graph/badge.svg?token=QZKqxsNNsL)](https://codecov.io/github/ansible/ansible-creator)
[![PyPI - Status](https://img.shields.io/pypi/status/ansible-creator)](https://pypi.org/project/ansible-creator/)
[![PyPI - Version](https://img.shields.io/pypi/v/ansible-creator)](https://pypi.org/project/ansible-creator/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ansible-creator)
![License](https://img.shields.io/github/license/ansible/ansible-creator)
[![Ansible Code of Conduct](https://img.shields.io/badge/Code%20of%20Conduct-Ansible-silver.svg)](https://docs.ansible.com/ansible/latest/community/code_of_conduct.html)
[![GitHub issues](https://img.shields.io/github/issues/ansible/ansible-creator)](https://github.com/ansible/ansible-creator/issues)

# ansible-creator

A CLI tool for scaffolding all your Ansible Content.

## Installation

```shell
$ pip install ansible-creator
```

```shell
$ ansible-creator --help
usage: ansible-creator [-h] command ...

The fastest way to generate all your ansible content.

Positional arguments:
 command
  add           Add resources to an existing Ansible project.
  init          Initialize a new Ansible project.

Options:
 -h     --help  Show this help message and exit
```

## Usage

Full documentation on how to use this, along with it's integration with VS Code Ansible Extension can be found in https://ansible.readthedocs.io/projects/creator/.

## Command line completion

`ansible-creator` has experimental command line completion for common shells. Please ensure you have the `argcomplete` package installed and configured.

```shell
$ pip install argcomplete --user
$ activate-global-python-argcomplete --user
```

## Upcoming features

- Scaffold Ansible plugins of your choice with the `create` action.
  Switch to the [create](https://github.com/ansible-community/ansible-creator/tree/create) branch and try it out!

## Licensing

ansible-creator is released under the Apache License version 2.

See the [LICENSE](https://github.com/ansible/ansible-creator/blob/main/LICENSE) file for more details.
