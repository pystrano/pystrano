from fabric import Connection
from datetime import datetime
from yaml import safe_load
from os import path
from dotenv import dotenv_values

import click


def configure_deployment(project_dir=None, repo_url=None, venv_dir=None, keep_releases=None, servers=None, project_user=None, system_packages=None, env_file=None, ssh_known_hosts=None, gunicorn_service_file=None):
    """Configures deployment paths and settings."""
    global REPO_URL, VENV_DIR, KEEP_RELEASES, PROJECT_USER
    if project_user:
        PROJECT_USER = project_user
    if repo_url:
        REPO_URL = repo_url
    if venv_dir:
        VENV_DIR = f"/home/{PROJECT_USER}/{venv_dir}"
    if keep_releases:
        KEEP_RELEASES = keep_releases
    global PROJECT_DIR, RELEASES_DIR, CURRENT_DIR, SHARED_DIR, PYTHON_PATH, SERVERS, SYSTEM_PACKAGES, KNOWN_HOSTS, ENV_FILE, GUNICORN_SERVICE_FILE
    PROJECT_DIR = f"/home/{PROJECT_USER}/{project_dir}"
    RELEASES_DIR = f'{PROJECT_DIR}/releases'
    CURRENT_DIR = f'{PROJECT_DIR}/current'
    SHARED_DIR = f'{PROJECT_DIR}/shared'
    PYTHON_PATH = f'{VENV_DIR}/bin/python'
    SERVERS = servers
    SYSTEM_PACKAGES = system_packages
    KNOWN_HOSTS = ssh_known_hosts.split(';') if ssh_known_hosts else []
    ENV_FILE = env_file
    GUNICORN_SERVICE_FILE = gunicorn_service_file


def set_up():
    for server in parse_servers(SERVERS):
        try:
            print(f"Setting up {server}")
            c = Connection(f"root@{server}")

            print("Creating project user")
            create_project_user(c)

            print("Copy SSH keys from root")
            copy_authorized_keys(c)

            print("Creating directory structure")
            create_directory_structure(c)

            print("Install necessary packages")
            setup_packages(c)

            print("Setting up venv")
            setup_venv(c)

            print("Setting up known hosts")
            setup_known_hosts(c)

            print("Setting up Gunicorn service")
            setup_gunicorn_service(c)
        except Exception as e:
            print(f"Error setting up {server}: {e}")
            continue


def deploy():
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    new_release_dir = f"{RELEASES_DIR}/{timestamp}"
    load_environment()

    for server in parse_servers(SERVERS):
        try:
            print(f"Deploying to {server}")
            c = Connection(f"{PROJECT_USER}@{server}")

            print("Creating release directory")
            setup_release_dir(c, new_release_dir)

            print("Updating source code")
            update_source_code(c, new_release_dir)

            print("Copying environment file to shared directory")
            copy_env_file(c, new_release_dir)

            print("Setting up symlinks")
            setup_symlinks(c, new_release_dir)

            print("Installing requirements")
            install_requirements(c, new_release_dir)

            print("Collecting static files")
            collect_static_files(c, new_release_dir)

            print("Migrating database")
            migrate_database(c, new_release_dir)

            print("Updating symlinks")
            update_symlink(c, new_release_dir)

            print("Restarting Gunicorn")
            restart_gunicorn(c)

            print("Cleaning up old releases")
            cleanup_old_releases(c)
        except Exception as e:
            print(f"Error deploying to {server}: {e}")
            try_to_remove_release_dir(c, new_release_dir)
            continue


def parse_servers(servers):
    try:
        server_list = servers.split(';')
        return server_list
    except Exception as e:
        print(f"Error parsing servers: {e}")
        return []


def setup_release_dir(c, new_release_dir):
    c.run(f'mkdir -p {new_release_dir}')


def update_source_code(c, new_release_dir):
    # Clone or pull latest code into the new release directory
    c.run(f'git clone {REPO_URL} {new_release_dir}')
    with c.cd(new_release_dir):
        c.run('git pull')


def setup_symlinks(c, new_release_dir):
    # Link shared files and directories (e.g., static and media)
    c.run(f'ln -sfn {SHARED_DIR}/media {new_release_dir}/media')
    c.run(f'ln -sfn {SHARED_DIR}/.env.{new_release_dir.split("/")[-1]} {SHARED_DIR}/.env')


def install_requirements(c, new_release_dir):
    # Install dependencies in the virtual environment
    with c.cd(new_release_dir):
        c.run(f'{VENV_DIR}/bin/pip install -r requirements.txt')


def collect_static_files(c, new_release_dir):
    # Collect static files to the shared directory
    with c.cd(new_release_dir):
        c.run(f'{PYTHON_PATH} manage.py collectstatic --noinput', env=ENV_VARS)


def migrate_database(c, new_release_dir):
    # Apply migrations
    with c.cd(new_release_dir):
        c.run(f'{PYTHON_PATH} manage.py migrate', env=ENV_VARS)


def update_symlink(c, new_release_dir):
    # Update the `current` symlink to point to the new release
    c.run(f'ln -sfn {new_release_dir} {CURRENT_DIR}')


def restart_gunicorn(c):
    # Restart Gunicorn service
    c.sudo('systemctl restart gunicorn.service')


