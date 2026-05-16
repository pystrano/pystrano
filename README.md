# Pystrano

Capistrano-inspired deployment automation for Django apps.

Pystrano helps you define repeatable SSH-based Django deployment workflows with
simple YAML playbooks.

- Website: https://pystrano.com
- Documentation: https://pystrano.com/docs
- PyPI: https://pypi.org/project/pystrano/
- Issues: https://github.com/lexpank/pystrano/issues

## Project Status

Pystrano is currently focused on Django deployment workflows. Django is the
tested and documented path today.

FastAPI support is planned, but it should be treated as roadmap work until the
implementation, tests, and documentation are released.

Other Python applications may be possible through custom commands, but they are
not the primary supported workflow yet.

## Why Pystrano?

Use Pystrano if:

- you deploy Django apps to one or more servers over SSH
- you want repeatable deployment workflows
- you prefer simple YAML playbooks
- you want release-oriented deploys and rollback-friendly structure
- you are deploying to VPS-style servers with tools like Gunicorn and systemd

Pystrano may be adaptable to other Python applications through custom commands,
but Django is the supported and documented workflow today.

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
pystrano deploy production api --deploy-config-dir ./ops/deploy --config-file-name pystrano.yml
```

Add `--verbose` to show more Fabric, Invoke, and Paramiko output.

## Configuration

A deployment config contains a `common` section and a `servers` list.
Values in `common` apply to every server. Values on an individual server override
the common values for that server.

```yaml
common:
  source_code_url: "git@github.com:example/example-django-app.git"
  project_root: "apps/example-django-app"
  project_user: "deploy"
  venv_dir: ".venv"
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

- `source_code_url`: Git repository URL cloned on each deploy.
- `project_root`: Project directory under `/home/<project_user>/`.
- `project_user`: Remote user that owns and deploys the app.
- `venv_dir`: Virtualenv directory under `/home/<project_user>/`.
- `keep_releases`: Number of release directories to keep. Use `0` or less to keep all.
- `system_packages`: Extra packages installed during `setup`.
- `env_file`: Local dotenv file copied to the remote shared directory during deploy.
- `ssh_known_hosts`: Semicolon-separated hosts added with `ssh-keyscan` during `setup`.
- `service_file`: Optional local systemd service file copied during `setup`.
- `secrets`: Optional semicolon-separated local files copied during `setup` and linked into releases.
- `branch`: Git branch cloned during deploy.
- `clone_depth`: Shallow clone depth. Use `0` or less for a full clone.
- `revision`: Optional tag, SHA, or ref checked out after cloning. When set, Pystrano performs a full clone.

Server fields:

- `host`: SSH host.
- `port`: SSH port. Defaults to `22`.
- `run_migrations`: Whether to run `manage.py migrate` during deploy.
- `collect_static_files`: Whether to run `manage.py collectstatic --noinput` during deploy.

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
the shared directory, links shared assets, installs `requirements.txt`, links
configured secrets, optionally runs Django static collection and migrations,
updates the `current` symlink, optionally restarts the configured systemd
service, and removes old releases according to `keep_releases`.

Pystrano does not currently expose a `rollback` CLI command. Deployments are
release-oriented, so a maintainer can inspect previous release directories on
the server and manually repoint the `current` symlink if needed. Keep
`keep_releases` high enough for the rollback window you want.

## Example: Django on a VPS

See [examples/django-gunicorn-systemd](examples/django-gunicorn-systemd/) for a
starting point that combines Django, Gunicorn, systemd, SSH deployment, shared
files, and release cleanup.

## Maintainer Checklist

Recommended GitHub repository metadata:

- Repository description: `Capistrano-inspired deployment automation for Django apps.`
- Website: `https://pystrano.com`
- Topics: `python`, `django`, `deployment`, `deploy`, `cli`, `yaml`, `capistrano`, `devops`, `ssh`, `systemd`, `gunicorn`, `vps`
