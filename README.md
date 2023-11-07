![PyPI - Status](https://img.shields.io/pypi/status/ansible-creator)
![PyPI - Version](https://img.shields.io/pypi/v/ansible-creator)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ansible-creator)
![License](https://img.shields.io/github/license/ansible-community/ansible-creator)
[![Ansible Code of Conduct](https://img.shields.io/badge/Code%20of%20Conduct-Ansible-silver.svg)](https://docs.ansible.com/ansible/latest/community/code_of_conduct.html)
[![GitHub issues](https://img.shields.io/github/issues/ansible-community/ansible-creator)](https://github.com/ansible-community/ansible-creator/issues)

# ansible-creator

A CLI tool for scaffolding all your Ansible Content.

## Installation

```
$ pip install ansible-creator
```

## Usage

```
$ ansible-creator --help
usage: ansible-creator [-h] [--version] {init} ...

Tool to scaffold Ansible Content. Get started by looking at the help text.

optional arguments:
  -h, --help  show this help message and exit
  --version   Print ansible-creator version and exit.

Commands:
  {init}      The subcommand to invoke.
    init      Initialize an Ansible Collection.
```

### Initialize an Ansible Collection skeleton with 'init'

```
$ ansible-creator init --help
usage: ansible-creator init [-h] [--na] [--lf LOG_FILE] [--ll {notset,debug,info,warning,error,critical}] [--la {true,false}] [--json] [-v]
                            [--init-path INIT_PATH] [--force]
                            collection

Creates the skeleton framework of an Ansible collection.

positional arguments:
  collection            The collection name in the format ``<namespace>.<collection>``.

optional arguments:
  -h, --help            show this help message and exit
  --na, --no-ansi       Disable the use of ANSI codes for terminal color.
  --lf LOG_FILE, --log-file <file> LOG_FILE
                        Log file to write to.
  --ll {notset,debug,info,warning,error,critical}, --log-level <level> {notset,debug,info,warning,error,critical}
                        Log level for file output.
  --la {true,false}, --log-append <bool> {true,false}
                        Append to log file.
  --json                Output messages as JSON
  -v, --verbose         Give more Cli output. Option is additive, and can be used up to 3 times.
  --init-path INIT_PATH
                        The path in which the skeleton collection will be created. The default is the current working directory.
  --force               Force re-initialize the specified directory as an Ansible collection.
```

```
$ ansible-creator init testns.testname --init-path $HOME/collections/ansible_collections
    Note: collection testns.testname created at /home/ansible-dev/collections/ansible_collections
```

Running the above command generates an Ansible Collection with the following structure:

```
$ tree -lla /home/ansible-dev/collections/ansible_collections
.
├── CHANGELOG.rst
├── changelogs
│   └── config.yaml
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING
├── docs
│   ├── docsite
│   │   └── links.yml
│   └── .keep
├── extensions
│   ├── eda
│   │   └── rulebooks
│   │       └── rulebook.yml
│   └── molecule
│       ├── integration_hello_world
│       │   └── molecule.yml
│       └── utils
│           ├── playbooks
│           │   ├── converge.yml
│           │   └── noop.yml
│           └── vars
│               └── vars.yml
├── galaxy.yml
├── .github
│   └── workflows
│       └── test.yml
├── .isort.cfg
├── LICENSE
├── MAINTAINERS
├── meta
│   └── runtime.yml
├── plugins
│   ├── action
│   │   └── __init__.py
│   ├── cache
│   │   └── __init__.py
│   ├── filter
│   │   ├── hello_world.py
│   │   └── __init__.py
│   ├── inventory
│   │   └── __init__.py
│   ├── modules
│   │   └── __init__.py
│   ├── module_utils
│   │   └── __init__.py
│   ├── plugin_utils
│   │   └── __init__.py
│   ├── sub_plugins
│   │   └── __init__.py
│   └── test
│       └── __init__.py
├── .pre-commit-config.yaml
├── .prettierignore
├── pyproject.toml
├── README.md
├── tests
│   ├── .gitignore
│   ├── integration
│   │   ├── __init__.py
│   │   ├── targets
│   │   │   └── hello_world
│   │   │       └── tasks
│   │   │           └── main.yml
│   │   └── test_integration.py
│   └── unit
│       └── .keep
└── .vscode
    └── extensions.json
```

### Upcoming features

- Scaffold Ansible plugins of your choice with the `create` action.
  Switch to the [create](https://github.com/ansible-community/ansible-creator/tree/create) branch and try it out!

## Licensing

GNU General Public License v3.0 or later.

See [LICENSE](https://www.gnu.org/licenses/gpl-3.0.txt) to see the full text.
