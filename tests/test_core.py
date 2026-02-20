from types import SimpleNamespace
from unittest.mock import call

from pystrano import core


def test_setup_release_dir(fake_connection):
    release_dir = "/srv/app/releases/20240101"

    core.setup_release_dir(fake_connection, release_dir)

    fake_connection.run.assert_called_once_with(f"mkdir -p {release_dir}")


def test_install_requirements(fake_connection):
    release_dir = "/srv/app/releases/20240101"
    conf = SimpleNamespace(venv_dir="/home/app/.venv")

    core.install_requirements(fake_connection, release_dir, conf)

    fake_connection.cd.assert_called_once_with(release_dir)
    fake_connection.run.assert_called_once_with(
        "/home/app/.venv/bin/pip install -r requirements.txt"
    )


def test_collect_static_files(fake_connection):
    release_dir = "/srv/app/releases/20240101"
    conf = SimpleNamespace(
        python_path="/home/app/.venv/bin/python",
        env_vars={"DJANGO_SETTINGS_MODULE": "mysite.settings"},
    )

    core.collect_static_files(fake_connection, release_dir, conf)

    fake_connection.run.assert_called_once_with(
        "/home/app/.venv/bin/python manage.py collectstatic --noinput",
        env={"DJANGO_SETTINGS_MODULE": "mysite.settings"},
    )


def test_cleanup_old_releases(fake_connection):
    conf = SimpleNamespace(releases_dir="/srv/app/releases", keep_releases=1)
    releases_output = "20240101\n20240102\n20240103\n"

    def run_side_effect(command, hide=False):
        if command.startswith("ls -1"):
            return SimpleNamespace(stdout=releases_output)
        return SimpleNamespace(stdout="")

    fake_connection.run.side_effect = run_side_effect

    core.cleanup_old_releases(fake_connection, conf)

    fake_connection.run.assert_any_call("rm -rf /srv/app/releases/20240101")
    fake_connection.run.assert_any_call("rm -rf /srv/app/releases/20240102")


def test_cleanup_old_releases_no_limit(fake_connection):
    conf = SimpleNamespace(releases_dir="/srv/app/releases", keep_releases=0)

    core.cleanup_old_releases(fake_connection, conf)

    fake_connection.run.assert_not_called()


def test_setup_packages(fake_connection):
    conf = SimpleNamespace(system_packages="libpq-dev")

    core.setup_packages(fake_connection, conf)

    fake_connection.run.assert_any_call("apt update")
    fake_connection.run.assert_any_call("apt install -y python3 python3-venv python3-pip git")
    fake_connection.run.assert_any_call("apt install -y libpq-dev")


def test_copy_secrets(fake_connection):
    conf = SimpleNamespace(shared_dir="/srv/app/shared", secrets=["/tmp/secret.json", "/tmp/.env"])

    core.copy_secrets(fake_connection, conf)

    fake_connection.put.assert_any_call("/tmp/secret.json", "/srv/app/shared/secret.json")
    fake_connection.put.assert_any_call("/tmp/.env", "/srv/app/shared/.env")


def test_update_source_code(fake_connection):
    conf = SimpleNamespace(
        source_code_url="git@github.com:example/repo.git",
        branch="main",
        clone_depth=1,
    )

    core.update_source_code(fake_connection, "/srv/app/releases/20240101", conf)

    fake_connection.run.assert_called_once_with(
        "git clone --single-branch --depth 1 --branch main git@github.com:example/repo.git /srv/app/releases/20240101"
    )


def test_update_source_code_with_revision(fake_connection):
    conf = SimpleNamespace(
        source_code_url="git@github.com:example/repo.git",
        branch="main",
        revision="v1.2.3",
        clone_depth=None,
    )

    core.update_source_code(fake_connection, "/srv/app/releases/20240101", conf)

    fake_connection.cd.assert_called_once_with("/srv/app/releases/20240101")
    assert fake_connection.run.call_args_list == [
        call(
            "git clone --single-branch --branch main git@github.com:example/repo.git /srv/app/releases/20240101"
        ),
        call("git fetch --tags --force"),
        call("git checkout v1.2.3"),
    ]


def test_setup_symlinks(fake_connection):
    conf = SimpleNamespace(shared_dir="/srv/app/shared")
    release_dir = "/srv/app/releases/20240101"

    core.setup_symlinks(fake_connection, release_dir, conf)

    fake_connection.run.assert_has_calls(
        [
            call("ln -sfn /srv/app/shared/media /srv/app/releases/20240101/media"),
            call("ln -sfn /srv/app/shared/.env.20240101 /srv/app/shared/.env"),
        ]
    )


def test_update_symlink(fake_connection):
    conf = SimpleNamespace(current_dir="/srv/app/current")
    release_dir = "/srv/app/releases/20240101"

    core.update_symlink(fake_connection, release_dir, conf)

    fake_connection.run.assert_called_once_with(
        "ln -sfn /srv/app/releases/20240101 /srv/app/current"
    )


