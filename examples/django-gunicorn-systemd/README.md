# Django, Gunicorn, and systemd Example

This example is intended as a starting point, not a complete production
infrastructure template.

It shows a Pystrano config for deploying a Django app to a VPS-style Linux
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
deploy/example_django_app/production/deployment.yml
```

The example config references local files such as:

```text
deploy/example_django_app/production/.env
deploy/example_django_app/production/gunicorn.service
deploy/example_django_app/production/django-secret-key.txt
```

Do not commit real secrets.

## Setup

Preview the setup commands:

```bash
pystrano setup production example_django_app --dry-run
```

Run setup when the target server, SSH access, and local referenced files are
ready:

```bash
pystrano setup production example_django_app
```

Setup connects as `root`, creates the deploy user, prepares the directory
structure, installs packages, creates the virtualenv, updates SSH known hosts,
copies the systemd service file, and uploads configured secret files.

## Deploy

Preview the deployment commands:

```bash
pystrano deploy production example_django_app --dry-run
```

Deploy the app:

```bash
pystrano deploy production example_django_app
```

Deploy connects as the configured `project_user`, creates a timestamped release,
clones the configured repository, installs `requirements.txt`, links shared
files, optionally runs Django migrations and static collection, updates the
`current` symlink, restarts the configured systemd service, and prunes older
releases according to `keep_releases`.

## systemd Restart

When `service_file` is configured, setup copies that file to
`/etc/systemd/system/<service_file_name>` and enables it. Deploy restarts it with
the equivalent of:

```bash
systemctl restart gunicorn.service
```

## Rollback Note

Pystrano does not currently include a rollback CLI command. It keeps timestamped
release directories and updates a `current` symlink during deploy, so keep enough
releases for your recovery window and test any manual rollback procedure on your
own infrastructure.
