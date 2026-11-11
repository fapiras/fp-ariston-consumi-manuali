"""Explicit manual consumption action."""
from homeassistant.components.button import ButtonEntity

from .const import COORDINATOR, DOMAIN, MANUAL_ENERGY
from .entity import AristonEntity
from .manual_sensor import SENSOR_TYPES


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data[DOMAIN][entry.unique_id]
    device_info = AristonEntity(runtime[COORDINATOR], SENSOR_TYPES[0]).device_info
    async_add_entities([RefreshEnergyButton(runtime[MANUAL_ENERGY], device_info)])


class RefreshEnergyButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = 'Aggiorna consumi'
    _attr_icon = 'mdi:refresh'

    def __init__(self, coordinator, device_info):
        self.coordinator = coordinator
        self._attr_unique_id = f'{DOMAIN}:{coordinator.device.gateway}:energy:aggiorna_consumi'
        self._attr_device_info = device_info

    async def async_press(self):
        await self.coordinator.async_update_manually()