def cleanup_old_releases(c):
    # Remove old releases, keeping only the last `KEEP_RELEASES`
    releases = c.run(f'ls -1 {RELEASES_DIR}', hide=True).stdout.split()
    if len(releases) > KEEP_RELEASES:
        old_releases = releases[:-KEEP_RELEASES]
        for release in old_releases:
            c.run(f'rm -rf {RELEASES_DIR}/{release}')


def create_project_user(c):
    # Check if user exists
    result = c.run(f'id -u {PROJECT_USER}', warn=True)

    if result.failed:
        # Create user if it doesn't exist
        c.run(f'useradd -m -s /bin/bash {PROJECT_USER}')
        # Allow sudo without password
        c.run(f'echo "{PROJECT_USER} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/{PROJECT_USER}')


def create_directory_structure(c):
    c.run(f'mkdir -p {PROJECT_DIR}')
    c.run(f'mkdir -p {RELEASES_DIR}')
    c.run(f'mkdir -p {SHARED_DIR}')
    c.run(f'mkdir -p {SHARED_DIR}/media')
    c.run(f'chown -R {PROJECT_USER}:{PROJECT_USER} {PROJECT_DIR}')


def setup_packages(c):
    c.run('apt update')
    c.run('apt install -y python3 python3-venv python3-pip git')

    if SYSTEM_PACKAGES:
        c.run(f'apt install -y {SYSTEM_PACKAGES}')

def setup_venv(c):
    c.run(f'python3 -m venv {VENV_DIR}')
    c.run(f'chown -R {PROJECT_USER}:{PROJECT_USER} {VENV_DIR}')


def copy_authorized_keys(c):
    c.run(f'mkdir -p /home/{PROJECT_USER}/.ssh')
    c.run(f'cp ~/.ssh/authorized_keys /home/{PROJECT_USER}/.ssh/')
    c.run(f'chown -R {PROJECT_USER}:{PROJECT_USER} /home/{PROJECT_USER}/.ssh')


def setup_known_hosts(c):
    c.run(f'ssh-keyscan github.com >> /home/{PROJECT_USER}/.ssh/known_hosts')

    for host in KNOWN_HOSTS:
        c.run(f'ssh-keyscan {host} >> /home/{PROJECT_USER}/.ssh/known_hosts')

    c.run(f'chown {PROJECT_USER}:{PROJECT_USER} /home/{PROJECT_USER}/.ssh/known_hosts')


def try_to_remove_release_dir(c, release_dir):
    try:
        c.run(f'rm -rf {release_dir}')
    except Exception as e:
        print(f"Error removing release directory: {e}")


def setup_gunicorn_service(c):
    c.put(GUNICORN_SERVICE_FILE, '/etc/systemd/system/gunicorn.service')
    c.sudo('systemctl daemon-reload')
    c.sudo('systemctl enable gunicorn.service')


def copy_env_file(c, new_release_dir):
    c.put(ENV_FILE, f'{SHARED_DIR}/.env.{new_release_dir.split("/")[-1]}')


def load_config(config_file):
    """Loads deployment settings from a YAML config file."""
    with open(config_file, 'r') as f:
        return safe_load(f)


def load_environment():
    """Loads environment variables from the .env file in the shared directory."""
    dotenv_path = ENV_FILE
    if path.exists(dotenv_path):
        global ENV_VARS
        ENV_VARS = dotenv_values(dotenv_path)  # Load .env as a dictionary
        print("Environment variables loaded from .env file.")
    else:
        print("Warning: .env file not found in shared directory.")


@click.command()
@click.option('--config-file', help='Path to the configuration file')
@click.option('--servers', help='Semicolon-separated list of hostnames')
@click.option('--project-dir', help='Path to the project directory')
@click.option('--repo-url', help='Repository URL')
@click.option('--venv-dir', help='Virtual environment directory')
@click.option('--keep-releases', help='Number of releases to keep')
@click.option('--project-user', help='Path to the project directory')
def main(config_file, servers, project_dir, repo_url, venv_dir, keep_releases, project_user):
    config = {}

    if config_file:
        config = load_config(config_file)

    config['servers'] = servers or config.get('servers')
    config['project_dir'] = project_dir or config.get('project_dir')
    config['repo_url'] = repo_url or config.get('repo_url')
    config['venv_dir'] = venv_dir or config.get('venv_dir')
    config['keep_releases'] = keep_releases or config.get('keep_releases')
    config['project_user'] = project_user or config.get('project_user')

    configure_deployment(**config)
    deploy()


@click.command()
@click.option('--config-file', help='Path to the configuration file')
@click.option('--servers', help='Semicolon-separated list of hostnames')
@click.option('--project-user', help='Path to the project directory')
@click.option('--project-dir', help='Path to the project directory')
@click.option('--venv-dir', help='Virtual environment directory')
def setup(config_file, servers, project_user, project_dir, venv_dir):
    config = {}

    if config_file:
        config = load_config(config_file)

    config['servers'] = servers or config.get('servers')
    config['project_user'] = project_user or config.get('project_user')
    config['project_dir'] = project_dir or config.get('project_dir')
    config['venv_dir'] = venv_dir or config.get('venv_dir')

    configure_deployment(**config)
    set_up()