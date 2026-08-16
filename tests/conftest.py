import pytest


@pytest.fixture(autouse=True)
def _isolate_from_user_config(monkeypatch):
    """Never pick up the developer's `~/.config/viewmd/config` during tests (VIEWMD-0061)."""
    monkeypatch.setenv("VIEWMD_NO_CONFIG", "1")
