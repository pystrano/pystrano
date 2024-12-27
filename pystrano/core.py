from fabric import Connection
from pystrano.config import PystranoConfig
from os import path


def setup_release_dir(connection: Connection, new_release_dir: str):
    """Set up a new release directory on the server."""
    connection.run(f'mkdir -p {new_release_dir}')


def update_source_code(connection: Connection, new_release_dir: str, conf: PystranoConfig):
    """Update the source code in the new release directory."""
    connection.run(f'git clone {conf.source_code_url} {new_release_dir}')
    connection.run(f'cd {new_release_dir} && git checkout {conf.branch}')


def setup_symlinks(connection: Connection, new_release_dir: str, conf: PystranoConfig):
    """Set up symlinks to shared directories."""
    connection.run(f'ln -sfn {conf.shared_dir}/media {new_release_dir}/media')
    connection.run(f'ln -sfn {conf.shared_dir}/.env.{new_release_dir.split("/")[-1]} {conf.shared_dir}/.env')


def install_requirements(connection: Connection, new_release_dir: str, conf: PystranoConfig):
    """Install dependencies in the virtual environment."""
    with connection.cd(new_release_dir):
        connection.run(f'{conf.venv_dir}/bin/pip install -r requirements.txt')


def collect_static_files(connection: Connection, new_release_dir: str, conf: PystranoConfig):
    """Collect static files to the shared directory."""
    with connection.cd(new_release_dir):
        connection.run(f'{conf.python_path} manage.py collectstatic --noinput', env=conf.env_vars)


def migrate_database(connection: Connection, new_release_dir: str, conf: PystranoConfig):
    """Apply migrations to the database."""
    with connection.cd(new_release_dir):
        connection.run(f'{conf.python_path} manage.py migrate', env=conf.env_vars)


def update_symlink(connection: Connection, new_release_dir: str, conf: PystranoConfig):
    """Update the `current` symlink to point to the new release."""
    connection.run(f'ln -sfn {new_release_dir} {conf.current_dir}')


def restart_service(connection: Connection, conf: PystranoConfig):
    """Restart the Gunicorn service."""
    connection.sudo(f'systemctl restart {conf.service_file_name}')


def cleanup_old_releases(connection: Connection, conf: PystranoConfig):
    """Remove old releases, keeping only the last `KEEP_RELEASES`."""

    # Allow people to choose to keep all releases
    if conf.keep_releases <= 0:
        return

    releases = connection.run(f'ls -1 {conf.releases_dir}', hide=True).stdout.split()

    if len(releases) > conf.keep_releases:
        old_releases = releases[:-conf.keep_releases]
        for release in old_releases:
            connection.run(f'rm -rf {conf.releases_dir}/{release}')


def create_project_user(connection: Connection, conf: PystranoConfig):
    """Set up a user if it does not exist."""

    # Check if user exists
    result = connection.run(f'id -u {conf.project_user}', warn=True)

    if result.failed:
        # Create user if it doesn't exist
        connection.sudo(f'useradd -m -s /bin/bash {conf.project_user}')
        # Allow sudo without password
        connection.sudo(f'echo "{conf.project_user} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/{conf.project_user}')


def create_directory_structure(connection: Connection, conf: PystranoConfig):
    """Create the directory structure on the server."""
    connection.sudo(f'mkdir -p {conf.shared_dir}')
    connection.sudo(f'mkdir -p {conf.releases_dir}')
    connection.sudo(f'mkdir -p {conf.venv_dir}')
    connection.sudo(f'chown -R {conf.project_user}:{conf.project_user} {conf.project_root}')


def setup_packages(connection: Connection, conf: PystranoConfig):
    """Install required packages on the server."""
    connection.run('apt update')
    connection.run('apt install -y python3 python3-venv python3-pip git')

    # Install additional system packages if specified
    if conf.system_packages:
        connection.run(f'apt install -y {conf.system_packages}')


def setup_venv(connection: Connection, conf: PystranoConfig):
    """Set up a virtual environment."""
    connection.run(f'python3 -m venv {conf.venv_dir}')
    connection.run(f'chown -R {conf.project_user}:{conf.project_user} {conf.venv_dir}')


def copy_authorized_keys(connection: Connection, conf: PystranoConfig):
    """Copy the authorized keys to the project user's directory."""
    connection.run(f'mkdir -p /home/{conf.project_user}/.ssh')
    connection.run(f'cp ~/.ssh/authorized_keys /home/{conf.project_user}/.ssh/')
    connection.run(f'chown -R {conf.project_user}:{conf.project_user} /home/{conf.project_user}/.ssh')


def setup_known_hosts(connection: Connection, conf: PystranoConfig):
    """Add known hosts to the project user's SSH configuration."""
    connection.run(f'ssh-keyscan github.com >> /home/{conf.project_user}/.ssh/known_hosts')

    for host in conf.ssh_known_hosts:
        connection.run(f'ssh-keyscan {host} >> /home/{conf.project_user}/.ssh/known_hosts')

    connection.run(f'chown {conf.project_user}:{conf.project_user} /home/{conf.project_user}/.ssh/known_hosts')


def setup_service(connection: Connection, conf: PystranoConfig):
    """Set up the service."""
    connection.put(conf.service_file, f'/etc/systemd/system/{conf.service_file_name}')
    connection.sudo('systemctl daemon-reload')
    connection.sudo(f'systemctl enable {conf.service_file_name}')


def try_to_remove_release_dir(connection: Connection, release_dir: str):
    """Try to remove a release directory."""
    try:
        connection.run(f'rm -rf {release_dir}')
    except Exception as e:
        print(f"Error removing release directory: {e}")


def copy_env_file(connection: Connection, new_release_dir: str, conf: PystranoConfig):
    """Copy the environment file to the shared directory."""
    connection.put(conf.env_file, f'{conf.shared_dir}/.env.{new_release_dir.split("/")[-1]}')


def copy_secrets(connection: Connection, conf: PystranoConfig):
    """Copy secrets to the shared directory."""
    for secret in conf.secrets:
        secret_file_name = path.basename(secret)
        connection.put(secret, f'{conf.shared_dir}/{secret_file_name}')


def link_secrets_to_release(connection: Connection, new_release_dir: str, conf: PystranoConfig):
    """Link secrets to the release directory."""
    for secret in conf.secrets:
        secret_file_name = path.basename(secret)
        connection.run(f'ln -sfn {conf.shared_dir}/{secret_file_name} {new_release_dir}/{secret_file_name}')