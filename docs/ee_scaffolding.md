<!-- cspell: ignore buildah -->
# Execution Environment Scaffolding

The `ansible-creator init execution_env` command scaffolds a complete
Execution Environment (EE) project, including the EE definition file, a
CI/CD workflow for **GitHub Actions** (default) or **GitLab CI**, and optional
configuration for Ansible Galaxy servers.

## Quick start

```console
ansible-creator init execution_env my-ee-project
```

This produces a GitHub Actions–based project:

```text
my-ee-project/
├── .github/
│   └── workflows/
│       └── ee-build.yml
├── .gitignore
├── README.md
└── execution-environment.yml
```

### GitLab instead of GitHub

Use `--scm-provider gitlab` to scaffold `.gitlab-ci.yml` instead of
`.github/workflows/ee-build.yml`:

```console
ansible-creator init execution_env --scm-provider gitlab my-ee-gitlab
```

```text
my-ee-gitlab/
├── .gitlab-ci.yml
├── .gitignore
├── README.md
└── execution-environment.yml
```

Galaxy and SCM tokens use the **same variable names** as in the GitHub
workflow (`ANSIBLE_GALAXY_SERVER_<ID>_TOKEN`, plus each
`scm_servers[*].token_env_var`). Configure them under **Settings →
CI/CD → Variables** (mark secrets as masked/protected). For pushes to
GitLab Container Registry you can rely on the predefined
`CI_REGISTRY_USER` / `CI_REGISTRY_PASSWORD`, or set
`REGISTRY_USERNAME` / `REGISTRY_PASSWORD` for another registry. See
[GitLab CI pipeline](#gitlab-ci-pipeline-gitlab-ciyml).

You can add the same CI files to an existing directory with:

```console
ansible-creator add resource ee-ci --scm-provider gitlab /path/to/project
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
For private Git repositories, use token-interpolated URLs with matching
`scm_servers` entries (see [SCM servers](#scm-servers)):

```json
{
  "collections": [
    {"name": "ansible.posix"},
    {
      "name": "https://${GITHUB_ORG1_TOKEN}@github.com/my-org/my-ns.my-col",
      "type": "git",
      "version": "1.0.0"
    }
  ],
  "scm_servers": [
    {
      "id": "github_org1",
      "hostname": "github.com",
      "token_env_var": "GITHUB_ORG1_TOKEN"
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

For each server with `token_required: true`, the scaffolded workflow
(GitHub Actions `ee-build.yml` or GitLab `.gitlab-ci.yml`):

1. Checks whether the corresponding `ANSIBLE_GALAXY_SERVER_<ID>_TOKEN`
   is configured (repository **secret** on GitHub, **CI/CD variable** on
   GitLab).
2. Passes the token as a `--build-arg` to `podman build` / `buildah bud`.
3. Declares a matching `ARG` directive in the EE definition's
   `prepend_galaxy` section.

Tokens are never written to `ansible.cfg` or persisted in any OCI layer.

### SCM servers

The `scm_servers` configuration controls how the CI workflow handles
tokens for private Git-hosted collections.  Each entry describes one
SCM provider or organization:

```json
{
  "scm_servers": [
    {
      "id": "github_org1",
      "hostname": "github.com",
      "token_env_var": "GITHUB_ORG1_TOKEN"
    },
    {
      "id": "internal_gitlab",
      "hostname": "gitlab.corp.com",
      "token_env_var": "INTERNAL_GITLAB_TOKEN"
    }
  ]
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Identifier (lowercase letters, numbers, underscores) |
| `hostname` | yes | Git server hostname (e.g. `github.com`) |
| `token_env_var` | yes | Environment variable name for the token. Must start with an uppercase letter and contain only uppercase letters, digits, and underscores (e.g. `GITHUB_ORG1_TOKEN`). This name is used as the GitHub Actions secret name or the GitLab CI/CD variable name. |

#### Collection URL naming convention

Collection URLs must embed the token variable as a `${...}` placeholder.
The placeholder name must **exactly match** the `token_env_var` value
from the corresponding `scm_servers` entry.  At build time, `envsubst`
resolves these placeholders to the actual secret values.

```json
{
  "collections": [
    {
      "name": "https://${GITHUB_ORG1_TOKEN}@github.com/org1/my-collection",
      "type": "git"
    }
  ],
  "scm_servers": [
    {
      "id": "github_org1",
      "hostname": "github.com",
      "token_env_var": "GITHUB_ORG1_TOKEN"
    }
  ]
}
```

In the example above, `${GITHUB_ORG1_TOKEN}` in the collection URL
matches the `token_env_var` of the `github_org1` SCM server entry.
The workflow will:

1. Expect a GitHub Actions secret or GitLab CI/CD variable named
   `GITHUB_ORG1_TOKEN`
2. Validate it is configured before building
3. Resolve `${GITHUB_ORG1_TOKEN}` in the generated requirements file
   via `envsubst`

#### Build-time token flow

1. `ansible-builder create` generates the build context with unresolved
   `${TOKEN}` references in the requirements file.
2. The workflow runs `envsubst` to resolve the tokens in the generated
   `context/_build/requirements.yml` (post-processing).
3. `buildah bud` builds the image.  The resolved URLs exist only in
   the intermediate `galaxy` build stage.
4. The final image only contains installed collections — no tokens,
   no requirements file with URLs.

#### Security

The multi-stage build generated by `ansible-builder` ensures tokens
never reach the final image:

- The `galaxy` stage `COPY`s the requirements file and runs
  `ansible-galaxy collection install`.
- The `final` stage only `COPY --from=galaxy /usr/share/ansible`
  (installed collections, not source files).
- Intermediate stages are not tagged or pushed to any registry.

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

The same `--ee-config` with `--scm-provider gitlab` swaps the last item
for `.gitlab-ci.yml` (and omits `.github/workflows/`):

```console
ansible-creator init execution_env \
  --scm-provider gitlab \
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
  my-ee-gitlab
```

## CI/CD workflow

Scaffolded pipelines build and publish the EE image using **podman** (GitLab)
or **buildah** (GitHub), with the same token and `envsubst` model.

### GitHub Actions (`ee-build.yml`)

#### Triggers

- **Pull requests** to `main`/`master` — build only (no push).
- **Push** to `main`/`master` — build, push with `latest` and SHA tags.
- **Release** — tag with the release version and `prd`.
- **Manual** (`workflow_dispatch`) — with optional skip-validation toggle.

#### Required secrets

Galaxy server tokens follow the Ansible naming convention:

```text
ANSIBLE_GALAXY_SERVER_<ID>_TOKEN
```

where `<ID>` matches the `[galaxy_server.<id>]` section in `ansible.cfg`.
Configure these as GitHub repository secrets.

SCM tokens are declared via the `scm_servers` configuration (see
[SCM servers](#scm-servers)).  The workflow dynamically generates
checks and environment variables for each configured token.

Additional secrets:

| Secret | Purpose |
|--------|---------|
| `REGISTRY_USERNAME` / `REGISTRY_PASSWORD` | Container registry credentials |
| `REDHAT_REGISTRY_PASSWORD` | Red Hat registry authentication for base images |

### GitLab CI pipeline (`.gitlab-ci.yml`)

#### Triggers

The pipeline runs when:

- A **Git tag** is pushed, or
- The pipeline is started from the **web UI**, **API**, or an **upstream trigger**.

(There is no default “every push to `main`” rule; adjust `workflow: rules`
in `.gitlab-ci.yml` if you want branch pipelines.)

#### Required CI/CD variables

Use the **same names** as GitHub secrets. Galaxy tokens:

```text
ANSIBLE_GALAXY_SERVER_<ID>_TOKEN
```

Set each under **Settings → CI/CD → Variables**. SCM `token_env_var`
values from `scm_servers` are listed in the header comments of
`.gitlab-ci.yml`.

Registry-related variables:

| Variable | Purpose |
|----------|---------|
| `REGISTRY_USERNAME` / `REGISTRY_PASSWORD` | Push target registry. If unset, the job uses `CI_REGISTRY_USER` / `CI_REGISTRY_PASSWORD` (GitLab Container Registry). |
| `REDHAT_REGISTRY_USERNAME` / `REDHAT_REGISTRY_PASSWORD` | Login to `registry.redhat.io` for Red Hat base images |

Optional: `SKIP_BASE_IMAGE_VALIDATION`, `STORAGE_DRIVER` (e.g. `vfs` for
some runners). The template expects a **podman**-capable image (e.g.
`quay.io/podman/stable`) and **podman 4+** so build `ARG`s are not stored
in image history.

The pipeline uses a single `REGISTRY_AUTHFILE` under the project directory
for `podman login`, `podman build`, and `podman push`, so registries that
require authentication on layer/blob checks (e.g. Quay.io) succeed.
`IMAGE_NAME` is lowercased before tagging and pushing because many OCI
registries reject mixed-case repository paths.

### Token security

- **Galaxy server tokens** are passed as `--build-arg` values.  With
  `buildah >= 1.24` / **podman 4+**, `ARG` values do not appear in image
  history or metadata.
- **SCM tokens** are resolved via `envsubst` into the build context
  after `ansible-builder create`.  The multi-stage build ensures tokens
  only exist in intermediate stages, never in the final image.
- **`ansible.cfg`** (containing server URLs only, never tokens) is
  volume-mounted into the build and never enters any OCI layer.
