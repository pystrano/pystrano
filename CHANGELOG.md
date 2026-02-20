# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2026-02-20
### Added
- Support for shallow git clones with configurable `clone_depth` and optional `revision` pins during deployments (`pystrano/core.py`).
- Extras for local development (`test`, `lint`), pytest/coverage/ruff configuration, and a pre-commit configuration to keep quality checks consistent (`pyproject.toml`, `.pre-commit-config.yaml`).
- A comprehensive automated test suite covering config loading, core tasks, and the CLI workflow to guard regressions (`tests/`).
- Dry-run mode for both `setup` and `deploy`, plus optional verbose logging to inspect activity without touching remote hosts (`pystrano/deploy.py`).
- Additional ignored local artifacts for modern Python workflows (`.venv`, coverage files, and `htmlcov`) (`.gitignore`).

### Changed
- Deployment CLI now relies on structured logging instead of prints, reads configs from a computed path, and reports clearer per-step progress with elapsed-time summaries (`pystrano/deploy.py`).
- Example deployment manifest now demonstrates multi-line `system_packages` to improve readability (`example/deployment.yml`).
- Remote command output is hidden by default; pass `--verbose` to stream the raw Fabric output (`pystrano/deploy.py`).
- Runtime dependency minimum versions were raised and `requirements.txt` was regenerated from `pyproject.toml` (`pyproject.toml`, `requirements.txt`).
- `setup.py` metadata was aligned with current project settings (version, Python requirement, dependencies, and classifiers) (`setup.py`).
- README option names and CLI flags were updated to match current behavior (`README.md`).

### Removed
- Removed the legacy `pystrano-setup` console script entry from `setup.py` in favor of the unified `pystrano` command (`setup.py`).

## [1.1.2] - 2025-07-25
### Changed
- Escape environment variables loaded from `.env` files before injecting them into remote commands, preventing accidental shell breakage and injection bugs (`pystrano/config.py`).

## [1.1.1] - 2025-01-13
### Added
- Regenerated `requirements.txt` with pinned, annotated dependencies for reproducible installs on deployment targets (`requirements.txt`).

### Fixed
- Removed an unused import from the CLI entry point and aligned metadata to avoid packaging lint warnings (`pystrano/deploy.py`, `pyproject.toml`, `setup.py`).

## [1.1.0] - 2025-01-11
### Added
- Unified `pystrano` command that accepts `<command> <environment> <app>` arguments, centralising deploy and setup flows with configurable config directories (`pystrano/deploy.py`).
- Expanded documentation with end-to-end usage instructions and the expected config directory layout (`README.md`).

### Changed
- Simplified distribution metadata and trimmed redundant console scripts in favour of the unified CLI (`pyproject.toml`, `setup.py`).
- Refreshed default requirements to match the supported runtime stack (`requirements.txt`).

## [1.0.0] - 2024-12-27
### Added
- Initial public release with Fabric-based tasks for provisioning hosts (`setup`, `deploy`), handling app directory structure, virtualenv creation, git checkout, static collection, and service restarts (`pystrano/core.py`, `pystrano/deploy.py`).
- YAML-driven configuration loader with per-environment overrides and `.env` support (`pystrano/config.py`).
- Basic project packaging metadata and installation instructions (`pyproject.toml`, `setup.py`, `README.md`).
