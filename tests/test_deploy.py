import logging
from types import SimpleNamespace

from click.testing import CliRunner

from pystrano import deploy


def test_make_connection_dry_run():
    connection = deploy._make_connection("app", "host", 2222, dry_run=True, hide_output=True)

    assert isinstance(connection, deploy.DryRunConnection)


def test_make_connection_real(mocker):
    connection_cls = mocker.patch("pystrano.deploy.Connection")
    config_cls = mocker.patch("pystrano.deploy.Config")

    deploy._make_connection("app", "example.com", 2222, dry_run=False, hide_output=True)

    config_cls.assert_called_once_with(overrides={"run": {"hide": True}, "sudo": {"hide": True}})
    connection_cls.assert_called_once_with(
        "app@example.com",
        forward_agent=True,
        port=2222,
        config=config_cls.return_value,
    )


def test_make_connection_real_verbose(mocker):
    connection_cls = mocker.patch("pystrano.deploy.Connection")
    config_cls = mocker.patch("pystrano.deploy.Config")

    deploy._make_connection("app", "example.com", 2222, dry_run=False, hide_output=False)

    connection_cls.assert_called_once_with("app@example.com", forward_agent=True, port=2222)
    config_cls.assert_not_called()


def test_main_dispatches_deploy(tmp_path, mocker):
    runner = CliRunner()
    server_configs = [SimpleNamespace()]

    load_config = mocker.patch("pystrano.deploy.load_config", return_value=server_configs)
    deploy_mock = mocker.patch("pystrano.deploy.deploy")
    setup_mock = mocker.patch("pystrano.deploy.set_up")
    configure_loggers = mocker.patch("pystrano.deploy._configure_library_loggers")

    result = runner.invoke(
        deploy.main,
        ["deploy", "staging", "myapp", "--deploy-config-dir", str(tmp_path), "--dry-run"],
    )

    assert result.exit_code == 0
    load_config.assert_called_once()
    configure_loggers.assert_called_once_with(False)
    deploy_mock.assert_called_once_with(
        server_configs,
        dry_run=True,
        context_label="staging myapp",
        hide_remote_output=True,
    )
    setup_mock.assert_not_called()


