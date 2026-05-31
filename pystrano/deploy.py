import logging
from time import perf_counter
from types import SimpleNamespace
from fabric import Connection, Config
from datetime import datetime
from click import argument, command, option
from os import path

from .config import CURRENT_CONFIG_VERSION, load_config, PystranoConfig
from .config_builder import build_deployment_config
from .core import (
    setup_release_dir,
    update_source_code,
    setup_symlinks,
    install_requirements,
    update_symlink,
    restart_service,
    cleanup_old_releases,
    create_project_user,
    copy_authorized_keys,
    create_directory_structure,
    setup_packages,
    setup_venv,
    setup_known_hosts,
    setup_service,
    copy_env_file,
    copy_secrets,
    link_secrets_to_release,
)
from .workflows import get_workflow


class DryRunConnection:
    """A minimal Connection-like object that logs commands without executing them."""

    def __init__(self, label: str):
        self.label = label

    def run(self, command, hide=False, warn=False, env=None):
        msg = f"RUN [{self.label}]: {command}"
        if env:
            msg += " (with env vars)"
        logging.info(msg)
        return SimpleNamespace(stdout="", failed=False)

    def sudo(self, command, hide=False, warn=False, env=None):
        msg = f"SUDO [{self.label}]: {command}"
        if env:
            msg += " (with env vars)"
        logging.info(msg)
        return SimpleNamespace(stdout="", failed=False)

    def put(self, local, remote):
        logging.info("PUT [%s]: %s -> %s", self.label, local, remote)
        return SimpleNamespace()

    class _CD:
        def __init__(self, label, directory):
            self.label = label
            self.directory = directory

        def __enter__(self):
            logging.info("CD [%s]: -> %s", self.label, self.directory)
            return self

        def __exit__(self, exc_type, exc, tb):
            logging.info("CD [%s]: <- %s", self.label, self.directory)

    def cd(self, directory):
        return DryRunConnection._CD(self.label, directory)


def _make_connection(
    user: str,
    host: str,
    port: int,
    dry_run: bool,
    hide_output: bool,
):
    label = f"{user}@{host}:{port}"
    if dry_run:
        return DryRunConnection(label)

    kwargs = {"forward_agent": True, "port": port}
    if hide_output:
        kwargs["config"] = Config(
            overrides={
                "run": {"hide": True},
                "sudo": {"hide": True},
            }
        )

    return Connection(f"{user}@{host}", **kwargs)


def _configure_library_loggers(verbose: bool):
    """Tone down third-party loggers unless verbose output is requested."""

    level = logging.DEBUG if verbose else logging.WARNING
    for name in ("paramiko", "invoke", "fabric"):  # keep console calm by default
        logging.getLogger(name).setLevel(level)


def _step(message: str):
    """Render a successful step message with the default checkmark prefix."""

    logging.info("✓ %s", message)


def _success(message: str):
    """Render a completion message with a heavier checkmark icon."""

    logging.info("✅ %s", message)


def _target_label(server_config: PystranoConfig, context_label: str | None) -> str:
    """Produce the display label shown in CLI output for a server."""

    if context_label:
        return f"{context_label} ({server_config.host})"
    return server_config.host


def _config_version(config: PystranoConfig) -> int | None:
    version = getattr(config, "config_version", None)
    if version in (None, ""):
        return None
    try:
        return int(version)
    except (TypeError, ValueError):
        return None


def _warn_about_config_version(server_configurations: list[PystranoConfig]):
    needs_warning = any(
        (_config_version(server_config) or 0) < CURRENT_CONFIG_VERSION
        for server_config in server_configurations
    )
    if not needs_warning:
        return

    logging.warning(
        "Pystrano 2.x compatibility warning: this deployment config does not declare "
        "config_version: 2. Review the v2 config fields before running against older setups."
    )


