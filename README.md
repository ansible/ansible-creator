# ansible-creator

A CLI tool for scaffolding Ansible Content.

## Installation

```
$ pip install git+https://github.com/ansible-community/ansible-creator
```

## Usage

```
$ ansible-creator --help
usage: ansible-creator [-h] [--version] {init} ...

Tool to scaffold Ansible Content. Get started by looking at the help text.

positional arguments:
   {init}               The command to invoke.
    init                Initialize an Ansible Collection.

optional arguments:
  -h, --help            show this help message and exit
  --version             Print ansible-creator version and exit.
```

### Initialize an Ansible Collection skeleton with 'init'

```
$ ansible-creator init --help
usage: ansible-creator init [-h] [--verbose] [--init-path INIT_PATH] [--force] collection_name

Creates the skeleton framework of an Ansible collection.

positional arguments:
  collection_name       The collection name in the format ``<namespace>.<collection>``.

optional arguments:
  -h, --help            show this help message and exit
  --verbose             Increase output verbosity
  --init-path INIT_PATH
                        The path in which the skeleton collection will be created.
                        The default is the current working directory.
  --force               Force re-initialize the specified directory as an Ansible collection.
```

```
$ ansible-creator init namespace.name --init-path $HOME
INFO     starting requested action 'init'
INFO     collection namespace.name successfully created at /home/ansible
```

Running the above command generates an Ansible Collection with the following structure:

```
$ tree -lla /home/ansible/namespace/name
/home/ansible/namespace/name
├── CHANGELOG.rst
├── changelogs
│   └── config.yaml
├── docs
│   ├── docsite
│   │   └── links.yml
│   └── .keep
├── galaxy.yml
├── .github
│   └── workflows
│       └── test.yml
├── .isort.cfg
├── LICENSE
├── meta
│   └── runtime.yml
├── plugins
│   ├── action
│   │   └── __init__.py
│   ├── cache
│   │   └── __init__.py
│   ├── filter
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
│   │   └── targets
│   │       └── .keep
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
