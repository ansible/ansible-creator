# Next Steps

Complete the following setup to enable automated EE builds.

## Optional CI/CD variables

| Variable | Purpose |
|----------|---------|
| `REGISTRY_USERNAME` | Container registry username (defaults to `CI_REGISTRY_USER`) |
| `REGISTRY_PASSWORD` | Container registry password (defaults to `CI_REGISTRY_PASSWORD`) |
| `REDHAT_REGISTRY_PASSWORD` | Red Hat registry password (for pulling base images) |

## Additional CI/CD variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `EE_REGISTRY` | `ghcr.io` | Container registry hostname |
| `EE_IMAGE_NAME` | (see `.gitlab-ci.yml`) | Image name in the registry |
| `REDHAT_REGISTRY_USERNAME` | - | Red Hat registry username |

## Verify your setup

1. Review the optional variables listed above and configure any you need
2. Run a pipeline (for example **CI/CD > Pipelines > Run pipeline**) or push a tag
3. Open the pipeline job logs for any authentication errors
4. Once the build succeeds, verify the image in your container registry
