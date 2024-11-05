# Pystrano

---

Pystrano is a simple deployment tool for Python projects.
It is inspired by Capistrano, a popular deployment tool for
Ruby projects.

## Disclaimer

This is a work in progress. It is not ready for production use
just yet.

## Installation

```bash
pip install pystrano
```

## Usage

Pystrano is a command line tool. To deploy a project, you need
to create a config for the environment you want to deploy to.

### Configuration

Pystrano uses a YAML file to configure the deployment.
Here is a description of variables you can set in the
config file:

- `repo_url`: The URL of the git repository.
- `project_user`: The user that will be used to deploy the project.
- `project_dir`: The directory where the project is located.
- `venv_dir`: The directory where the virtual environment is located (in the `project_user` home).
- `servers`: A list of servers to deploy to (hostname or ip addresses separated by `;`).
- `keep_releases`: The number of releases to keep on the server.
- `system_packages`: A list of system packages to install on the server (during setup).
- `env_file`: The path to the environment file to use for the deployment.
- `ssh_known_hosts`: The path to the known hosts file to use for the deployment (during setup; separated by `;`).
- `gunicorn_service_file`: The path to the gunicorn service file to use for the deployment.

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
