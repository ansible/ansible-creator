# Next Steps

Complete the following setup to enable automated EE builds.

## Optional Secrets

| Secret | Purpose |
|--------|---------|
| `REGISTRY_USERNAME` | Container registry username (defaults to `github.actor`) |
| `REGISTRY_PASSWORD` | Container registry password (defaults to `GITHUB_TOKEN`) |
| `REDHAT_REGISTRY_PASSWORD` | Red Hat registry password (for pulling base images) |

## Repository Variables

Configure these in **Settings > Secrets and variables > Actions > Variables**.

| Variable | Default | Purpose |
|----------|---------|---------|
| `EE_REGISTRY` | `ghcr.io` | Container registry hostname |
| `EE_IMAGE_NAME` | `<owner>/<repo>` | Image name |
| `REDHAT_REGISTRY_USERNAME` | - | Red Hat registry username |

## Verify Your Setup

1. Review the optional secrets listed above and configure any you need
2. Push to a branch or open a pull request to trigger the workflow
3. Check the workflow run in **Actions** for any authentication errors
4. Once the build succeeds, verify the image in your container registry
