from fabric import Connection
from datetime import datetime
from click import command, option

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
    copy_env_file
)


def set_up(server_configurations: list[PystranoConfig]):
    for server_config in server_configurations:
        try:
            print(f"Setting up {server_config.host}")
            c = Connection(f"root@{server_config.host}")

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
        except Exception as e:
            print(f"Error setting up {server_config.host}: {e}")
            continue


def deploy(server_configurations: list[PystranoConfig]):
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    for server_config in server_configurations:
        new_release_dir = f"{server_config.releases_dir}/{timestamp}"

        try:
            print(f"Deploying to {server_config.host}")
            c = Connection(f"{server_config.project_user}@{server_config.host}")

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
            print(f"Error deploying to {server_config.host}: {e}")
            try_to_remove_release_dir(c, new_release_dir)
            continue


@command()
@option('--config-file', required=True, help='Path to the configuration file')
def main(config_file):
    try:
        server_configurations = load_config(config_file)
        deploy(server_configurations)
    except Exception as e:
        print(f"Error deploying servers: {e}")
        exit(1)


@command()
@option('--config-file', required=True, help='Path to the configuration file')
def setup(config_file):
    try:
        server_configurations = load_config(config_file)
        set_up(server_configurations)
    except Exception as e:
        print(f"Error setting up servers: {e}")
        exit(1)
