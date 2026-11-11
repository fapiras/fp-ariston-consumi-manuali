"""Entity object for shared properties of Ariston entities."""

from __future__ import annotations

from abc import ABC
import logging

from .vendor.ariston_net_api.const import WheType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    EXTRA_STATE_ATTRIBUTE,
    EXTRA_STATE_DEVICE_METHOD,
    AristonBaseEntityDescription,
)
from .coordinator import DeviceDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class AristonEntity(CoordinatorEntity, ABC):
    """Generic Ariston entity (base class)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DeviceDataUpdateCoordinator,
        description: AristonBaseEntityDescription,
        zone: int = 0,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)

        self.device = coordinator.device
        self.entity_description: AristonBaseEntityDescription = description
        self.zone = zone

    @property
    def device_info(self) -> DeviceInfo:
        """Return device specific attributes."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.device.gateway)},
            manufacturer="Ariston",
            name=f"{self.device.name} FP",
            sw_version=self.device.firmware_version,
            model=self.model,
        )

    @property
    def model(self) -> str:
        """Return the model of the entity."""
        if self.device.whe_model_type == 0:
            if self.device.whe_type is WheType.Unknown:
                return f"{self.device.system_type.name}"
            return f"{self.device.system_type.name} {self.device.whe_type.name}"
        return f"{self.device.system_type.name} {self.device.whe_type.name} | Model {self.device.whe_model_type}"

    @property
    def extra_state_attributes(self):
        """Return the holiday end date."""
        state_attributes = {}
        if getattr(self.coordinator, '_poll_settings', False):
            state_attributes['impostazioni_aggiornate'] = self.coordinator.settings_update_success
            state_attributes['errore_lettura_impostazioni'] = self.coordinator.settings_error

        if self.entity_description.extra_states is None:
            return state_attributes or None

        for extra_state in self.entity_description.extra_states:
            device_method = extra_state.get(EXTRA_STATE_DEVICE_METHOD)

            if device_method is None:
                continue

            state_attribute = device_method(self)

            if state_attribute is None:
                continue

            state_attributes[extra_state.get(EXTRA_STATE_ATTRIBUTE)] = state_attribute

        return state_attributes

    @property
    def name(self):
        """Use the device name once and retain familiar command labels."""
        name = (self.entity_description.name or self.entity_description.key).removeprefix("Ariston NET ")
        return f"{name} {self.zone}" if self.zone else name

    @property
    def unique_id(self):
        """Identifiers are independent of display names and the old integration."""
        return f"{DOMAIN}:{self.device.gateway}:{self.entity_description.key}:{self.zone}"