def test_main_dispatches_setup(tmp_path, mocker):
    runner = CliRunner()
    server_configs = [SimpleNamespace()]

    load_config = mocker.patch("pystrano.deploy.load_config", return_value=server_configs)
    deploy_mock = mocker.patch("pystrano.deploy.deploy")
    setup_mock = mocker.patch("pystrano.deploy.set_up")
    configure_loggers = mocker.patch("pystrano.deploy._configure_library_loggers")

    result = runner.invoke(
        deploy.main,
        ["setup", "production", "api", "--deploy-config-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
    load_config.assert_called_once()
    configure_loggers.assert_called_once_with(False)
    setup_mock.assert_called_once_with(
        server_configs,
        dry_run=False,
        context_label="production api",
        hide_remote_output=True,
    )
    deploy_mock.assert_not_called()


def test_main_verbose_disables_quiet_mode(tmp_path, mocker):
    runner = CliRunner()
    server_configs = [SimpleNamespace()]

    load_config = mocker.patch("pystrano.deploy.load_config", return_value=server_configs)
    deploy_mock = mocker.patch("pystrano.deploy.deploy")
    configure_loggers = mocker.patch("pystrano.deploy._configure_library_loggers")

    result = runner.invoke(
        deploy.main,
        [
            "deploy",
            "production",
            "api",
            "--deploy-config-dir",
            str(tmp_path),
            "--verbose",
        ],
    )

    assert result.exit_code == 0
    load_config.assert_called_once()
    configure_loggers.assert_called_once_with(True)
    deploy_mock.assert_called_once_with(
        server_configs,
        dry_run=False,
        context_label="production api",
        hide_remote_output=False,
    )


def test_main_invalid_command(tmp_path, mocker):
    runner = CliRunner()
    mocker.patch("pystrano.deploy.load_config", return_value=[SimpleNamespace()])

    result = runner.invoke(
        deploy.main,
        ["unknown", "staging", "myapp", "--deploy-config-dir", str(tmp_path)],
    )

    assert result.exit_code != 0
    assert isinstance(result.exception, SystemExit)


def test_dry_run_connection_methods(caplog):
    conn = deploy.DryRunConnection("app@example.com:22")

    with caplog.at_level(logging.INFO):
        run_result = conn.run("echo test")
        sudo_result = conn.sudo("id")
        conn.put("/tmp/local", "/tmp/remote")
        with conn.cd("/srv/app"):
            pass

    assert run_result.failed is False
    assert sudo_result.failed is False
    assert "RUN [app@example.com:22]: echo test" in caplog.text
    assert "CD [app@example.com:22]: -> /srv/app" in caplog.text


def test_step_helpers_emit_expected_prefixes(caplog):
    with caplog.at_level(logging.INFO):
        deploy._step("Example step")
        deploy._success("All done")

    assert "✓ Example step" in caplog.text
    assert "✅ All done" in caplog.text


def test_set_up_invokes_helpers(mocker):
    server_config = SimpleNamespace(
        host="example.com",
        port=2222,
        service_file="/etc/systemd/system/gunicorn.service",
        service_file_name="gunicorn.service",
        secrets=["secret.json"],
        project_user="deploy",
        venv_dir="/home/deploy/.venv",
    )
    connection = mocker.Mock()
    make_connection = mocker.patch("pystrano.deploy._make_connection", return_value=connection)
    create_project_user = mocker.patch("pystrano.deploy.create_project_user")
    copy_authorized_keys = mocker.patch("pystrano.deploy.copy_authorized_keys")
    create_directory_structure = mocker.patch("pystrano.deploy.create_directory_structure")
    setup_packages = mocker.patch("pystrano.deploy.setup_packages")
    setup_venv = mocker.patch("pystrano.deploy.setup_venv")
    setup_known_hosts = mocker.patch("pystrano.deploy.setup_known_hosts")
    setup_service = mocker.patch("pystrano.deploy.setup_service")
    copy_secrets = mocker.patch("pystrano.deploy.copy_secrets")

    deploy.set_up([server_config], dry_run=True)

    make_connection.assert_called_once_with("root", "example.com", 2222, True, True)
    create_project_user.assert_called_once_with(connection, server_config)
    copy_authorized_keys.assert_called_once_with(connection, server_config)
    create_directory_structure.assert_called_once_with(connection, server_config)
    setup_packages.assert_called_once_with(connection, server_config)
    setup_venv.assert_called_once_with(connection, server_config)
    setup_known_hosts.assert_called_once_with(connection, server_config)
    setup_service.assert_called_once_with(connection, server_config)
    copy_secrets.assert_called_once_with(connection, server_config)


def test_deploy_executes_full_flow(mocker):
    server_config = SimpleNamespace(
        host="example.com",
        port=22,
        project_user="app",
        releases_dir="/srv/app/releases",
        secrets=["secret.json"],
        collect_static_files=True,
        run_migrations=True,
        service_file="/etc/systemd/system/gunicorn.service",
        service_file_name="gunicorn.service",
        branch="main",
    )
    connection = mocker.Mock()
    make_connection = mocker.patch("pystrano.deploy._make_connection", return_value=connection)
    datetime_mock = mocker.patch("pystrano.deploy.datetime")
    datetime_mock.now.return_value.strftime.return_value = "20240101010101"

    helpers = {
        name: mocker.patch(f"pystrano.deploy.{name}")
        for name in [
            "setup_release_dir",
            "update_source_code",
            "copy_env_file",
            "setup_symlinks",
            "install_requirements",
            "link_secrets_to_release",
            "collect_static_files",
            "migrate_database",
            "update_symlink",
            "restart_service",
            "cleanup_old_releases",
        ]
    }

    deploy.deploy([server_config], dry_run=False)

    make_connection.assert_called_once_with("app", "example.com", 22, False, True)

    new_release_dir = "/srv/app/releases/20240101010101"

    helpers["setup_release_dir"].assert_called_once_with(connection, new_release_dir)
    helpers["update_source_code"].assert_called_once_with(
        connection,
        new_release_dir,
        server_config,
    )
    helpers["copy_env_file"].assert_called_once_with(
        connection,
        new_release_dir,
        server_config,
    )
    helpers["setup_symlinks"].assert_called_once_with(
        connection,
        new_release_dir,
        server_config,
    )
    helpers["install_requirements"].assert_called_once_with(
        connection,
        new_release_dir,
        server_config,
    )
    helpers["link_secrets_to_release"].assert_called_once_with(
        connection,
        new_release_dir,
        server_config,
    )
    helpers["collect_static_files"].assert_called_once_with(
        connection,
        new_release_dir,
        server_config,
    )
    helpers["migrate_database"].assert_called_once_with(
        connection,
        new_release_dir,
        server_config,
    )
    helpers["update_symlink"].assert_called_once_with(
        connection,
        new_release_dir,
        server_config,
    )
    helpers["restart_service"].assert_called_once_with(connection, server_config)
    helpers["cleanup_old_releases"].assert_called_once_with(connection, server_config)
