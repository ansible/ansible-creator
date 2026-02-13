# Python API (Internal)

!!! warning "Internal Use Only"

    This API is intended for use by **internal Ansible ecosystem tooling**
    (ansible-dev-tools server, VS Code extension, MCP servers). It is not a
    public contract for end users and may change between minor releases.

## Overview

The `ansible_creator.api` module provides a programmatic Python interface to
ansible-creator's scaffolding capabilities. Instead of shelling out to the CLI,
ecosystem tools can import the `V1` class and call its methods directly.

The API is **dynamic and schema-driven**: it introspects the argparser tree at
runtime to discover available commands and their parameters. When new
subcommands or resource types are added to ansible-creator, they are
automatically available through the API with no code changes required.

## Quick start

```python
from ansible_creator.api import V1

api = V1(verbosity=1)

# Discover what the CLI can do
schema = api.schema()

# Scaffold a collection
result = api.run("init", "collection", collection="testns.testcol")
print(result.status)  # "success"
print(result.path)    # Path to temp dir with scaffolded content

# Add a filter plugin
result = api.run("add", "plugin", "filter", plugin_name="my_filter")
```

## API reference

### `V1(verbosity=0)`

Create an API instance.

| Parameter   | Type  | Default | Description                                          |
|-------------|-------|---------|------------------------------------------------------|
| `verbosity` | `int` | `0`     | Log detail level: 0 = normal, 1 = info, 2 = debug   |

### `V1.schema() -> dict`

Returns the full CLI capability schema as a nested dictionary. The schema
describes all available subcommands, their parameters, types, defaults, and
descriptions.

**Example response structure:**

```json
{
  "name": "ansible-creator",
  "description": "The fastest way to generate all your ansible content.",
  "parameters": { ... },
  "subcommands": {
    "init": {
      "name": "init",
      "subcommands": {
        "collection": { "name": "collection", "parameters": { ... } },
        "playbook": { ... },
        "execution_env": { ... }
      }
    },
    "add": {
      "name": "add",
      "subcommands": {
        "resource": { "subcommands": { "devfile": { ... }, ... } },
        "plugin": { "subcommands": { "filter": { ... }, ... } }
      }
    }
  }
}
```

### `V1.schema_for(*path) -> dict`

Returns the schema subtree for a specific command path.

```python
# Get parameters for "init collection"
params = api.schema_for("init", "collection")
print(params["parameters"]["properties"].keys())
# dict_keys(['collection', 'overwrite', 'no_overwrite', ...])
```

Raises `KeyError` if the command path is invalid.

### `V1.run(*command_path, **kwargs) -> CreatorResult`

Execute a command dynamically. The command path segments identify the
subcommand, and keyword arguments supply parameters.

```python
# Initialize a collection
result = api.run("init", "collection", collection="myns.mycol")

# Add a devcontainer resource
result = api.run("add", "resource", "devcontainer")

# Add a lookup plugin
result = api.run("add", "plugin", "lookup", plugin_name="my_lookup")
```

**Important:** The scaffolded content is placed in a temporary directory
returned via `result.path`. The caller is responsible for copying what they
need and cleaning up (e.g., `shutil.rmtree(result.path)`).

## `CreatorResult` dataclass

| Field     | Type              | Description                                                |
|-----------|-------------------|------------------------------------------------------------|
| `status`  | `"success"` or `"error"` | Whether the operation succeeded                     |
| `path`    | `pathlib.Path`    | Temp directory containing scaffolded content               |
| `logs`    | `list[str]`       | Captured log messages (format: `"Level: message"`)         |
| `message` | `str`             | Summary on success, error description on failure           |

## Schema structure

Each node in the schema tree follows this structure:

```json
{
  "name": "command-name",
  "description": "Help text for this command",
  "parameters": {
    "type": "object",
    "properties": {
      "param_name": {
        "type": "string|boolean|int|array",
        "description": "Parameter help text",
        "default": "default-value",
        "aliases": ["--flag", "-f"],
        "enum": ["choice1", "choice2"]
      }
    },
    "required": ["param_name"]
  },
  "subcommands": {
    "child": { ... }
  }
}
```

**Parameter types** are inferred from the argparse actions:

- `"string"` — default for most arguments
- `"boolean"` — for store-true / store-false flags
- `"int"` / `"float"` — when a type converter is specified
- `"array"` — for nargs `+` or `*`

**Routing parameters** (`subcommand`, `project`, `type`, `resource_type`,
`plugin_type`) are excluded from the schema — they are implicit in the command
tree path rather than user-facing parameters.

## Discovering parameters at runtime

Because the API is schema-driven, you can discover the parameters for any
command at runtime:

```python
api = V1()

# What init project types exist?
init_schema = api.schema_for("init")
print(list(init_schema["subcommands"].keys()))
# ['collection', 'execution_env', 'playbook']

# What parameters does "add resource devfile" accept?
devfile_schema = api.schema_for("add", "resource", "devfile")
for name, info in devfile_schema["parameters"]["properties"].items():
    print(f"  {name}: {info['type']} — {info['description']}")
```

## Error handling

Errors are returned in the `CreatorResult` rather than raised as exceptions:

```python
result = api.run("init", "nonexistent")
assert result.status == "error"
assert "Invalid command path" in result.message
```

The `logs` field may contain captured messages even on error, which can be
helpful for debugging.
