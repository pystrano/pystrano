from os import path
from shlex import quote
from typing import Any

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _split_semicolon_values(value: str) -> list[str]:
    parts: list[str] = []
    for item in value.split(";"):
        parts.extend(item.splitlines())
    return [part.strip() for part in parts if part.strip()]


class PystranoConfig(BaseModel):
    """A pydantic model representing a single deployment server configuration."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

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

    @field_validator("ssh_known_hosts", "secrets", mode="before")
    @classmethod
    def _parse_semicolon_list(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return _split_semicolon_values(value)
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        raise ValueError(f"Expected a string or list, got {type(value).__name__}")

    @field_validator("system_packages", mode="before")
    @classmethod
    def _parse_system_packages(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.replace(";", " ").split() if item.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        raise ValueError(f"Expected a string or list, got {type(value).__name__}")

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
        """Atomically update config values and validate before mutating state."""
        payload = self.model_dump(mode="python")
        payload.update(data)
        updated = type(self).model_validate(payload)
        for field_name in type(self).model_fields:
            object.__setattr__(self, field_name, getattr(updated, field_name))

    def _load_env_file(self) -> dict[str, str]:
        """Load the environment file and return shell-safe values."""
        if not self.env_file:
            return {}
        return {k: quote(str(v)) for k, v in dotenv_values(self.env_file).items()}

    def finalize_config(self):
        """Finalize computed path fields after all overrides are merged."""
        if self.project_user and self.project_root:
            if not path.isabs(self.project_root):
                self.project_root = path.join("/home", self.project_user, self.project_root)
            self.releases_dir = path.join(self.project_root, "releases")
            self.current_dir = path.join(self.project_root, "current")
            self.shared_dir = path.join(self.project_root, "shared")
        else:
            self.releases_dir = None
            self.current_dir = None
            self.shared_dir = None

        if self.project_user and self.venv_dir:
            if not path.isabs(self.venv_dir):
                self.venv_dir = path.join("/home", self.project_user, self.venv_dir)
            self.python_path = path.join(self.venv_dir, "bin", "python")
        else:
            self.python_path = None

        self.env_vars = self._load_env_file() if self.env_file else {}
        self.service_file_name = path.basename(self.service_file) if self.service_file else None
