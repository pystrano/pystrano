# Pystrano

---

[![Tests](https://github.com/pystrano/pystrano/actions/workflows/tests.yml/badge.svg?branch=master)](https://github.com/pystrano/pystrano/actions/workflows/tests.yml)

Pystrano is a simple deployment tool for Python projects.
It is inspired by Capistrano, a popular deployment tool for
Ruby projects.

## Disclaimer

This is a work in progress. It is not ready for production use
just yet. Proceed with caution. Currently used with Ubuntu
by yours truly. If someone finds it useful and wants to use it
in any capacity, don't hesitate.

## Installation

```bash
pip install pystrano
```

Requires Python `3.12+`.

### Configuration

Pystrano uses a YAML file with two top-level sections: `common` and `servers`.
Values in `common` are shared defaults. Values in each `servers` item override `common`.

Here is a description of variables you can set in the config file:

- `source_code_url`: The URL of the git repository;
- `project_root`: The directory where the project is located;
- `project_user`: The user that will be used to deploy the project;
- `venv_dir`: The directory where the virtual environment is located (in the `project_user` home);
- `keep_releases`: The number of releases to keep on the server. If set to 0 or less, all releases will be kept;
- `system_packages`: System packages to install during setup. Accepts YAML list, whitespace-separated string, or semicolon-separated string;
- `env_file`: The path to the environment file to use for the deployment;
- `ssh_known_hosts`: List of hostnames to add via `ssh-keyscan` during setup (semicolon-separated string or YAML list);
- `service_file`: The path to the service file to set up/use in deployment (optional);
- `secrets`: List of secret file paths to copy during setup (semicolon-separated string or YAML list);
- `branch`: The name of the branch to deploy.
- `clone_depth`: Depth to use for the shallow clone (default 1; set to 0 for a full clone).
- `revision`: Optional git revision (tag, SHA, or ref) to check out after cloning.

Server-specific variables:

- `host`: The hostname of the server;
- `port`: The port to use for SSH connection (optional, default is 22);
- `run_migrations`: Whether to run migrations on deployment (optional, default is false; use YAML booleans `true`/`false`);
- `collect_static_files`: Whether to collect static files on deployment (optional, default is false; use YAML booleans `true`/`false`);

Validation rules:

- `common` is required;
- `servers` is required and must be non-empty;
- unknown keys are rejected (strict validation), so typos fail fast.

Default directory structure for the configs is as follows:

```commandline
deploy/
    app_name/
        environment_name/
            deployment.yml
```

## Usage

Pystrano is a command line tool. To deploy a project, you need
to create a config for the environment you want to deploy to.
General syntax for usage is as follows:

```bash
pystrano <command> <environment> <app>
```

Available commands are:

- `setup`: Set up the server for deployment;
- `deploy`: Deploy the project to the server.

Optional arguments:

- `--deploy-config-dir`: The directory where the deployment configs are located (default is `deploy`);
- `--config-file-name`: The name of the config file to use (default is `deployment.yml`);
- `--verbose`: Enable verbose logging output;
- `--dry-run`: Print all commands without executing them.

### Example usage

To set up deployment for a project, run the following command:

```bash
pystrano setup production api
```

This will set up your production server to be ready for deployment.

To deploy your project, run the following command:

```bash
pystrano deploy production api
```

To preview what will run without making remote changes:

```bash
pystrano deploy production api --dry-run --verbose
```