def set_up(
    server_configurations: list[PystranoConfig],
    *,
    dry_run: bool = False,
    context_label: str | None = None,
    hide_remote_output: bool = True,
):
    try:
        started_at = perf_counter()
        _warn_about_config_version(server_configurations)

        for server_config in server_configurations:
            label = _target_label(server_config, context_label)
            c = _make_connection(
                "root",
                server_config.host,
                server_config.port,
                dry_run,
                hide_remote_output,
            )
            _step(f"Connecting to {label}")

            create_project_user(c, server_config)
            _step(f"Ensured deploy user {server_config.project_user} exists")

            copy_authorized_keys(c, server_config)
            _step("Copied SSH authorized_keys")

            create_directory_structure(c, server_config)
            _step("Prepared remote directory structure")

            setup_packages(c, server_config)
            _step("Installed system packages")

            setup_venv(c, server_config)
            _step(f"Provisioned virtualenv at {server_config.venv_dir}")

            setup_known_hosts(c, server_config)
            _step("Updated known hosts")

            if getattr(server_config, "service_file", None):
                setup_service(c, server_config)
                _step(f"Registered {server_config.service_file_name}")

            if getattr(server_config, "secrets", None):
                copy_secrets(c, server_config)
                _step("Uploaded secrets to shared directory")

        elapsed = perf_counter() - started_at
        _success(f"Setup completed in {int(elapsed)}s")
    except Exception:
        logging.exception("Error setting up")
        exit(1)


def deploy(
    server_configurations: list[PystranoConfig],
    *,
    dry_run: bool = False,
    context_label: str | None = None,
    hide_remote_output: bool = True,
):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    try:
        started_at = perf_counter()
        _warn_about_config_version(server_configurations)

        for server_config in server_configurations:
            new_release_dir = f"{server_config.releases_dir}/{timestamp}"
            label = _target_label(server_config, context_label)

            connection = _make_connection(
                server_config.project_user,
                server_config.host,
                server_config.port,
                dry_run,
                hide_remote_output,
            )
            _step(f"Connecting to {label}")

            setup_release_dir(connection, new_release_dir)
            _step("Prepared release directory")

            update_source_code(connection, new_release_dir, server_config)
            branch = getattr(server_config, "branch", "HEAD")
            _step(f"Pulled branch {branch}")

            copy_env_file(connection, new_release_dir, server_config)
            setup_symlinks(connection, new_release_dir, server_config)
            _step("Synced shared assets and env file")

            install_requirements(connection, new_release_dir, server_config)
            _step("Installed Python dependencies")

            if getattr(server_config, "secrets", None):
                link_secrets_to_release(connection, new_release_dir, server_config)
                _step("Linked secrets into release")

            workflow = get_workflow(getattr(server_config, "framework", "django"))
            for message in workflow.run_release_steps(connection, new_release_dir, server_config):
                _step(message)

            update_symlink(connection, new_release_dir, server_config)
            _step("Promoted release to current")

            if getattr(server_config, "service_file", None):
                restart_service(connection, server_config)
                _step(f"Restarted {server_config.service_file_name}")

            cleanup_old_releases(connection, server_config)
            _step("Pruned old releases")

        elapsed = perf_counter() - started_at
        _success(f"Deployment completed in {int(elapsed)}s")
    except Exception:
        logging.exception("Error deploying")
        exit(1)


@command()
@argument("cmd", required=True)
@argument("environment_name", required=True)
@argument("app_name", required=True)
@option(
    "--deploy-config-dir",
    required=False,
    default="./deploy",
    help="Path to the deploy configuration directory. Default: ./deploy",
)
@option(
    "--config-file-name",
    required=False,
    default="deployment.yml",
    help="Name of the configuration file. Default: deployment.yml",
)
@option("--verbose", is_flag=True, help="Enable verbose logging", default=False)
@option("--dry-run", is_flag=True, help="Print commands without executing them", default=False)
def main(
    cmd,
    environment_name,
    app_name,
    deploy_config_dir="./deploy",
    config_file_name="deployment.yml",
    verbose=False,
    dry_run=False,
):
    try:
        # Configure logging
        logging.basicConfig(
            level=logging.DEBUG if verbose else logging.INFO,
            format="%(message)s",
        )
        _configure_library_loggers(verbose)

        context_label = f"{environment_name} {app_name}"
        hide_remote_output = not verbose

        if cmd in {"init", "configure"}:
            build_deployment_config(
                environment_name,
                app_name,
                deploy_config_dir=deploy_config_dir,
                config_file_name=config_file_name,
            )
        elif cmd in {"deploy", "setup"}:
            config_path = path.join(deploy_config_dir, app_name, environment_name, config_file_name)
            server_configurations = load_config(config_path)

            if cmd == "deploy":
                deploy(
                    server_configurations,
                    dry_run=dry_run,
                    context_label=context_label,
                    hide_remote_output=hide_remote_output,
                )
            else:
                set_up(
                    server_configurations,
                    dry_run=dry_run,
                    context_label=context_label,
                    hide_remote_output=hide_remote_output,
                )
        else:
            logging.error("Invalid command: %s", cmd)
            exit(1)
    except Exception:
        logging.exception("Error deploying servers")
        exit(1)
