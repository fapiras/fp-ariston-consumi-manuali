"""Month selection reads cached data only; never requests energy from Ariston."""
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .calendar_report import month_label
from .const import COORDINATOR, DOMAIN, MANUAL_ENERGY
from .entity import AristonEntity
from .manual_sensor import SENSOR_TYPES


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data[DOMAIN][entry.unique_id]
    info = AristonEntity(runtime[COORDINATOR],SENSOR_TYPES[0]).device_info
    async_add_entities([MonthSelect(runtime[MANUAL_ENERGY],info)])


class MonthSelect(CoordinatorEntity, SelectEntity):
    _attr_has_entity_name = True
    _attr_name = 'Mese consumi'
    _attr_icon = 'mdi:calendar-month'

    def __init__(self, coordinator, info):
        super().__init__(coordinator)
        self._attr_unique_id = f'{DOMAIN}:{coordinator.device.gateway}:energy:month_select'
        self._attr_device_info = info

    @property
    def available(self):
        return bool(self.coordinator.months)

    @property
    def options(self):
        return [month_label(k) for k in sorted(self.coordinator.months,reverse=True)]

    @property
    def current_option(self):
        key = self.coordinator.selected_month
        return month_label(key) if key in self.coordinator.months else None

    async def async_select_option(self, option):
        key = next((k for k in self.coordinator.months if month_label(k)==option),None)
        await self.coordinator.async_select_month(key)
