"""Cached period totals and status; reads never initiate HTTP requests."""
from __future__ import annotations
from datetime import datetime
from homeassistant.components.sensor import (
    SensorDeviceClass, SensorEntity, SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, PERIOD_KEYS
from .reader import ManualEnergyCoordinator

SENSOR_TYPES = (
    SensorEntityDescription(
        key="day_kwh", name="Consumo periodo giornaliero",
        icon="mdi:calendar-today", device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="week_kwh", name="Consumo periodo settimanale",
        icon="mdi:calendar-week", device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="month_kwh", name="Consumo periodo mensile",
        icon="mdi:calendar-month", device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="year_kwh", name="Consumo periodo annuale",
        icon="mdi:calendar", device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="stato", name="Stato lettura consumi", icon="mdi:cloud-check"
    ),
    SensorEntityDescription(
        key="ultimo_aggiornamento", name="Ultimo aggiornamento consumi",
        icon="mdi:clock-check-outline", device_class=SensorDeviceClass.TIMESTAMP,
    ),
)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    coordinator: ManualEnergyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        FPManualEnergySensor(coordinator, entry, description)
        for description in SENSOR_TYPES
    )

class FPManualEnergySensor(CoordinatorEntity[ManualEnergyCoordinator], SensorEntity):
    """Represent the most recent manual snapshot."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ManualEnergyCoordinator, entry: ConfigEntry, description):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.unique_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=entry.title,
            manufacturer="FP / Ariston (API cloud non ufficiale)",
            model="Lydos Hybrid: consumi su richiesta",
        )

    @property
    def native_value(self):
        key = self.entity_description.key
        if key in PERIOD_KEYS:
            return (self.coordinator.data or {}).get(key)
        if key == "stato":
            return self.coordinator.state
        if key == "ultimo_aggiornamento" and self.coordinator.last_success_utc:
            return datetime.fromisoformat(self.coordinator.last_success_utc)
        return None

    @property
    def extra_state_attributes(self):
        return {
            "solo_su_richiesta": True,
            "dato_non_aggiornato": self.coordinator.stale,
            "ultimo_tentativo_utc": self.coordinator.last_attempt_utc,
            "ultimo_successo_utc": self.coordinator.last_success_utc,
            "ultimo_errore": self.coordinator.last_error,
            "fonte": "Ariston cloud (API Lydos non ufficiale)",
            "nota": "Totali dei periodi restituiti dall'API, non contatore dalla prima installazione",
        }
