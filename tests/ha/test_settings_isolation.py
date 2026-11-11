"""A settings outage must not discard a fresh state or mask a state outage."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed
from custom_components.fp_ariston_consumi.coordinator import DeviceDataUpdateCoordinator
from custom_components.fp_ariston_consumi.const import COORDINATOR
from custom_components.fp_ariston_consumi.vendor.ariston_net_api import ConnectionException


async def test_settings_500_does_not_discard_state_and_next_poll_recovers(hass):
    device = SimpleNamespace(name='Boiler', async_update_settings=AsyncMock(side_effect=ConnectionException(500)))
    state = AsyncMock(return_value={'temperature':47})
    c = DeviceDataUpdateCoordinator(hass, device,600,COORDINATOR,state)
    assert await c._async_update_device_state() == {'temperature':47}
    assert c.settings_update_success is False
    assert c.settings_error == 'HTTP 500'
    state.assert_awaited_once()
    device.async_update_settings.assert_awaited_once()
    device.async_update_settings.side_effect = None
    await c._async_update_device_state()
    assert c.settings_update_success is True
    assert c.settings_error is None


async def test_state_500_remains_an_error_and_does_not_request_settings(hass):
    device = SimpleNamespace(name='Boiler',async_update_settings=AsyncMock())
    c = DeviceDataUpdateCoordinator(hass,device,600,COORDINATOR,AsyncMock(side_effect=ConnectionException(500)))
    with pytest.raises(UpdateFailed,match='500'):
        await c._async_update_device_state()
    device.async_update_settings.assert_not_awaited()


async def test_optional_coordinators_do_not_refresh_core_settings(hass):
    device = SimpleNamespace(name='Boiler',async_update_settings=AsyncMock())
    c = DeviceDataUpdateCoordinator(hass,device,600,'bus_errors_coordinator',AsyncMock(return_value=[]))
    assert await c._async_update_device_state() == []
    device.async_update_settings.assert_not_awaited()
