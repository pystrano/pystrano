# Pystrano

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

## Usage

Pystrano is a command line tool. To deploy a project, you need
to create a config for the environment you want to deploy to.

### Configuration

Pystrano uses a YAML file to configure the deployment. It contains two sections: `common` and `servers`. Variables in `common` section are shared across all servers, while in `servers` section you define a list of servers to deploy to. It is also possible to define server-specific variables, which will override the common ones (if defined).

Here is a description of variables you can set in the config file:

- `source_code_url`: The URL of the git repository;
- `project_root`: The directory where the project is located;
- `project_user`: The user that will be used to deploy the project;
- `venv_dir`: The directory where the virtual environment is located (in the `project_user` home);
- `keep_releases`: The number of releases to keep on the server. If set to 0 or less, all releases will be kept;
- `system_packages`: A list of system packages to install on the server (during setup);
- `env_file`: The path to the environment file to use for the deployment;
- `ssh_known_hosts`: The path to the known hosts file to use for the deployment  (during setup; separated by semicolons);
- `service_file`: The path to the service file to set up/use in deployment (optional);
- `secrets`: List of secrets to set up on the server (during setup only for now; separated by semicolons);
- `branch`: The name of the branch to deploy.

Server-specific variables:

- `host`: The hostname of the server;
- `port`: The port to use for SSH connection (optional, default is 22);
- `run_migrations`: Whether to run migrations on deployment (optional, default is false);
- `run_collectstatic`: Whether to run collectstatic on deployment (optional, default is false);

### Deployment

To set up deployment for a project, run the following command:

```bash
pystrano-setup --config-file=path/to/config.yml
```

This will set up your server to be ready for deployment.

To deploy your project, run the following command:

```bash
pystrano --config-file=path/to/config.yml
```
