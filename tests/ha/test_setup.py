"""Load actual HA platforms and preserve all dashboard control types."""
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import timedelta

from homeassistant.const import CONF_DEVICE, CONF_PASSWORD, CONF_USERNAME
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.fp_ariston_consumi.const import DOMAIN, COORDINATOR, MANUAL_ENERGY
from custom_components.fp_ariston_consumi.vendor.ariston_net_api import Ariston
from custom_components.fp_ariston_consumi.vendor.ariston_net_api.const import (
    DeviceAttribute, VelisDeviceAttribute, SystemType, WheType, DeviceFeatures, SeDeviceSettings,
)
from custom_components.fp_ariston_consumi.vendor.ariston_net_api.lydos_hybrid_device import AristonLydosHybridDevice


def device_attributes(gateway='fake-gw', name='Boiler A'):
    return {DeviceAttribute.GW: gateway, DeviceAttribute.NAME: name, DeviceAttribute.SN: 'fake-serial',
            DeviceAttribute.SYS: SystemType.VELIS.value, VelisDeviceAttribute.WHE_TYPE: WheType.LydosHybrid.value}


def fake_device(gateway='fake-gw', name='Boiler A'):
    api = MagicMock()
    api.async_get_features_for_device = AsyncMock(return_value={DeviceFeatures.HAS_METERING:True})
    api.async_get_velis_plant_data = AsyncMock(return_value={
        'on':True, 'temp':48.0, 'reqTemp':50.0, 'procReqTemp':50.0,
        'avShw':3, 'heatReq':False, 'antiLeg':False, 'mode':2,
    })
    settings = {getattr(SeDeviceSettings, key): 1 for key in dir(SeDeviceSettings) if key.startswith('SE_')}
    settings.update({SeDeviceSettings.SE_ANTI_COOLING_TEMPERATURE_MIN:5,
                     SeDeviceSettings.SE_ANTI_COOLING_TEMPERATURE_MAX:30,
                     SeDeviceSettings.SE_MAX_SETPOINT_TEMPERATURE:75,
                     SeDeviceSettings.SE_MAX_SETPOINT_TEMPERATURE_MIN:40,
                     SeDeviceSettings.SE_MAX_SETPOINT_TEMPERATURE_MAX:80,
                     SeDeviceSettings.SE_ANTI_COOLING_TEMPERATURE:10,
                     SeDeviceSettings.SE_MAX_GREEN_SETPOINT_TEMPERATURE:55})
    api.async_get_velis_plant_settings = AsyncMock(return_value=settings)
    api._async_get = AsyncMock(return_value=[{'v':[1]}]*4)
    api.async_get_consumptions_sequences = AsyncMock()
    api.async_get_energy_account = AsyncMock()
    api.async_set_velis_power = AsyncMock()
    api.async_set_lydos_temperature = AsyncMock()
    api.async_set_lydos_mode = AsyncMock()
    api.async_set_velis_plant_setting = AsyncMock()
    return AristonLydosHybridDevice(api, device_attributes(gateway, name))


async def test_all_platforms_setup_without_old_integration_or_energy_polling(hass):
    device = fake_device()
    entry = MockConfigEntry(domain=DOMAIN, unique_id=f'{DOMAIN}:fake-gw', version=2,
        title='Boiler A', data={CONF_USERNAME:'test@example.test', CONF_PASSWORD:'fake', CONF_DEVICE:device_attributes()},
        options={'enable_energy':True, 'energy_scan_interval':1})
    entry.add_to_hass(hass)
    with patch.object(Ariston, 'async_connect', new=AsyncMock(return_value=True)), patch.object(Ariston, 'async_hello', new=AsyncMock(return_value=device)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert 'ariston_net' not in hass.data
        states = hass.states.async_all()
        ids = {s.entity_id for s in states}
        expected = {
            'sensor.boiler_a_fp_current_temperature', 'sensor.boiler_a_fp_proc_req_temp',
            'sensor.boiler_a_fp_average_showers', 'water_heater.boiler_a_fp',
            'select.boiler_a_fp_operation_mode', 'binary_sensor.boiler_a_fp_is_heating',
            'binary_sensor.boiler_a_fp_anti_legionella_cycle', 'switch.boiler_a_fp_power',
            'switch.boiler_a_fp_night_mode', 'switch.boiler_a_fp_permanent_boost',
            'switch.boiler_a_fp_anti_legionella', 'switch.boiler_a_fp_anti_cooling',
            'number.boiler_a_fp_anti_cooling_temperature', 'button.boiler_a_fp_aggiorna_consumi',
        }
        assert expected <= ids, expected - ids
        assert hass.states.get('sensor.boiler_a_fp_current_temperature').state == '48.0'
        registry = er.async_get(hass)
        entries = er.async_entries_for_config_entry(registry, entry.entry_id)
        assert all(e.unique_id.startswith(DOMAIN + ':fake-gw:') for e in entries)
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(hours=1))
        await hass.async_block_till_done()
        device.api._async_get.assert_not_awaited()
        device.api.async_get_consumptions_sequences.assert_not_awaited()
        device.api.async_get_energy_account.assert_not_awaited()
        await hass.services.async_call('button', 'press', {'entity_id':'button.boiler_a_fp_aggiorna_consumi'}, blocking=True)
        device.api._async_get.assert_awaited_once()
        await hass.config_entries.async_unload(entry.entry_id)


