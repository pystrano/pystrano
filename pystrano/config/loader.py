from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError
from yaml import safe_load

from .models import PystranoConfig


class DeploymentConfigFile(BaseModel):
    """Top-level schema for the YAML deployment file."""

    model_config = ConfigDict(extra="forbid")

    common: dict[str, Any]
    servers: list[dict[str, Any]]


def _format_validation_error(exc: ValidationError) -> str:
    """Turn pydantic errors into short user-facing messages."""
    parts = []
    for error in exc.errors():
        location = ".".join(str(item) for item in error["loc"]) or "<root>"
        parts.append(f"{location}: {error['msg']}")
    return "; ".join(parts)


def create_server_config(server_description: dict, common_config: dict) -> PystranoConfig:
    """Build a Pystrano config from shared defaults and server overrides."""
    merged = {**common_config, **server_description}
    try:
        config = PystranoConfig(**merged)
    except ValidationError as exc:
        host = server_description.get("host", "<unknown>")
        details = _format_validation_error(exc)
        raise ValueError(f"Invalid server config for '{host}': {details}") from exc

    config.finalize_config()
    return config


def load_config(config_path: str) -> list[PystranoConfig]:
    """Load Pystrano server configurations from the given YAML config file."""
    with open(config_path) as f:
        parsed = safe_load(f)

    if parsed is None:
        raise ValueError(f"Config file '{config_path}' is empty.")

    try:
        config_file = DeploymentConfigFile.model_validate(parsed)
    except ValidationError as exc:
        details = _format_validation_error(exc)
        raise ValueError(f"Invalid deployment config '{config_path}': {details}") from exc

    if not config_file.servers:
        raise ValueError(f"Invalid deployment config '{config_path}': 'servers' must not be empty.")

    server_configs: list[PystranoConfig] = []
    for index, server in enumerate(config_file.servers):
        try:
            server_configs.append(create_server_config(server, config_file.common))
        except ValueError as exc:
            raise ValueError(
                f"Invalid deployment config '{config_path}' at servers[{index}]: {exc}"
            ) from exc

    return server_configs
