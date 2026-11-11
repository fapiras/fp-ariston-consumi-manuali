"""Use the real HA runtime in Linux CI; all cloud calls are mocked."""
import pytest


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    yield
