# Execution Environment Project

This is a sample execution environment project to build and publish your EE.

## Directory Structure

```shell
├── .github
│   └── workflows
│       └── ee-build.yml    # CI/CD workflow for building and publishing
├── .gitignore
├── README.md
└── execution-environment.yml
```

## CI/CD Workflow Features

The included GitHub Actions workflow (`ee-build.yml`) provides:

### Token Validation

- Validates Automation Hub tokens before starting builds
- Fails fast if credentials are invalid or expired

### Base Image Lifecycle Checks

- Warns if the base image is older than 40 days
- Fails if the base image is older than 80 days
- Helps ensure your EE stays up-to-date with security patches

### Automation Hub Support

- Supports both Red Hat Automation Hub (console.redhat.com) and on-premises AAP
- Configurable via repository variables and secrets
- Falls back to public Galaxy if no token is configured

### Production Release Workflow

- Automatic tagging on release
- Preserves previous production image as `previous` tag for rollback
- Supports semantic versioning

## Required Secrets and Variables

### Secrets (Repository Settings > Secrets)

| Secret | Required | Description |
|--------|----------|-------------|
| `ANSIBLE_GALAXY_SERVER_TOKEN` | No | Token for Automation Hub authentication |
| `AAP_EE_BUILDER_GITHUB_TOKEN` | No | GitHub PAT for private collection repositories |
| `AAP_EE_BUILDER_GITLAB_TOKEN` | No | GitLab PAT for private collection repositories |
| `SCM_TOKEN` | No | Generic SCM token for custom Git servers |
| `REGISTRY_USERNAME` | No | Container registry username (defaults to `github.actor`) |
| `REGISTRY_PASSWORD` | No | Container registry password (defaults to `GITHUB_TOKEN`) |
| `REDHAT_REGISTRY_PASSWORD` | No | Red Hat registry password (for pulling base images) |

#### Secret Naming Convention

For organization-specific secrets, consider the naming pattern:

- `AAP_EE_BUILDER_GITHUB_<ORG_NAME>` - GitHub token for specific org
- `AAP_EE_BUILDER_GITLAB_<ORG_NAME>` - GitLab token for specific org

Example: `AAP_EE_BUILDER_GITHUB_MYCOMPANY` for collections from `github.com/mycompany/*`

> **Note:** The workflow references `AAP_EE_BUILDER_GITHUB_TOKEN` and
> `AAP_EE_BUILDER_GITLAB_TOKEN` by default. If you use org-specific secret
> names, update the workflow to reference them accordingly.

### Variables (Repository Settings > Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `EE_REGISTRY` | `ghcr.io` | Container registry URL |
| `EE_IMAGE_NAME` | `<owner>/<repo>` | Image name (GHCR requires the `owner/repo` namespace) |
| `AUTOMATION_HUB_URL` | `console.redhat.com` | Automation Hub URL |
| `REDHAT_REGISTRY_USERNAME` | - | Red Hat registry username |
| `SCM_SERVER` | - | Custom Git server hostname (for `SCM_TOKEN`) |

## Usage

### Building Locally

```bash
# Install ansible-builder
pip install ansible-builder

# Create build context
ansible-builder create --file execution-environment.yml

# Build the image
podman build -t my-ee:latest context/
```

### Triggering CI/CD

- **Pull Request**: Builds and tests the EE (no push to registry)
- **Push to main**: Builds, tests, and pushes with `latest` and commit SHA tags
- **Release**: Tags image with version number and `prd` tag

## Customization

Edit `execution-environment.yml` to customize:

- Base image
- Ansible collections
- Python dependencies
- System packages

See the [ansible-builder documentation](https://ansible.readthedocs.io/projects/builder/en/latest/)
for more details on execution environment configuration.
