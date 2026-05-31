from pathlib import Path

import yaml
from click.testing import CliRunner

from pystrano import deploy


def test_build_deployment_config_creates_fastapi_config(tmp_path):
    runner = CliRunner()
    service_file = tmp_path / "api" / "production" / "uvicorn.service"
    inputs = "\n".join(
        [
            "fastapi",
            "deployer",
            ".venv",
            "uv",
            "",
            "project.main:app",
            "9001",
            "git@github.com:example/api.git",
            "apps/api",
            "7",
            "n",
            "libpq-dev,python3-dev",
            "./deploy/api/production/.env",
            "github.com;gitlab.com",
            str(service_file),
            "main",
            "1",
            "",
            "y",
            "n",
            "/home/deployer/.venv/bin/alembic upgrade head",
            "app.example.com",
            "2222",
        ]
    )

    result = runner.invoke(
        deploy.main,
        ["init", "production", "api", "--deploy-config-dir", str(tmp_path)],
        input=f"{inputs}\n",
    )

    assert result.exit_code == 0

    config_path = tmp_path / "api" / "production" / "deployment.yml"
    data = yaml.safe_load(config_path.read_text())

    assert data["common"] == {
        "source_code_url": "git@github.com:example/api.git",
        "framework": "fastapi",
        "project_root": "apps/api",
        "project_user": "deployer",
        "venv_dir": ".venv",
        "package_manager": "uv",
        "dependency_file": "uv.lock",
        "keep_releases": 7,
        "system_packages": "libpq-dev\npython3-dev",
        "env_file": "./deploy/api/production/.env",
        "ssh_known_hosts": "github.com;gitlab.com",
        "service_file": str(service_file),
        "branch": "main",
        "clone_depth": 1,
        "migration_command": "/home/deployer/.venv/bin/alembic upgrade head",
    }
    assert data["servers"] == [
        {
            "host": "app.example.com",
            "port": 2222,
            "run_migrations": True,
            "collect_static_files": False,
        }
    ]
    service = service_file.read_text()
    assert "WorkingDirectory=/home/deployer/apps/api/current" in service
    assert "EnvironmentFile=/home/deployer/apps/api/shared/.env" in service
    assert (
        "ExecStart=/home/deployer/.venv/bin/uvicorn "
        "project.main:app --host 127.0.0.1 --port 9001"
    ) in service


def test_build_deployment_config_creates_django_config_with_defaults(tmp_path):
    runner = CliRunner()
    inputs = "\n".join(
        [
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "git@github.com:example/web.git",
            "",
            "",
            "n",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "y",
            "y",
            "web.example.com",
            "",
        ]
    )

    result = runner.invoke(
        deploy.main,
        ["init", "staging", "web", "--deploy-config-dir", str(tmp_path)],
        input=f"{inputs}\n",
    )

    assert result.exit_code == 0

    config_path = tmp_path / "web" / "staging" / "deployment.yml"
    data = yaml.safe_load(config_path.read_text())

    assert data["common"]["framework"] == "django"
    assert data["common"]["project_user"] == "deploy"
    assert data["common"]["project_root"] == "apps/web"
    assert data["common"]["package_manager"] == "pip"
    assert data["common"]["dependency_file"] == "requirements.txt"
    assert data["common"]["service_file"] == str(tmp_path / "web" / "staging" / "gunicorn.service")
    assert data["servers"][0] == {
        "host": "web.example.com",
        "port": 22,
        "run_migrations": True,
        "collect_static_files": True,
    }
    service = (tmp_path / "web" / "staging" / "gunicorn.service").read_text()
    assert "WorkingDirectory=/home/deploy/apps/web/current" in service
    assert (
        "ExecStart=/home/deploy/.venv/bin/gunicorn "
        "web.wsgi:application --bind 127.0.0.1:8000"
    ) in service


def test_build_deployment_config_refuses_overwrite(tmp_path):
    config_path = tmp_path / "api" / "production" / "deployment.yml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("existing: true\n")

    runner = CliRunner()
    result = runner.invoke(
        deploy.main,
        ["init", "production", "api", "--deploy-config-dir", str(tmp_path)],
        input="n\n",
    )

    assert result.exit_code == 0
    assert Path(config_path).read_text() == "existing: true\n"
    assert "Aborted." in result.output
