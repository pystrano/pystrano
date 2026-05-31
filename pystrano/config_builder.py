from os import makedirs, path

import click
from yaml import safe_dump


def _config_path(
    deploy_config_dir: str,
    app_name: str,
    environment_name: str,
    config_file_name: str,
) -> str:
    return path.join(deploy_config_dir, app_name, environment_name, config_file_name)


def _split_packages(value: str) -> str:
    packages = [package.strip() for package in value.replace(",", ";").split(";")]
    return "\n".join(package for package in packages if package)


def _venv_bin_path(project_user: str, venv_dir: str, executable: str) -> str:
    if path.isabs(venv_dir):
        return path.join(venv_dir, "bin", executable)
    return path.join("/home", project_user, venv_dir, "bin", executable)


def _remote_project_root(project_user: str, project_root: str) -> str:
    if path.isabs(project_root):
        return project_root
    return path.join("/home", project_user, project_root)


def _local_deploy_file(
    deploy_config_dir: str,
    app_name: str,
    environment_name: str,
    file_name: str,
) -> str:
    return path.join(deploy_config_dir, app_name, environment_name, file_name)


def _service_file_content(
    *,
    app_name: str,
    framework: str,
    project_user: str,
    project_root: str,
    venv_dir: str,
    app_module: str,
    service_port: int,
) -> str:
    remote_root = _remote_project_root(project_user, project_root)
    current_dir = path.join(remote_root, "current")
    env_file = path.join(remote_root, "shared", ".env")

    if framework == "fastapi":
        executable = _venv_bin_path(project_user, venv_dir, "uvicorn")
        exec_start = f"{executable} {app_module} --host 127.0.0.1 --port {service_port}"
    else:
        executable = _venv_bin_path(project_user, venv_dir, "gunicorn")
        exec_start = f"{executable} {app_module} --bind 127.0.0.1:{service_port}"

    return "\n".join(
        [
            "[Unit]",
            f"Description={app_name} application service",
            "After=network.target",
            "",
            "[Service]",
            f"User={project_user}",
            f"Group={project_user}",
            f"WorkingDirectory={current_dir}",
            f"EnvironmentFile={env_file}",
            f"ExecStart={exec_start}",
            "Restart=always",
            "RestartSec=5",
            "",
            "[Install]",
            "WantedBy=multi-user.target",
            "",
        ]
    )


def _write_service_file(service_file: str, content: str) -> bool:
    if path.exists(service_file) and not click.confirm(f"Overwrite {service_file}?", default=False):
        click.echo(f"Skipped {service_file}")
        return False

    makedirs(path.dirname(service_file) or ".", exist_ok=True)
    with open(service_file, "w", encoding="utf-8") as target:
        target.write(content)

    click.echo(f"Created {service_file}")
    return True


def build_deployment_config(
    environment_name: str,
    app_name: str,
    *,
    deploy_config_dir: str = "./deploy",
    config_file_name: str = "deployment.yml",
) -> str:
    target = _config_path(deploy_config_dir, app_name, environment_name, config_file_name)

    if path.exists(target) and not click.confirm(f"Overwrite {target}?", default=False):
        click.echo("Aborted.")
        return target

    framework = click.prompt(
        "Framework",
        default="django",
        type=click.Choice(["django", "fastapi"], case_sensitive=False),
    ).lower()
    project_user = click.prompt("Project user", default="deploy")
    venv_dir = click.prompt("Virtualenv directory", default=".venv")
    package_manager = click.prompt(
        "Package manager",
        default="pip",
        type=click.Choice(["pip", "uv"], case_sensitive=False),
    ).lower()
    dependency_file = click.prompt(
        "Dependency file",
        default="uv.lock" if package_manager == "uv" else "requirements.txt",
    )
    default_module = "main:app" if framework == "fastapi" else f"{app_name}.wsgi:application"
    app_module = click.prompt("Application import path", default=default_module)
    service_port = click.prompt("Service port", default=8000, type=int)
    service_file_name = "uvicorn.service" if framework == "fastapi" else "gunicorn.service"

    common = {
        "source_code_url": click.prompt("Git repository URL"),
        "framework": framework,
        "project_root": click.prompt("Remote project root", default=f"apps/{app_name}"),
        "project_user": project_user,
        "venv_dir": venv_dir,
        "package_manager": package_manager,
        "dependency_file": dependency_file,
        "keep_releases": click.prompt("Releases to keep", default=5, type=int),
    }

    if click.confirm("Use custom dependency install command?", default=False):
        common["dependency_install_command"] = click.prompt("Dependency install command")

    system_packages = click.prompt(
        "System packages (; or , separated)",
        default="libpq-dev;python3-dev;build-essential",
    )
    if system_packages:
        common["system_packages"] = _split_packages(system_packages)

    common.update(
        {
            "env_file": click.prompt(
                "Local dotenv file",
                default=_local_deploy_file(deploy_config_dir, app_name, environment_name, ".env"),
            ),
            "ssh_known_hosts": click.prompt("SSH known hosts (; separated)", default="github.com"),
            "service_file": click.prompt(
                "Local systemd service file",
                default=_local_deploy_file(
                    deploy_config_dir,
                    app_name,
                    environment_name,
                    service_file_name,
                ),
            ),
            "branch": click.prompt("Git branch", default="main"),
            "clone_depth": click.prompt("Git clone depth", default=1, type=int),
        }
    )

    secrets = click.prompt("Secret files (; separated, optional)", default="", show_default=False)
    if secrets:
        common["secrets"] = secrets

    run_migrations = click.confirm("Run migrations during deploy?", default=True)
    collect_static_files = click.confirm(
        "Collect/build static files during deploy?",
        default=framework == "django",
    )

    if framework == "fastapi" and run_migrations:
        common["migration_command"] = click.prompt(
            "FastAPI migration command",
            default=f"{_venv_bin_path(project_user, venv_dir, 'alembic')} upgrade head",
        )

    if framework == "fastapi" and collect_static_files:
        common["static_files_command"] = click.prompt("FastAPI static files command")

    config = {
        "common": common,
        "servers": [
            {
                "host": click.prompt("Server host"),
                "port": click.prompt("SSH port", default=22, type=int),
                "run_migrations": run_migrations,
                "collect_static_files": collect_static_files,
            }
        ],
    }

    makedirs(path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as config_file:
        safe_dump(config, config_file, sort_keys=False)

    click.echo(f"Created {target}")
    _write_service_file(
        common["service_file"],
        _service_file_content(
            app_name=app_name,
            framework=framework,
            project_user=project_user,
            project_root=common["project_root"],
            venv_dir=venv_dir,
            app_module=app_module,
            service_port=service_port,
        ),
    )
    return target
