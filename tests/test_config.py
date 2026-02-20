from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

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


def test_normalizers_handle_none_and_defaults():
    cfg = PystranoConfig(
        ssh_known_hosts=None,
        secrets=None,
        system_packages=None,
        run_migrations=None,
        collect_static_files=None,
        port=None,
        clone_depth=None,
    )

    assert cfg.ssh_known_hosts == []
    assert cfg.secrets == []
    assert cfg.system_packages == []
    assert cfg.run_migrations is False
    assert cfg.collect_static_files is False
    assert cfg.port == 22
    assert cfg.clone_depth == 1


def test_rejects_invalid_list_like_field_types():
    with pytest.raises(TypeError):
        PystranoConfig(ssh_known_hosts=123)

    with pytest.raises(TypeError):
        PystranoConfig(system_packages=123)


def test_bool_parsing_accepts_numbers_and_rejects_invalid_strings():
    assert PystranoConfig(run_migrations=1).run_migrations is True
    assert PystranoConfig(collect_static_files=0).collect_static_files is False

    with pytest.raises(ValidationError):
        PystranoConfig(run_migrations="sometimes")


def test_clone_depth_parsing_cases():
    assert PystranoConfig(clone_depth="abc").clone_depth is None
    assert PystranoConfig(clone_depth=0).clone_depth is None
    assert PystranoConfig(clone_depth=2).clone_depth == 2
    assert PystranoConfig(clone_depth=2, revision="v1.0.0").clone_depth is None


def test_finalize_config_with_absolute_paths_and_optional_fields():
    cfg = PystranoConfig(project_user="deployer", project_root="/srv/app", venv_dir="/opt/venv")
    cfg.finalize_config()

    assert cfg.project_root == "/srv/app"
    assert cfg.releases_dir == "/srv/app/releases"
    assert cfg.current_dir == "/srv/app/current"
    assert cfg.shared_dir == "/srv/app/shared"
    assert cfg.venv_dir == "/opt/venv"
    assert cfg.python_path == "/opt/venv/bin/python"

    empty = PystranoConfig()
    empty.finalize_config()
    assert empty.releases_dir is None
    assert empty.current_dir is None
    assert empty.shared_dir is None
    assert empty.python_path is None
    assert empty.service_file_name is None


def test_load_env_file_without_env_file_returns_empty_dict():
    cfg = PystranoConfig()
    assert cfg._load_env_file() == {}
