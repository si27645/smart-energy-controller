"""Wire pytest-homeassistant-custom-component's fixtures into this repo's tests
and allow loading custom_components/smart_energy_controller as a real integration.
"""
import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
