# Installation and Usage

ansible-creator provides two main functionalities: `init` and `add`. The `init` command allows you to initialize an Ansible project, while `add` command allows you to add resources to an existing ansible project.

## Installation

{{ install_from_adt('ansible-creator') }}

To install ansible-creator, use the following pip command:

```console
$ pip install ansible-creator
```

## CLI Usage

The Command-Line Interface (CLI) for ansible-creator provides a straightforward and efficient way to interact with the tool. Users can initiate actions, such as initializing Ansible Collections and other Ansible Projects, through concise commands. The CLI is designed for simplicity, allowing users to execute operations with ease and without the need for an extensive understanding of the tool's intricacies. It serves as a flexible and powerful option for users who prefer command-line workflows, enabling them to integrate ansible-creator seamlessly into their development processes.

If command line is not your preferred method, you can also leverage the GUI interface within VS Code's Ansible extension that offers a more visually intuitive experience of ansible-creator. See [here](content_creation.md).

## Command line completion

`ansible-creator` has experimental command line completion for common shells. Please ensure you have the `argcomplete` package installed and configured.

```shell
$ pip install argcomplete --user
$ activate-global-python-argcomplete --user
```

### General Usage

Get an overview of available commands and options by running:

```console
$ ansible-creator --help
```

## Initialize projects

### Initialize Ansible collection project

The `init collection` command enables you to initialize an Ansible collection project. Use the following command template:

```console
$ ansible-creator init collection <collection-name> <path>
```

#### Positional Arguments

| Parameter       | Description                                             |
| --------------- | ------------------------------------------------------- |
| collection-name | The collection name in the format '<namespace>.<name>'. |
| path            | The destination directory for the collection project.   |

#### Optional Arguments

| Short flag | Long flag      | Flag argument | Description                                                                                                                              |
| ---------- | -------------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| -f         | --force        |               | Force re-initialize the specified directory as an Ansible collection. This flag is deprecated and will be removed soon. (default: False) |
| -o         | --overwrite    |               | Overwrites existing files or directories. (default: False)                                                                               |
| -no        | --no-overwrite |               | Restricts the overwriting operation for files or directories. (default: False)                                                           |
|            | --json         |               | Output messages as JSON (default: False)                                                                                                 |
| --la       | --log-append   | bool          | Append to log file. (choices: true, false) (default: true)                                                                               |
| --lf       | --log-file     | file          | Log file to write to. (default: ./ansible-creator.log)                                                                                   |
| --ll       | --log-level    | level         | Log level for file output. (choices: notset, debug, info, warning, error, critical) (default: notset)                                    |
| --na       | --no-ansi      |               | Disable the use of ANSI codes for terminal color. (default: False)                                                                       |
| -h         | --help         |               | Show this help message and exit                                                                                                          |
| -v         | --verbosity    |               | Give more Cli output. Option is additive, and can be used up to 3 times. (default: 0)                                                    |

#### Example

```console
$ ansible-creator init collection testns.testname $HOME/collections/ansible_collections
```

This command will scaffold the collection `testns.testname` at `/home/ansible-dev/collections/ansible_collections/testns/testname`

#### Generated Ansible Collection Structure

Running the `init collection` command generates an Ansible collection project with a comprehensive directory structure. Explore it using:

```console
$ tree -lla /home/ansible-dev/collections/ansible_collections/testns/testname
.
├── CHANGELOG.rst
├── changelogs
│   └── config.yaml
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING
├── .devcontainer
│   ├── devcontainer.json
│   ├── docker
│   │   └── devcontainer.json
│   └── podman
│       └── devcontainer.json
├── devfile.yaml
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
- `pip install ansible-dev-tools`.
- Invoke `pytest` from collection root.

### Initialize Ansible playbook project

The `init playbook` command enables you to initialize an Ansible playbook project. Use the following command template:

```console
$ ansible-creator init playbook <collection-name> <path>
```

#### Positional Arguments

| Parameter       | Description                                                                       |
| --------------- | --------------------------------------------------------------------------------- |
| collection-name | The name for the playbook adjacent collection in the format '<namespace>.<name>'. |
| path            | The destination directory for the playbook project.                               |

#### Optional Arguments

| Short flag | Long flag      | Flag argument | Description                                                                                                                              |
| ---------- | -------------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| -f         | --force        |               | Force re-initialize the specified directory as an Ansible collection. This flag is deprecated and will be removed soon. (default: False) |
| -o         | --overwrite    |               | Overwrites existing files or directories. (default: False)                                                                               |
| -no        | --no-overwrite |               | Restricts the overwriting operation for files or directories. (default: False)                                                           |
|            | --json         |               | Output messages as JSON (default: False)                                                                                                 |
| --la       | --log-append   | bool          | Append to log file. (choices: true, false) (default: true)                                                                               |
| --lf       | --log-file     | file          | Log file to write to. (default: ./ansible-creator.log)                                                                                   |
| --ll       | --log-level    | level         | Log level for file output. (choices: notset, debug, info, warning, error, critical) (default: notset)                                    |
| --na       | --no-ansi      |               | Disable the use of ANSI codes for terminal color. (default: False)                                                                       |
| -h         | --help         |               | Show this help message and exit                                                                                                          |
| -v         | --verbosity    |               | Give more Cli output. Option is additive, and can be used up to 3 times. (default: 0)                                                    |

Example:

```console
$ ansible-creator init playbook myorg.myproject $HOME/ansible-projects/playbook-project
```

This command will scaffold the new Ansible playbook project at `/home/user/ansible-projects/playbook-project`.

#### Generated Ansible playbook project Structure

Running the `init playbook` command generates an Ansible playbook project with a comprehensive directory structure. Explore it using:

```console
$ tree -la /home/user/ansible-projects/playbook-project
.
├── ansible.cfg
├── ansible-navigator.yml
├── collections
│   ├── ansible_collections
│   │   └── myorg
│   │       └── myproject
│   │           ├── README.md
│   │           └── roles
│   │               └── run
│   │                   ├── README.md
│   │                   └── tasks
│   │                       └── main.yml
│   └── requirements.yml
├── .devcontainer
│   ├── devcontainer.json
│   ├── docker
│   │   └── devcontainer.json
│   └── podman
│       └── devcontainer.json
├── devfile.yaml
├── .github
│   ├── ansible-code-bot.yml
│   └── workflows
│       └── tests.yml
├── inventory
│   ├── group_vars
│   │   ├── all.yml
│   │   └── web_servers.yml
│   ├── hosts.yml
│   └── host_vars
│       ├── server1.yml
│       ├── server2.yml
│       ├── server3.yml
│       ├── switch1.yml
│       └── switch2.yml
├── linux_playbook.yml
├── network_playbook.yml
├── README.md
├── site.yml
└── .vscode
    └── extensions.json