def test_restart_service(fake_connection):
    conf = SimpleNamespace(service_file_name="gunicorn.service")

    core.restart_service(fake_connection, conf)

    fake_connection.sudo.assert_called_once_with("systemctl restart gunicorn.service")


def test_create_project_user_exists(fake_connection):
    fake_connection.run.return_value = SimpleNamespace(failed=False)
    conf = SimpleNamespace(project_user="deployer")

    core.create_project_user(fake_connection, conf)

    fake_connection.run.assert_called_once_with("id -u deployer", warn=True)
    fake_connection.sudo.assert_not_called()


def test_create_project_user_new(fake_connection):
    fake_connection.run.return_value = SimpleNamespace(failed=True)
    conf = SimpleNamespace(project_user="deployer")

    core.create_project_user(fake_connection, conf)

    fake_connection.sudo.assert_has_calls(
        [
            call("useradd -m -s /bin/bash deployer"),
            call('echo "deployer ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/deployer'),
        ]
    )


def test_create_directory_structure(fake_connection):
    conf = SimpleNamespace(
        shared_dir="/srv/app/shared",
        releases_dir="/srv/app/releases",
        venv_dir="/srv/app/.venv",
        project_root="/srv/app",
        project_user="deployer",
    )

    core.create_directory_structure(fake_connection, conf)

    fake_connection.sudo.assert_has_calls(
        [
            call("mkdir -p /srv/app/shared"),
            call("mkdir -p /srv/app/releases"),
            call("mkdir -p /srv/app/.venv"),
            call("chown -R deployer:deployer /srv/app"),
        ]
    )


def test_setup_venv(fake_connection):
    conf = SimpleNamespace(venv_dir="/srv/app/.venv", project_user="deployer")

    core.setup_venv(fake_connection, conf)

    fake_connection.run.assert_has_calls(
        [
            call("python3 -m venv /srv/app/.venv"),
            call("chown -R deployer:deployer /srv/app/.venv"),
        ]
    )


def test_copy_authorized_keys(fake_connection):
    conf = SimpleNamespace(project_user="deployer")

    core.copy_authorized_keys(fake_connection, conf)

    fake_connection.run.assert_has_calls(
        [
            call("mkdir -p /home/deployer/.ssh"),
            call("cp ~/.ssh/authorized_keys /home/deployer/.ssh/"),
            call("chown -R deployer:deployer /home/deployer/.ssh"),
        ]
    )


def test_setup_known_hosts(fake_connection):
    conf = SimpleNamespace(project_user="deployer", ssh_known_hosts=["gitlab.com", "bitbucket.org"])

    core.setup_known_hosts(fake_connection, conf)

    fake_connection.run.assert_has_calls(
        [
            call("ssh-keyscan github.com >> /home/deployer/.ssh/known_hosts"),
            call("ssh-keyscan gitlab.com >> /home/deployer/.ssh/known_hosts"),
            call("ssh-keyscan bitbucket.org >> /home/deployer/.ssh/known_hosts"),
            call("chown deployer:deployer /home/deployer/.ssh/known_hosts"),
        ]
    )


def test_setup_service(fake_connection):
    conf = SimpleNamespace(
        service_file="/tmp/gunicorn.service",
        service_file_name="gunicorn.service",
    )

    core.setup_service(fake_connection, conf)

    fake_connection.put.assert_called_once_with(
        "/tmp/gunicorn.service",
        "/etc/systemd/system/gunicorn.service",
    )
    fake_connection.sudo.assert_has_calls(
        [
            call("systemctl daemon-reload"),
            call("systemctl enable gunicorn.service"),
        ]
    )


def test_try_to_remove_release_dir(fake_connection, mocker):
    core.try_to_remove_release_dir(fake_connection, "/srv/app/releases/old")

    fake_connection.run.assert_called_once_with("rm -rf /srv/app/releases/old")

    fake_connection.run.side_effect = Exception("boom")
    printer = mocker.patch("builtins.print")

    core.try_to_remove_release_dir(fake_connection, "/srv/app/releases/broken")

    printer.assert_called_once()


def test_copy_env_file(fake_connection):
    conf = SimpleNamespace(env_file="/tmp/.env", shared_dir="/srv/app/shared")

    core.copy_env_file(fake_connection, "/srv/app/releases/20240101", conf)

    fake_connection.put.assert_called_once_with("/tmp/.env", "/srv/app/shared/.env.20240101")


def test_link_secrets_to_release(fake_connection):
    conf = SimpleNamespace(
        shared_dir="/srv/app/shared",
        secrets=["/srv/app/shared/secret.json", "/srv/app/shared/.env"],
    )

    core.link_secrets_to_release(fake_connection, "/srv/app/releases/20240101", conf)

    fake_connection.run.assert_has_calls(
        [
            call("ln -sfn /srv/app/shared/secret.json /srv/app/releases/20240101/secret.json"),
            call("ln -sfn /srv/app/shared/.env /srv/app/releases/20240101/.env"),
        ]
    )
