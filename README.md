# Pystrano

[![PyPI version](https://img.shields.io/pypi/v/pystrano.svg)](https://pypi.org/project/pystrano/)
[![Django Packages](https://img.shields.io/badge/Django%20Packages-pystrano-0C4B33.svg)](https://www.djangopackages.org/packages/p/pystrano/)

Capistrano-inspired deployment automation for Django and FastAPI apps.

Pystrano helps you define repeatable SSH-based Python web deployment workflows
with simple YAML playbooks.

- Website: https://pystrano.com
- Documentation: https://pystrano.com/docs
- PyPI: https://pypi.org/project/pystrano/
- Issues: https://github.com/lexpank/pystrano/issues

## Project Status

Pystrano currently supports Django and FastAPI deployment workflows.

Other Python applications may be possible through custom commands, but they are
not the primary supported workflow yet.

## Why Pystrano?

Use Pystrano if:

- you deploy Django or FastAPI apps to one or more servers over SSH
- you want repeatable deployment workflows
- you prefer simple YAML playbooks
- you want release-oriented deploys and rollback-friendly structure
- you are deploying to VPS-style servers with tools like Gunicorn and systemd

Pystrano may be adaptable to other Python applications through custom commands,
but Django and FastAPI are the supported and documented workflows today.

Consider other tools if:

- you need full infrastructure provisioning
- you need container orchestration
- you need complex multi-cloud workflows
- you already have a mature CI/CD platform handling deployments
- you need a fully managed deployment platform

## Installation

Pystrano requires Python 3.12 or newer.

```bash
pip install pystrano
```

## Quickstart

Pystrano reads a deployment config from this default path:

```text
deploy/<app_name>/<environment_name>/deployment.yml
```

For an app named `api` and an environment named `production`, create:

```text
deploy/api/production/deployment.yml
```

Build that file interactively:

```bash
pystrano init production api
```

The init flow also writes a starter `gunicorn.service` or `uvicorn.service`
file referenced by the generated config.

Then inspect the remote commands without executing them:

```bash
pystrano setup production api --dry-run
pystrano deploy production api --dry-run
```

Run the setup flow when the server is ready to be provisioned:

```bash
pystrano setup production api
```

Run the deployment flow:

```bash
pystrano deploy production api
```

Use a different config root or file name when needed:

```bash
pystrano init production api --deploy-config-dir ./ops/deploy --config-file-name pystrano.yml
pystrano deploy production api --deploy-config-dir ./ops/deploy --config-file-name pystrano.yml
```

Add `--verbose` to show more Fabric, Invoke, and Paramiko output.

## Configuration

A deployment config contains a `common` section and a `servers` list.
Values in `common` apply to every server. Values on an individual server override
the common values for that server.

Use `pystrano init <environment> <app>` to create this file interactively. The
command writes to `deploy/<app>/<environment>/deployment.yml` by default,
generates the referenced systemd service file, and prompts before overwriting an
existing file. `pystrano configure <environment> <app>` is accepted as an alias.

```yaml
config_version: 2

common:
  source_code_url: "git@github.com:example/example-django-app.git"
  framework: "django"
  project_root: "apps/example-django-app"
  project_user: "deploy"
  venv_dir: ".venv"
  package_manager: "pip"
  dependency_file: "requirements.txt"
  keep_releases: 5
  system_packages: |
    libpq-dev
    python3-dev
  env_file: "./deploy/api/production/.env"
  ssh_known_hosts: "github.com"
  service_file: "./deploy/api/production/gunicorn.service"
  secrets: "./deploy/api/production/secret.json"
  branch: "main"
  clone_depth: 1

servers:
  - host: "app1.example.com"
    port: 22
    run_migrations: true
    collect_static_files: true

  - host: "app2.example.com"
    run_migrations: false
    collect_static_files: true
```

Common fields used by the current implementation:

- `config_version`: Pystrano config format version. Version 2 configs should declare `2`; missing or older values produce a runtime compatibility warning.
- `source_code_url`: Git repository URL cloned on each deploy.
- `framework`: Deployment workflow. Supported values are `django` and `fastapi`. Defaults to `django`.
- `project_root`: Project directory under `/home/<project_user>/`.
- `project_user`: Remote user that owns and deploys the app.
- `venv_dir`: Virtualenv directory under `/home/<project_user>/`.
- `package_manager`: Dependency installer. Supported values are `pip` and `uv`. Defaults to `pip`.
- `dependency_file`: Dependency file used during install. Defaults to `requirements.txt` for `pip` and `uv.lock` for `uv`.
- `dependency_install_command`: Optional exact dependency install command. When set, Pystrano runs it instead of the built-in `pip` or `uv` command.
- `keep_releases`: Number of release directories to keep. Use `0` or less to keep all.
- `system_packages`: Extra packages installed during `setup`.
- `env_file`: Local dotenv file copied to the remote shared directory during deploy.
- `ssh_known_hosts`: Semicolon-separated hosts added with `ssh-keyscan` during `setup`.
- `service_file`: Optional local systemd service file copied during `setup`.
- `secrets`: Optional semicolon-separated local files copied during `setup` and linked into releases.
- `branch`: Git branch cloned during deploy.
- `clone_depth`: Shallow clone depth. Use `0` or less for a full clone.
- `revision`: Optional tag, SHA, or ref checked out after cloning. When set, Pystrano performs a full clone.
- `migration_command`: FastAPI migration command. Defaults to `<venv_dir>/bin/alembic upgrade head`.
- `static_files_command`: FastAPI static files command. Required when `framework: fastapi` and `collect_static_files: true`.

Server fields:

- `host`: SSH host.
- `port`: SSH port. Defaults to `22`.
- `run_migrations`: Whether to run the framework migration step during deploy.
- `collect_static_files`: Whether to run the framework static files step during deploy.

## Deployment Workflow

`pystrano setup <environment> <app>` connects as `root` and prepares the remote
host. The setup flow creates the project user, copies authorized SSH keys,
creates the shared/releases/current directory structure, installs base packages,
creates the virtualenv, updates known hosts, optionally installs a systemd
service file, and optionally uploads secret files to the shared directory.

`pystrano deploy <environment> <app>` connects as `project_user` and creates a
timestamped release under:

```text
/home/<project_user>/<project_root>/releases/<timestamp>
```

The deploy flow clones the configured repository, copies the dotenv file into
the shared directory, links shared assets, installs Python dependencies, links
configured secrets, optionally runs framework-specific static collection and
migrations, updates the `current` symlink, optionally restarts the configured
systemd service, and removes old releases according to `keep_releases`.

For `package_manager: pip`, dependencies are installed with:

```text
<venv_dir>/bin/pip install -r <dependency_file>
```

For `package_manager: uv` with `dependency_file: uv.lock`, Pystrano ensures
`uv` exists in the virtualenv, then runs:

```text
UV_PROJECT_ENVIRONMENT=<venv_dir> <venv_dir>/bin/uv sync --frozen --no-dev
```

If `package_manager: uv` is configured with another dependency file, Pystrano
runs:

```text
<venv_dir>/bin/uv pip install --python <python_path> -r <dependency_file>
```

Set `dependency_install_command` when your project needs a custom flow such as
additional uv flags or dependency groups.

For Django, the framework steps are:

```text
<python_path> manage.py collectstatic --noinput
<python_path> manage.py migrate
```

For FastAPI, migrations default to:

```text
<venv_dir>/bin/alembic upgrade head
```

Set `migration_command` to override the FastAPI migration command. Set
`static_files_command` when a FastAPI deployment needs a custom static asset
build step.

Pystrano does not currently expose a `rollback` CLI command. Deployments are
release-oriented, so a maintainer can inspect previous release directories on
the server and manually repoint the `current` symlink if needed. Keep
`keep_releases` high enough for the rollback window you want.

## Example: Django on a VPS

See [examples/django-gunicorn-systemd](examples/django-gunicorn-systemd/) for a
starting point that combines Django, Gunicorn, systemd, SSH deployment, shared
files, and release cleanup.

## Example: FastAPI on a VPS

See [examples/fastapi-uvicorn-systemd](examples/fastapi-uvicorn-systemd/) for a
starting point that combines FastAPI, Uvicorn, systemd, SSH deployment, Alembic
migrations, shared files, and release cleanup.

## Maintainer Checklist

Recommended GitHub repository metadata:

- Repository description: `Capistrano-inspired deployment automation for Django and FastAPI apps.`
- Website: `https://pystrano.com`
- Topics: `python`, `django`, `fastapi`, `deployment`, `deploy`, `cli`, `yaml`, `capistrano`, `devops`, `ssh`, `systemd`, `gunicorn`, `uvicorn`, `vps`
