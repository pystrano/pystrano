from dotenv import dotenv_values
from yaml import safe_load
from os import path


class PystranoConfig(object):
    """A class to represent a Pystrano server configuration."""
    def __init__(self):
        self._config_finalized = False

    def update_dict(self, data):
        """Update the configuration with the given key-value pairs overwriting previous values."""
        self.__dict__.update(**data)
        self._clean()

    def _clean(self):
        """Clean up the configuration values for later use."""

        # Convert ssh_known_hosts to a list
        if hasattr(self, "ssh_known_hosts") and isinstance(getattr(self, "ssh_known_hosts"), str):
            setattr(self, "ssh_known_hosts", getattr(self, "ssh_known_hosts", "").split(";"))

        # Convert secrets to a list
        if hasattr(self, "secrets") and isinstance(getattr(self, "secrets"), str):
            setattr(self, "secrets", getattr(self, "secrets", "").split(";"))

    def _load_env_file(self):
        """Load the environment file and return the values as a dictionary."""
        return dotenv_values(self.env_file)

    def finalize_config(self):
        """Finalize the configuration by cleaning up the values."""
        if self._config_finalized:
            return

        # Mark the configuration as finalized so this method is not called again
        self._config_finalized = True

        self._clean()

        if hasattr(self, "project_user") and hasattr(self, "project_root"):
            setattr(self, "project_root", path.join("/home", self.project_user, self.project_root))
            setattr(self, "releases_dir", path.join(self.project_root, "releases"))
            setattr(self, "current_dir", path.join(self.project_root, "current"))
            setattr(self, "shared_dir", path.join(self.project_root, "shared"))

        if hasattr(self, "venv_dir"):
            setattr(self, "venv_dir", path.join("/home", self.project_user, self.venv_dir))
            setattr(self, "python_path", path.join(self.venv_dir, "bin", "python"))

        if hasattr(self, "env_file"):
            setattr(self, "env_vars", self._load_env_file())

        if hasattr(self, "service_file"):
            setattr(self, "service_file_name", path.basename(self.service_file))

        if hasattr(self, "run_migrations"):
            setattr(self, "run_migrations", self.run_migrations.lower() == "true")
        else:
            setattr(self, "run_migrations", False)

        if hasattr(self, "collect_static_files"):
            setattr(self, "collect_static_files", self.collect_static_files.lower() == "true")
        else:
            setattr(self, "collect_static_files", False)

        if hasattr(self, "port"):
            setattr(self, "port", int(self.port))
        else:
            setattr(self, "port", 22)



def create_server_config(server_description: dict, common_config: dict) -> PystranoConfig:
    """Create a Pystrano server configuration from the given server description and common configuration."""
    config = PystranoConfig()

    # Load common variables first
    config.update_dict(common_config)

    # Load server specific variables (potentially overwriting common variables)
    config.update_dict(server_description)

    # Finalize the configuration
    config.finalize_config()

    return config

def load_config(config_path: str) -> list[PystranoConfig]:
    """Load Pystrano server configurations from the given YAML config file."""
    with open(config_path) as f:
        config = safe_load(f)

    # Get common configuration
    common_config = config.pop("common")

    # Create a cofinguration for each server
    return [create_server_config(server, common_config) for server in config["servers"]]
