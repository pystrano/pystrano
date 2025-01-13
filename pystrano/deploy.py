from fabric import Connection
from datetime import datetime
from click import argument, command, option
from os import path

from .config import load_config, PystranoConfig
from .core import (
    setup_release_dir,
    update_source_code,
    setup_symlinks,
    install_requirements,
    collect_static_files,
    migrate_database,
    update_symlink,
    restart_service,
    cleanup_old_releases,
    try_to_remove_release_dir,
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


def set_up(server_configurations: list[PystranoConfig]):
    try:
        for server_config in server_configurations:
            print(f"Setting up {server_config.host}")
            c = Connection(f"root@{server_config.host}", forward_agent=True, port=server_config.port)

            print("Creating project user")
            create_project_user(c, server_config)

            print("Copy SSH keys from root")
            copy_authorized_keys(c, server_config)

            print("Creating directory structure")
            create_directory_structure(c, server_config)

            print("Install necessary packages")
            setup_packages(c, server_config)

            print("Setting up venv")
            setup_venv(c, server_config)

            print("Setting up known hosts")
            setup_known_hosts(c, server_config)

            if hasattr(server_config, "service_file"):
                print("Setting up service that should be executed")
                setup_service(c, server_config)

            if hasattr(server_config, "secrets"):
                print("Copying secrets to shared directory")
                copy_secrets(c, server_config)
    except Exception as e:
        print(f"Error setting up: {e}")
        exit(1)


def deploy(server_configurations: list[PystranoConfig]):
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    try:
        for server_config in server_configurations:
            new_release_dir = f"{server_config.releases_dir}/{timestamp}"

            print(f"Deploying to {server_config.host}")
            c = Connection(f"{server_config.project_user}@{server_config.host}", forward_agent=True, port=server_config.port)

            print("Creating release directory")
            setup_release_dir(c, new_release_dir)

            print("Updating source code")
            update_source_code(c, new_release_dir, server_config)

            print("Copying environment file to shared directory")
            copy_env_file(c, new_release_dir, server_config)

            print("Setting up symlinks")
            setup_symlinks(c, new_release_dir, server_config)

            print("Installing requirements")
            install_requirements(c, new_release_dir, server_config)

            if hasattr(server_config, "secrets"):
                print("Linking secrets to the release directory")
                link_secrets_to_release(c, new_release_dir, server_config)

            if hasattr(server_config, "collect_static_files") and server_config.collect_static_files:
                print("Collecting static files")
                collect_static_files(c, new_release_dir, server_config)

            if hasattr(server_config, "run_migrations") and server_config.run_migrations:
                print("Migrating database")
                migrate_database(c, new_release_dir, server_config)

            print("Updating symlinks")
            update_symlink(c, new_release_dir, server_config)

            if hasattr(server_config, "service_file"):
                print("Restarting service")
                restart_service(c, server_config)

            print("Cleaning up old releases")
            cleanup_old_releases(c, server_config)
    except Exception as e:
        print(f"Error deploying: {e}")
        exit(1)

@command()
@argument("cmd", required=True)
@argument("environment_name", required=True)
@argument("app_name", required=True)
@option("--deploy-config-dir", required=False, help="Path to the deploy configuration directory. Default: ./deploy", default='./deploy')
@option("--config-file-name", required=False, help="Name of the configuration file. Default: deployment.yml", default='deployment.yml')
def main(cmd, environment_name, app_name, deploy_config_dir='./deploy', config_file_name='deployment.yml'):
    try:
        # Load server configs for the environment
        print(cmd, environment_name, app_name, deploy_config_dir, config_file_name)
        server_configurations = load_config(path.join(deploy_config_dir, app_name, environment_name, config_file_name))

        if cmd == "deploy":
            deploy(server_configurations)
        elif cmd == "setup":
            set_up(server_configurations)
        else:
            print(f"Invalid command: {cmd}")
            exit(1)
    except Exception as e:
        print(f"Error deploying servers: {e}")
        exit(1)