```

It also comes equipped with Github Action Workflows that use [ansible-content-actions](https://github.com/marketplace/actions/ansible-content-actions) for testing and publishing the collection. For details on how to use these, please refer to the following:

- [Using the testing workflow](https://ansible.readthedocs.io/projects/dev-tools/user-guide/ci-setup/)
- [Using the release workflow](https://ansible.readthedocs.io/projects/dev-tools/user-guide/content-release/)

Please ensure that you review any potential `TO-DO` items in the scaffolded content and make the necessary modifications according to your requirements.

### Initialize execution environment project

The `init execution_env` command enables you to initialize an Ansible execution environment project. Use the following command template:

```console
$ ansible-creator init execution_env <path>
```

Example:

```console
$ ansible-creator init execution_env $HOME/ansible-projects/ee-project
```

This command will scaffold the new execution environment playbook project at `/home/user/ansible-projects/ee-project`.

#### Generated Ansible execution environment project Structure

Running the `init execution_env` command generates an Ansible execution environment project with a comprehensive directory structure. Explore it using:

```console
$ tree -la /home/user/ansible-projects/ee-project
.
├── .github
│   └── workflows
│       └── ci.yml
├── .gitignore
├── README.md
└── execution-environment.yml
```

## Add resources

The `add` subcommand allows users to scaffold content types like resources and plugins into an existing project. This feature is designed to streamline the development environment setup by automatically generating the necessary configuration files.

### General Usage

Get an overview of available commands and options by running:

```console
$ ansible-creator add --help
```

#### Positional Arguments

| Parameter | Description                                   |
| --------- | --------------------------------------------- |
| resource  | Add resources to an existing Ansible project. |
| plugin    | Add a plugin to an Ansible collection.        |

#### Optional Arguments

| Short flag | Long flag | Flag argument | Description                      |
| ---------- | --------- | ------------- | -------------------------------- |
| -h         | --help    |               | Show this help message and exit. |

### Add resource to an existing project

The `add resource` command enables you to add a resource to an already existing project. Use the following command template:

```console
$ ansible-creator add resource <resource-type> <path>
```

#### Positional Arguments

| Parameter             | Description                                                      |
| --------------------- | ---------------------------------------------------------------- |
| devcontainer          | Add devcontainer files to an existing Ansible project.           |
| devfile               | Add a devfile file to an existing Ansible project.               |
| role                  | Add a role to an existing Ansible collection.                    |
| execution-environment | Add a sample execution-environment.yml file to an existing path. |

#### Example of adding a resource

```console
$ ansible-creator add resource devcontainer /home/user/..path/to/your/existing_project
```

This command will scaffold the devcontainer directory at `/home/user/..path/to/your/existing_project`

### Add plugins to an existing ansible collection

The `add plugin` command enables you to add a plugin to an existing collection project. Use the following command template:

```console
$ ansible-creator add plugin <plugin-type> <plugin-name> <collection-path>
```

#### Positional Arguments

| Parameter | Description                                             |
| --------- | ------------------------------------------------------- |
| action    | Add an action plugin to an existing Ansible Collection. |
| filter    | Add a filter plugin to an existing Ansible Collection.  |
| lookup    | Add a lookup plugin to an existing Ansible Collection.  |
| module    | Add a generic module to an existing Ansible Collection. |

#### Example of adding a plugin

```console
$ ansible-creator add plugin action test_plugin /home/user/..path/to/your/existing_collection
```

This command will scaffold an action plugin at `/home/user/..path/to/your/existing_collection`
