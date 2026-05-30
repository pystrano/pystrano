from .core import collect_static_files, migrate_database, run_release_command


class DeploymentWorkflow:
    """Framework-specific deployment hooks."""

    def run_release_steps(self, connection, new_release_dir: str, conf) -> list[str]:
        return []


class DjangoDeploymentWorkflow(DeploymentWorkflow):
    def run_release_steps(self, connection, new_release_dir: str, conf) -> list[str]:
        ran_static = bool(getattr(conf, "collect_static_files", False))
        ran_migrations = bool(getattr(conf, "run_migrations", False))

        if ran_static:
            collect_static_files(connection, new_release_dir, conf)

        if ran_migrations:
            migrate_database(connection, new_release_dir, conf)

        if ran_static and ran_migrations:
            return ["Applied migrations and refreshed static assets"]
        if ran_static:
            return ["Refreshed static assets"]
        if ran_migrations:
            return ["Applied database migrations"]
        return []


class FastAPIDeploymentWorkflow(DeploymentWorkflow):
    def run_release_steps(self, connection, new_release_dir: str, conf) -> list[str]:
        messages = []

        if getattr(conf, "collect_static_files", False):
            command = getattr(conf, "static_files_command", None)
            if not command:
                raise ValueError(
                    "FastAPI static collection requires static_files_command "
                    "when collect_static_files is true"
                )
            run_release_command(connection, new_release_dir, conf, command)
            messages.append("Refreshed static assets")

        if getattr(conf, "run_migrations", False):
            command = getattr(conf, "migration_command", None)
            if not command:
                command = f"{conf.venv_dir}/bin/alembic upgrade head"
            run_release_command(connection, new_release_dir, conf, command)
            messages.append("Applied database migrations")

        return messages


WORKFLOWS = {
    "django": DjangoDeploymentWorkflow(),
    "fastapi": FastAPIDeploymentWorkflow(),
}


def get_workflow(framework: str) -> DeploymentWorkflow:
    try:
        return WORKFLOWS[framework]
    except KeyError as exc:
        raise ValueError(f"Unsupported framework: {framework}") from exc
