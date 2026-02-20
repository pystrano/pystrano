from contextlib import contextmanager

import pytest


@pytest.fixture
def fake_connection(mocker):
    """Provide a lightweight stand-in for Fabric's Connection."""

    @contextmanager
    def _cd(_path):  # pragma: no cover - trivial helper
        yield None

    connection = mocker.Mock()
    connection.cd = mocker.Mock(side_effect=lambda _: _cd(_))
    connection.run = mocker.Mock()
    connection.sudo = mocker.Mock()
    connection.put = mocker.Mock()
    return connection
