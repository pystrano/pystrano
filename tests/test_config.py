from pathlib import Path

import yaml

from pystrano import config
from pystrano.config import PystranoConfig


def test_load_config_normalizes_fields(tmp_path):
    env_file = tmp_path / ".env.deployment"
    env_file.write_text("DJANGO_SETTINGS_MODULE=mysite.settings\n")

    service_file = tmp_path / "gunicorn.service"
    service_file.write_text("[Unit]")

    deployment = {
        "common": {
            "project_user": "deployer",
            "project_root": "apps/blog",
            "venv_dir": ".venv",
            "env_file": str(env_file),
            "source_code_url": "git@github.com:example/repo.git",
            "branch": "main",
            "keep_releases": 3,
            "ssh_known_hosts": "github.com;gitlab.com",
            "secrets": f"{tmp_path}/secret.json;{tmp_path}/.env",
            "service_file": str(service_file),
            "run_migrations": "true",
            "collect_static_files": "false",
            "system_packages": "libpq-dev\npython3-dev",
        },
        "servers": [
            {
                "host": "example.com",
                "project_user": "web",
                "project_root": "projects/web",
            }
        ],
    }

    config_path = tmp_path / "deployment.yml"
    config_path.write_text(yaml.safe_dump(deployment))

    server_configs = config.load_config(str(config_path))

    assert len(server_configs) == 1
    server = server_configs[0]

    assert server.project_root == "/home/web/projects/web"
    assert server.releases_dir == "/home/web/projects/web/releases"
    assert server.current_dir == "/home/web/projects/web/current"
    assert server.shared_dir == "/home/web/projects/web/shared"
    assert server.venv_dir == "/home/web/.venv"
    assert server.python_path.endswith("bin/python")
    assert server.run_migrations is True
    assert server.collect_static_files is False
    assert server.port == 22
    assert server.env_vars == {"DJANGO_SETTINGS_MODULE": "mysite.settings"}
    assert server.ssh_known_hosts == ["github.com", "gitlab.com"]
    assert server.secrets[0].endswith("secret.json")
    assert server.service_file_name == Path(service_file).name
    assert server.clone_depth == 1
    assert server.system_packages == ["libpq-dev", "python3-dev"]


def test_finalize_config_defaults():
    cfg = PystranoConfig()
    cfg.update_dict(
        {
            "project_user": "deployer",
            "project_root": "apps/blog",
            "venv_dir": ".venv",
            "port": "2200",
        }
    )

    cfg.finalize_config()
    cfg.finalize_config()  # ensure idempotence

    assert cfg.project_root == "/home/deployer/apps/blog"
    assert cfg.releases_dir == "/home/deployer/apps/blog/releases"
    assert cfg.current_dir == "/home/deployer/apps/blog/current"
    assert cfg.shared_dir == "/home/deployer/apps/blog/shared"
    assert cfg.venv_dir == "/home/deployer/.venv"
    assert cfg.python_path == "/home/deployer/.venv/bin/python"
    assert cfg.port == 2200
    assert cfg.run_migrations is False
    assert cfg.collect_static_files is False
    assert cfg.clone_depth == 1


def test_revision_disables_shallow_clone():
    cfg = PystranoConfig()
    cfg.update_dict(
        {
            "project_user": "deployer",
            "project_root": "apps/blog",
            "venv_dir": ".venv",
            "revision": "abc123",
        }
    )

    cfg.finalize_config()

    assert cfg.clone_depth is None


def test_update_dict_splits_lists():
    cfg = PystranoConfig()
    cfg.update_dict(
        {
            "ssh_known_hosts": "github.com;gitlab.com",
            "secrets": "secret.json;path/.env",
        }
    )

    assert cfg.ssh_known_hosts == ["github.com", "gitlab.com"]
    assert cfg.secrets == ["secret.json", "path/.env"]


def test_finalize_config_accepts_yaml_booleans():
    cfg = PystranoConfig()
    cfg.update_dict(
        {
            "project_user": "deployer",
            "project_root": "apps/blog",
            "venv_dir": ".venv",
            "run_migrations": True,
            "collect_static_files": False,
        }
    )

    cfg.finalize_config()

    assert cfg.run_migrations is True
    assert cfg.collect_static_files is False
