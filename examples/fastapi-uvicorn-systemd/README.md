# FastAPI, Uvicorn, and systemd Example

This example is intended as a starting point, not a complete production
infrastructure template.

It shows a Pystrano config for deploying a FastAPI app to a VPS-style Linux
server over SSH. Replace the placeholder values before running commands.

## Files

- `deployment.yml`: Example Pystrano configuration.
- Your local dotenv file, systemd service file, and optional secret files should
  live outside this example or be added to your own private deploy directory.

## Suggested Layout

Pystrano looks for configs in this shape by default:

```text
deploy/<app_name>/<environment_name>/deployment.yml
```

For this example, you could copy the config to:

```text
deploy/example_fastapi_app/production/deployment.yml
```

The example config references local files such as:

```text
deploy/example_fastapi_app/production/.env
deploy/example_fastapi_app/production/uvicorn.service
deploy/example_fastapi_app/production/app-secret.txt
```

Do not commit real secrets.

## Setup

Preview the setup commands:

```bash
pystrano setup production example_fastapi_app --dry-run
```

Run setup when the target server, SSH access, and local referenced files are
ready:

```bash
pystrano setup production example_fastapi_app
```

Setup connects as `root`, creates the deploy user, prepares the directory
structure, installs packages, creates the virtualenv, updates SSH known hosts,
copies the systemd service file, and uploads configured secret files.

## Deploy

Preview the deployment commands:

```bash
pystrano deploy production example_fastapi_app --dry-run
```

Deploy the app:

```bash
pystrano deploy production example_fastapi_app
```

Deploy connects as the configured `project_user`, creates a timestamped release,
clones the configured repository, installs `requirements.txt`, links shared
files, optionally runs Alembic migrations, updates the `current` symlink,
restarts the configured systemd service, and prunes older releases according to
`keep_releases`.

## FastAPI Commands

When `run_migrations` is true, FastAPI deployments run:

```bash
/home/deploy/.venv/bin/alembic upgrade head
```

Set `migration_command` to match your app if migrations are not managed with
Alembic. If your FastAPI app has a static build step, set
`collect_static_files: true` and provide `static_files_command`.

## systemd Restart

When `service_file` is configured, setup copies that file to
`/etc/systemd/system/<service_file_name>` and enables it. Deploy restarts it with
the equivalent of:

```bash
systemctl restart uvicorn.service
```
