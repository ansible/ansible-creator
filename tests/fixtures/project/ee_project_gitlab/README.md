# Execution Environment Project

This is a sample execution environment project to build and publish your EE.

## Directory Structure

```shell
├── .gitlab-ci.yml          # GitLab CI/CD pipeline for building and publishing
├── .gitignore
├── README.md
└── execution-environment.yml
```

## CI/CD Workflow Features

The included GitLab CI pipeline (`.gitlab-ci.yml`) provides:

### Token Validation

- Validates configured tokens before starting builds
- Fails fast if credentials are missing

### Base Image Lifecycle Checks

- Warns if the base image is older than 40 days
- Fails if the base image is older than 80 days
- Helps ensure your EE stays up-to-date with security patches

### Production Release Workflow

- Automatic tagging on release
- Preserves previous production image as `previous` tag for rollback
- Supports semantic versioning

## Required Secrets and Variables

### CI/CD Variables (Settings > CI/CD > Variables)

| Variable | Required | Description |
|----------|----------|-------------|
| `REGISTRY_USERNAME` | No | Container registry username (defaults to `CI_REGISTRY_USER`) |
| `REGISTRY_PASSWORD` | No | Container registry password (defaults to `CI_REGISTRY_PASSWORD`) |
| `REDHAT_REGISTRY_PASSWORD` | No | Red Hat registry password (for pulling base images) |

### Additional CI/CD Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EE_REGISTRY` | `ghcr.io` | Container registry hostname |
| `EE_IMAGE_NAME` | `$CI_PROJECT_PATH` | Image name / path in the registry |
| `REDHAT_REGISTRY_USERNAME` | - | Red Hat registry username |

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

- **Tag push**, **manual pipeline** (Run pipeline), **API**, or **pipeline trigger**: runs build and push
- **Tag pipeline**: release job tags the image with the Git tag, `latest`, and `prd`

## Customization

Edit `execution-environment.yml` to customize:

- Base image
- Ansible collections
- Python dependencies
- System packages

See the [ansible-builder documentation](https://ansible.readthedocs.io/projects/builder/en/latest/)
for more details on execution environment configuration.
