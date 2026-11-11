"""Independent login, two devices, duplicate detection and reauthentication."""
from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_DEVICE, CONF_USERNAME, CONF_PASSWORD
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fp_ariston_consumi.const import DOMAIN
from custom_components.fp_ariston_consumi.vendor.ariston_net_api import Ariston
from custom_components.fp_ariston_consumi.vendor.ariston_net_api.const import DeviceAttribute
from .test_setup import device_attributes


async def test_login_selects_one_of_two_and_prevents_duplicate(hass):
    with patch.object(Ariston, 'async_connect', new=AsyncMock(return_value=True)), patch.object(
        Ariston, 'async_discover', new=AsyncMock(return_value=[device_attributes('a','Boiler A'),device_attributes('b','Boiler B')])
    ), patch('custom_components.fp_ariston_consumi.async_setup_entry', return_value=True):
        form = await hass.config_entries.flow.async_init(DOMAIN, context={'source':config_entries.SOURCE_USER})
        form = await hass.config_entries.flow.async_configure(form['flow_id'], {CONF_USERNAME:'test@example.test',CONF_PASSWORD:'fake'})
        assert form['step_id'] == 'select'
        result = await hass.config_entries.flow.async_configure(form['flow_id'], {'select_device':'b'})
        assert result['type'] == 'create_entry'
        assert result['result'].unique_id == f'{DOMAIN}:b'
        assert result['data'][CONF_DEVICE][DeviceAttribute.GW] == 'b'
        form = await hass.config_entries.flow.async_init(DOMAIN, context={'source':config_entries.SOURCE_USER})
        form = await hass.config_entries.flow.async_configure(form['flow_id'], {CONF_USERNAME:'test@example.test',CONF_PASSWORD:'fake'})
        duplicate = await hass.config_entries.flow.async_configure(form['flow_id'], {'select_device':'b'})
        assert duplicate['reason'] == 'already_configured'


async def test_cloud_error_is_reported_without_secret(hass):
    with patch.object(Ariston, 'async_connect', new=AsyncMock(side_effect=TimeoutError('secret'))):
        form = await hass.config_entries.flow.async_init(DOMAIN, context={'source':config_entries.SOURCE_USER})
        form = await hass.config_entries.flow.async_configure(form['flow_id'], {CONF_USERNAME:'test@example.test',CONF_PASSWORD:'fake'})
        assert form['errors'] == {'base':'cannot_connect'}


async def test_reauth_cannot_replace_one_boiler_with_the_other(hass):
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id=f'{DOMAIN}:a', data={'upstream_device_id':'a'})
    entry.add_to_hass(hass)
    with patch.object(Ariston, 'async_connect', new=AsyncMock(return_value=True)), patch.object(
        Ariston, 'async_discover', new=AsyncMock(return_value=[device_attributes('a','Boiler A'),device_attributes('b','Boiler B')])
    ), patch('custom_components.fp_ariston_consumi.async_setup_entry', return_value=True):
        form = await hass.config_entries.flow.async_init(DOMAIN, context={'source':config_entries.SOURCE_REAUTH,'entry_id':entry.entry_id}, data=entry.data)
        form = await hass.config_entries.flow.async_configure(form['flow_id'], {CONF_USERNAME:'test@example.test',CONF_PASSWORD:'fake'})
        wrong = await hass.config_entries.flow.async_configure(form['flow_id'], {'select_device':'b'})
        assert wrong['errors'] == {'base':'wrong_device'}
        result = await hass.config_entries.flow.async_configure(form['flow_id'], {'select_device':'a'})
        assert result['reason'] == 'reauth_successful'
        assert entry.data[CONF_DEVICE][DeviceAttribute.GW] == 'a'
