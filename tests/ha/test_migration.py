"""Local upgrade does not need the original runtime or any cloud request."""
from unittest.mock import patch

from homeassistant.const import CONF_DEVICE, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fp_ariston_consumi import async_migrate_entry
from custom_components.fp_ariston_consumi.const import DOMAIN
from .test_setup import device_attributes


async def test_upgrade_copies_configuration_once_and_preserves_entity_id(hass):
    old = MockConfigEntry(domain='ariston_net',unique_id='a',title='Boiler A',data={
        CONF_USERNAME:'test@example.test',CONF_PASSWORD:'fake',CONF_DEVICE:device_attributes('a','Boiler A')})
    old.add_to_hass(hass)
    addon = MockConfigEntry(domain=DOMAIN,version=1,unique_id='manual_energy_a',data={'upstream_device_id':'a'})
    addon.add_to_hass(hass)
    registry = er.async_get(hass)
    sensor = registry.async_get_or_create('sensor', DOMAIN, 'manual_energy_a_month_kwh', config_entry=addon,
        suggested_object_id='old_month_reading')
    assert await async_migrate_entry(hass, addon)
    assert addon.version == 2
    assert addon.unique_id == f'{DOMAIN}:a'
    assert addon.data[CONF_DEVICE] == old.data[CONF_DEVICE]
    assert registry.async_get(sensor.entity_id).unique_id == f'{DOMAIN}:a:energy:month_kwh'
    assert old.data[CONF_PASSWORD] == 'fake'
    assert not hass.data.get('ariston_net')


async def test_upgrade_without_original_keeps_target_for_own_reauth(hass):
    addon = MockConfigEntry(domain=DOMAIN,version=1,unique_id='manual_energy_a',data={'upstream_device_id':'a'})
    addon.add_to_hass(hass)
    assert await async_migrate_entry(hass, addon)
    assert addon.version == 2
    assert addon.data == {'upstream_device_id':'a'}
    assert addon.unique_id == f'{DOMAIN}:a'