async def test_core_write_commands_use_bundled_client_and_no_energy(hass):
    device = fake_device()
    from custom_components.fp_ariston_consumi.coordinator import DeviceDataUpdateCoordinator
    from custom_components.fp_ariston_consumi.const import ARISTON_WATER_HEATER_TYPES, ARISTON_SELECT_TYPES, ARISTON_SWITCH_TYPES, ARISTON_NUMBER_TYPES
    from custom_components.fp_ariston_consumi.water_heater import AristonWaterHeater
    from custom_components.fp_ariston_consumi.switch import AristonSwitch
    from custom_components.fp_ariston_consumi.select import AristonSelect
    from custom_components.fp_ariston_consumi.number import AristonNumber
    await device.async_get_features()
    await device.async_update_state()
    coordinator = DeviceDataUpdateCoordinator(hass, device, 600, COORDINATOR, device.async_update_state)
    descriptions = [d for d in ARISTON_WATER_HEATER_TYPES if device.are_device_features_available(d.device_features, d.system_types, d.whe_types)]
    heater = AristonWaterHeater(coordinator, descriptions[0])
    await heater.async_set_temperature(temperature=52)
    device.api.async_set_lydos_temperature.assert_awaited_once_with('fake-gw',52)
    await heater.async_set_operation_mode('GREEN')
    assert device.water_heater_current_mode_text == 'GREEN'
    await heater.async_set_operation_mode('BOOST')
    assert device.water_heater_current_mode_text == 'BOOST'
    for description in ARISTON_SWITCH_TYPES:
        if device.are_device_features_available(description.device_features, description.system_types, description.whe_types):
            switch = AristonSwitch(coordinator, description)
            await switch.async_turn_off()
            await switch.async_turn_on()
    for description in ARISTON_NUMBER_TYPES:
        if description.name.endswith('anti cooling temperature'):
            await AristonNumber(coordinator, description).async_set_native_value(12)
    device.api._async_get.assert_not_awaited()
    device.api.async_get_consumptions_sequences.assert_not_awaited()


async def test_two_boilers_share_one_login_and_unload_independently(hass):
    a, b = fake_device('a', 'Boiler A'), fake_device('b', 'Boiler B')
    entries = []
    for device in (a,b):
        entry = MockConfigEntry(domain=DOMAIN, unique_id=f'{DOMAIN}:{device.gateway}', version=2,
            title=device.name, data={CONF_USERNAME:'test@example.test',CONF_PASSWORD:'fake',CONF_DEVICE:device.attributes})
        entry.add_to_hass(hass)
        entries.append(entry)
    async def hello(gateway, is_metric):
        return {'a':a,'b':b}[gateway]
    with patch.object(Ariston,'async_connect',new=AsyncMock(return_value=True)) as login, patch.object(
        Ariston,'async_hello',side_effect=hello
    ):
        # Initial domain setup also loads its other configured entries.
        assert await hass.config_entries.async_setup(entries[0].entry_id)
        await hass.async_block_till_done()
        assert all(entry.state is ConfigEntryState.LOADED for entry in entries)
        login.assert_awaited_once()
        assert hass.states.get('switch.boiler_a_fp_power') is not None
        assert hass.states.get('switch.boiler_b_fp_power') is not None
        assert hass.states.get('button.boiler_a_fp_aggiorna_consumi') is not None
        assert hass.states.get('button.boiler_b_fp_aggiorna_consumi') is not None
        assert await hass.config_entries.async_unload(entries[0].entry_id)
        assert entries[1].unique_id in hass.data[DOMAIN]
        assert hass.states.get('switch.boiler_b_fp_power').state == 'on'
        a.api._async_get.assert_not_awaited()
        b.api._async_get.assert_not_awaited()
        assert await hass.config_entries.async_unload(entries[1].entry_id)
