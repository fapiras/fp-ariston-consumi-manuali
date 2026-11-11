"""User-controlled energy refresh only."""
from __future__ import annotations
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN
from .reader import ManualEnergyCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator: ManualEnergyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([RefreshEnergyButton(coordinator, entry)])

class RefreshEnergyButton(ButtonEntity):
    """Trigger one on-demand API read."""
    _attr_has_entity_name = True
    _attr_name = "Aggiorna consumi"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: ManualEnergyCoordinator, entry: ConfigEntry):
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry.unique_id}_aggiorna_consumi"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=entry.title,
            manufacturer="FP / Ariston (API cloud non ufficiale)",
            model="Lydos Hybrid: consumi su richiesta",
        )

    async def async_press(self) -> None:
        await self.coordinator.async_update_manually()
