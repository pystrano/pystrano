from types import SimpleNamespace
from unittest.mock import call

import pytest

from pystrano import workflows


def test_django_workflow_runs_django_steps(mocker):
    connection = mocker.Mock()
    conf = SimpleNamespace(run_migrations=True, collect_static_files=True)
    collect_static_files = mocker.patch("pystrano.workflows.collect_static_files")
    migrate_database = mocker.patch("pystrano.workflows.migrate_database")

    messages = workflows.DjangoDeploymentWorkflow().run_release_steps(
        connection,
        "/srv/app/releases/20240101",
        conf,
    )

    collect_static_files.assert_called_once_with(
        connection,
        "/srv/app/releases/20240101",
        conf,
    )
    migrate_database.assert_called_once_with(connection, "/srv/app/releases/20240101", conf)
    assert messages == ["Applied migrations and refreshed static assets"]


def test_fastapi_workflow_runs_default_alembic_migration(mocker):
    connection = mocker.Mock()
    conf = SimpleNamespace(
        framework="fastapi",
        run_migrations=True,
        collect_static_files=False,
        venv_dir="/home/app/.venv",
    )
    run_release_command = mocker.patch("pystrano.workflows.run_release_command")

    messages = workflows.FastAPIDeploymentWorkflow().run_release_steps(
        connection,
        "/srv/app/releases/20240101",
        conf,
    )

    run_release_command.assert_called_once_with(
        connection,
        "/srv/app/releases/20240101",
        conf,
        "/home/app/.venv/bin/alembic upgrade head",
    )
    assert messages == ["Applied database migrations"]


def test_fastapi_workflow_uses_configured_commands(mocker):
    connection = mocker.Mock()
    conf = SimpleNamespace(
        run_migrations=True,
        collect_static_files=True,
        migration_command="/home/app/.venv/bin/python -m alembic upgrade head",
        static_files_command="/home/app/.venv/bin/python scripts/build_static.py",
    )
    run_release_command = mocker.patch("pystrano.workflows.run_release_command")

    messages = workflows.FastAPIDeploymentWorkflow().run_release_steps(
        connection,
        "/srv/app/releases/20240101",
        conf,
    )

    run_release_command.assert_has_calls(
        [
            call(
                connection,
                "/srv/app/releases/20240101",
                conf,
                "/home/app/.venv/bin/python scripts/build_static.py",
            ),
            call(
                connection,
                "/srv/app/releases/20240101",
                conf,
                "/home/app/.venv/bin/python -m alembic upgrade head",
            ),
        ]
    )
    assert messages == ["Refreshed static assets", "Applied database migrations"]


def test_fastapi_static_requires_command(mocker):
    conf = SimpleNamespace(run_migrations=False, collect_static_files=True)

    with pytest.raises(ValueError, match="static_files_command"):
        workflows.FastAPIDeploymentWorkflow().run_release_steps(
            mocker.Mock(),
            "/srv/app/releases/20240101",
            conf,
        )


def test_get_workflow_rejects_unknown_framework():
    with pytest.raises(ValueError, match="Unsupported framework"):
        workflows.get_workflow("flask")
