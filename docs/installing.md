# Installation and Usage

ansible-creator provides two main functionalities: `init` and `create`. The `init` command allows you to initialize an Ansible Collection, while `create` command allows you scaffold ansible plugins of your choice.

## Installation

!!! Recommendation

    The **recommended** approach to install `ansible-creator` is using the
    `ansible-dev-tools` package.
    [Ansible Development Tools (ADT)](https://ansible.readthedocs.io/projects/dev-tools/)
    aims to streamline the setup and usage of several tools needed in order to
    create [Ansible](https://www.ansible.com) content. ADT combines critical Ansible
    development packages into a unified Python package.

    ```bash
    # This also installs ansible-core if it is not already installed
    pip3 install ansible-dev-tools
    ```

To install ansible-creator, use the following pip command:

```console
$ pip install ansible-creator
```

## CLI Usage

The Command-Line Interface (CLI) for ansible-creator provides a straightforward and efficient way to interact with the tool. Users can initiate actions, such as initializing Ansible Collections, through concise commands. The CLI is designed for simplicity, allowing users to execute operations with ease and without the need for an extensive understanding of the tool's intricacies. It serves as a flexible and powerful option for users who prefer command-line workflows, enabling them to integrate ansible-creator seamlessly into their development processes.

If command line is not your preferred method, you can also leverage the GUI interface within VS Code's Ansible extension that offers a more visually intuitive experience of ansible-creator. See [here](collection_creation.md).

### General Usage

Get an overview of available commands and options by running:

```console
$ ansible-creator --help
```

### Initialize Ansible Collection (`init` subcommand)

The `init` command enables you to initialize an Ansible Collection to create a foundational structure for the project. Use the following command template:

```console
$ ansible-creator init <collection-name> --init-path <path>
```

#### Positional Argument(s)

| Parameter  | Description                                                          |
| ---------- | -------------------------------------------------------------------- |
| collection | The name of the collection in the format `<namespace>.<collection>`. |

#### Optional Arguments

| Parameter                 | Description                                                                                           |
| ------------------------- | ----------------------------------------------------------------------------------------------------- |
| -h, --help                | Show help message and exit.                                                                           |
| --na, --no-ansi           | Disable the use of ANSI codes for terminal color.                                                     |
| --lf, --log-file <file>   | Log file to write to.                                                                                 |
| --ll, --log-level <level> | Log level (notset, debug, info, warning, error, critical) for file output.                            |
| --la, --log-append <bool> | Append to log file.                                                                                   |
| --json                    | Output messages as JSON.                                                                              |
| -v, --verbose             | Give more CLI output. Option is additive and can be used up to 3 times.                               |
| --init-path <path>        | The path where the skeleton collection will be scaffolded (default is the current working directory). |
| --force                   | Force re-initialize the specified directory as an Ansible collection.                                 |

#### Example

```console
$ ansible-creator init testns.testname --init-path $HOME/collections/ansible_collections
```

This command will scaffold the collection `testns.testname` at `/home/ansible-dev/collections/ansible_collections/testns/testname`

#### Generated Ansible Collection Structure

Running the init command generates an Ansible Collection with a comprehensive directory structure. Explore it using:

```console
$ tree -lla /home/ansible-dev/collections/ansible_collections/testns/testname
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
│       ├── release.yml
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
├── roles
│   └── run
│       ├── defaults
│       │   └── main.yml
│       ├── files
│       │   └── .keep
│       ├── handlers
│       │   └── main.yaml
│       ├── meta
│       │   └── main.yml
│       ├── README.md
│       ├── tasks
│       │   └── main.yml
│       ├── templates
│       │   └── .keep
│       ├── tests
│       │   └── inventory
│       ├── vars
│       │   └── main.yml
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

**Note:**

The scaffolded collection includes a `hello_world` filter plugin, along with a molecule scenario and an integration test target for it, that can be run using `pytest`. This serves as an example for you to refer when writing tests for your Ansible plugins and can be removed when it is no longer required.

To run the `hello_world` integration test, follow these steps:

- Git initialize the repository containing the scaffolded collection with `git init`.
- `pip install ansible-core molecule pytest-xdist pytest-ansible`.
- Invoke `pytest` from collection root.

It also comes equipped with Github Action Workflows that use [ansible-content-actions](https://github.com/marketplace/actions/ansible-content-actions) for testing and publishing the collection. For details on how to use these, please refer to the following:

- [Using the testing workflow](https://ansible.readthedocs.io/projects/dev-tools/user-guide/ci-setup/)
- [Using the release workflow](https://ansible.readthedocs.io/projects/dev-tools/user-guide/content-release/)

Please ensure that you review any potential `TO-DO` items in the scaffolded content and make the necessary modifications according to your requirements.
