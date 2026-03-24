<!-- cspell: ignore buildah -->
# Execution Environment Scaffolding

The `ansible-creator init execution_env` command scaffolds a complete
Execution Environment (EE) project, including the EE definition file, a
GitHub Actions CI/CD workflow, and optional configuration for Ansible Galaxy
servers.

## Quick start

```console
ansible-creator init execution_env my-ee-project
```

This produces:

```text
my-ee-project/
├── .github/
│   └── workflows/
│       └── ee-build.yml
├── .gitignore
├── README.md
└── execution-environment.yml
```

## Configuration

EE projects can be customized via CLI flags, inline JSON
(`--ee-config`), or a YAML/JSON config file (`--ee-config-file`).

### Base image

Use `--ee-base-image` or the `base_image` key in `--ee-config`:

```console
ansible-creator init execution_env \
  --ee-base-image registry.redhat.io/ansible-automation-platform-25/ee-minimal-rhel8:latest \
  my-ee-project
```

Official Red Hat EE images are detected automatically; the scaffolded
definition file will use `microdnf` as the package manager and skip
`ansible-core`/`ansible-runner` dependencies (already pre-installed).

### Collections

Add collections with `--ee-collections` (repeatable) or the `collections`
array in `--ee-config`:

```console
ansible-creator init execution_env \
  --ee-collections ansible.posix \
  --ee-collections 'cisco.ios:>=1.0.0' \
  my-ee-project
```

Each collection entry supports `name`, `version`, `type`, and `source`.
For private Git repositories, use token-interpolated URLs:

```json
{
  "collections": [
    {"name": "ansible.posix"},
    {
      "name": "https://${AAP_EE_BUILDER_GITHUB_TOKEN}@github.com/my-org/my-ns.my-col",
      "type": "git",
      "version": "1.0.0"
    }
  ]
}
```

### Python and system dependencies

```json
{
  "python_deps": ["jmespath", "boto3"],
  "system_packages": ["openssh-clients", "sshpass"]
}
```

Or via CLI: `--ee-python-deps jmespath --ee-system-packages openssh-clients`.

### Galaxy servers

The `galaxy_servers` configuration controls how `ansible.cfg` is generated
and how the CI workflow handles Galaxy server tokens.  Each entry describes
one `[galaxy_server.<id>]` section:

```json
{
  "galaxy_servers": [
    {
      "id": "automation_hub",
      "url": "https://console.redhat.com/api/automation-hub/content/published/",
      "auth_url": "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token",
      "token_required": true
    },
    {
      "id": "private_hub",
      "url": "https://pah.corp.example.com/api/galaxy/content/published/",
      "token_required": true
    },
    {
      "id": "galaxy",
      "url": "https://galaxy.ansible.com/"
    }
  ]
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Identifier used in `[galaxy_server.<id>]` and the `ANSIBLE_GALAXY_SERVER_<ID>_TOKEN` env var |
| `url` | yes | Galaxy server content URL |
| `auth_url` | no | SSO/OAuth token endpoint (e.g. Red Hat SSO) |
| `token_required` | no | When `true`, the workflow wires up the corresponding repository secret |

When `galaxy_servers` is provided, ansible-creator generates an `ansible.cfg`
with the server list and a comment for each server that requires a token:

```ini
[galaxy]
server_list = automation_hub, private_hub, galaxy

[galaxy_server.automation_hub]
url = https://console.redhat.com/api/automation-hub/content/published/
auth_url = https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token
# Token: set ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN as a repository secret

[galaxy_server.private_hub]
url = https://pah.corp.example.com/api/galaxy/content/published/
# Token: set ANSIBLE_GALAXY_SERVER_PRIVATE_HUB_TOKEN as a repository secret

