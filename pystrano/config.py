from os import path
from shlex import quote
from typing import Any

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator, model_validator
from yaml import safe_load


def _split_semicolon_values(value: str) -> list[str]:
    parts: list[str] = []
    for item in value.split(";"):
        parts.extend(item.splitlines())
    return [part.strip() for part in parts if part.strip()]


class PystranoConfig(BaseModel):
    """A pydantic model representing a single deployment server configuration."""

    model_config = ConfigDict(extra="allow", validate_assignment=True)

    source_code_url: str | None = None
    project_root: str | None = None
    project_user: str | None = None
    venv_dir: str | None = None
    keep_releases: int = 5
    system_packages: list[str] = Field(default_factory=list)
    env_file: str | None = None
    ssh_known_hosts: list[str] = Field(default_factory=list)
    service_file: str | None = None
    secrets: list[str] = Field(default_factory=list)
    branch: str | None = None
    revision: str | None = None
    clone_depth: int | None = 1
    host: str | None = None
    port: int = 22
    run_migrations: bool = False
    collect_static_files: bool = False

    releases_dir: str | None = None
    current_dir: str | None = None
    shared_dir: str | None = None
    python_path: str | None = None
    env_vars: dict[str, str] = Field(default_factory=dict)
    service_file_name: str | None = None

    _config_finalized: bool = PrivateAttr(default=False)

    @field_validator("ssh_known_hosts", "secrets", mode="before")
    @classmethod
    def _parse_semicolon_list(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return _split_semicolon_values(value)
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        raise TypeError(f"Expected a string or list, got {type(value).__name__}")

    @field_validator("system_packages", mode="before")
    @classmethod
    def _parse_system_packages(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.replace(";", " ").split() if item.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        raise TypeError(f"Expected a string or list, got {type(value).__name__}")

    @field_validator("run_migrations", "collect_static_files", mode="before")
    @classmethod
    def _parse_bool(cls, value):
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)

        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off", ""}:
            return False
        raise ValueError(f"Invalid boolean value: {value!r}")

    @field_validator("port", mode="before")
    @classmethod
    def _parse_port(cls, value):
        if value is None or value == "":
            return 22
        return int(value)

    @field_validator("clone_depth", mode="before")
    @classmethod
    def _parse_clone_depth(cls, value):
        if value is None or value == "":
            return 1
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        if parsed <= 0:
            return None
        return parsed

    @model_validator(mode="after")
    def _apply_revision_rules(self):
        if self.revision and self.clone_depth is not None:
            object.__setattr__(self, "clone_depth", None)
        return self

    def update_dict(self, data: dict[str, Any]):
        """Update config values and re-run pydantic assignment validation."""
        for key, value in data.items():
            setattr(self, key, value)
        self._config_finalized = False

    def _load_env_file(self) -> dict[str, str]:
        """Load the environment file and return shell-safe values."""
        if not self.env_file:
            return {}
        return {k: quote(str(v)) for k, v in dotenv_values(self.env_file).items()}

    def finalize_config(self):
        """Finalize computed path fields after all overrides are merged."""
        if self._config_finalized:
            return

        self._config_finalized = True

        if self.project_user and self.project_root:
            if not path.isabs(self.project_root):
                self.project_root = path.join("/home", self.project_user, self.project_root)
            self.releases_dir = path.join(self.project_root, "releases")
            self.current_dir = path.join(self.project_root, "current")
            self.shared_dir = path.join(self.project_root, "shared")

        if self.project_user and self.venv_dir:
            if not path.isabs(self.venv_dir):
                self.venv_dir = path.join("/home", self.project_user, self.venv_dir)
            self.python_path = path.join(self.venv_dir, "bin", "python")

        if self.env_file:
            self.env_vars = self._load_env_file()

        if self.service_file:
            self.service_file_name = path.basename(self.service_file)


def create_server_config(server_description: dict, common_config: dict) -> PystranoConfig:
    """Build a Pystrano config from shared defaults and server overrides."""
    merged = {**common_config, **server_description}
    config = PystranoConfig(**merged)
    config.finalize_config()
    return config


def load_config(config_path: str) -> list[PystranoConfig]:
    """Load Pystrano server configurations from the given YAML config file."""
    with open(config_path) as f:
        config = safe_load(f)

    common_config = config.pop("common")
    return [create_server_config(server, common_config) for server in config["servers"]]