[galaxy_server.galaxy]
url = https://galaxy.ansible.com/
```

If `galaxy_servers` is empty and no `ansible_cfg` is provided, no
`ansible.cfg` file is created.

#### Token workflow integration

For each server with `token_required: true`, the scaffolded
`ee-build.yml` workflow:

1. Checks whether the corresponding `ANSIBLE_GALAXY_SERVER_<ID>_TOKEN`
   secret is configured.
2. Passes the token as a `--build-arg` to `buildah bud`.
3. Declares a matching `ARG` directive in the EE definition's
   `prepend_galaxy` section.

Tokens are never written to `ansible.cfg` or persisted in any OCI layer.

### Custom build steps and files

Use `additional_build_steps` and `additional_build_files` to extend the
container build:

```json
{
  "additional_build_steps": {
    "prepend_base": ["RUN mkdir -p /etc/ansible"],
    "append_final": ["COPY _build/configs/custom.cfg /etc/ansible/ansible.cfg"]
  },
  "additional_build_files": [
    {"src": "custom.cfg", "dest": "configs"}
  ]
}
```

Phases: `prepend_base`, `append_base`, `prepend_galaxy`, `prepend_final`,
`append_final`.

### Build options

```json
{
  "options": {
    "package_manager_path": "/usr/bin/microdnf"
  }
}
```

For official Red Hat EE base images, `package_manager_path` is set to
`/usr/bin/microdnf` automatically.

### EE definition file name

The default file name is `execution-environment.yml`.  Override it with
`ee_file_name`:

```json
{
  "ee_file_name": "my-ee-definition.yml"
}
```

### Raw ansible.cfg

For full control, pass `ansible_cfg` as a raw string instead of using
`galaxy_servers`:

```json
{
  "ansible_cfg": "[galaxy]\nserver_list = my_server\n\n[galaxy_server.my_server]\nurl = https://galaxy.example.com/\n"
}
```

When `ansible_cfg` is set, it takes precedence over `galaxy_servers`.

## Full example

```console
ansible-creator init execution_env \
  --ee-config '{
    "name": "ee-network",
    "base_image": "registry.redhat.io/ansible-automation-platform-25/ee-minimal-rhel8:latest",
    "collections": [
      {"name": "cisco.ios"},
      {"name": "ansible.netcommon"}
    ],
    "galaxy_servers": [
      {
        "id": "automation_hub",
        "url": "https://console.redhat.com/api/automation-hub/content/published/",
        "auth_url": "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token",
        "token_required": true
      },
      {
        "id": "galaxy",
        "url": "https://galaxy.ansible.com/"
      }
    ]
  }' \
  my-ee-project
```

This creates:

- `execution-environment.yml` — EE definition with `cisco.ios`,
  `ansible.netcommon`, microdnf, Python 3.11, and an `ARG` directive
  for `ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN`.
- `ansible.cfg` — Galaxy server configuration with a token comment.
- `.github/workflows/ee-build.yml` — CI workflow that checks the
  `ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN` secret and passes it as
  a build arg.

## CI/CD workflow

The scaffolded `ee-build.yml` workflow builds and publishes the EE image.

### Triggers

- **Pull requests** to `main`/`master` — build only (no push).
- **Push** to `main`/`master` — build, push with `latest` and SHA tags.
- **Release** — tag with the release version and `prd`.
- **Manual** (`workflow_dispatch`) — with optional skip-validation toggle.

### Required secrets

Galaxy server tokens follow the Ansible naming convention:

```text
ANSIBLE_GALAXY_SERVER_<ID>_TOKEN
```

where `<ID>` matches the `[galaxy_server.<id>]` section in `ansible.cfg`.
Configure these as GitHub repository secrets.

Additional secrets:

| Secret | Purpose |
|--------|---------|
| `AAP_EE_BUILDER_GITHUB_TOKEN` | GitHub PAT for private collection Git repos |
| `AAP_EE_BUILDER_GITLAB_TOKEN` | GitLab PAT for private collection Git repos |
| `SCM_TOKEN` | Generic SCM token for custom Git servers |
| `REGISTRY_USERNAME` / `REGISTRY_PASSWORD` | Container registry credentials |
| `REDHAT_REGISTRY_PASSWORD` | Red Hat registry authentication for base images |

### Token security

- **Galaxy server tokens** are passed as `--build-arg` values.  With
  `buildah >= 1.24`, `ARG` values do not appear in image history or
  metadata.
- **`ansible.cfg`** (containing server URLs only, never tokens) is
  volume-mounted into the build and never enters any OCI layer.
- **Git credentials** (`~/.git-credentials`) are created only during the
  workflow run and are not part of the image.
