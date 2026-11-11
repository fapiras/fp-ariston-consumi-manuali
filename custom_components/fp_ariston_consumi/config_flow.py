"""Select an existing Ariston NET entry for manual energy readings."""
from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, UPSTREAM_DOMAIN

class FPAristonConsumiFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure one report reader per existing Lydos Hybrid."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        entries = [e for e in self.hass.config_entries.async_entries(UPSTREAM_DOMAIN) if e.unique_id]
        choices = {e.unique_id: e.title for e in entries}
        if not choices:
            return self.async_abort(reason="ariston_missing")
        schema = vol.Schema({vol.Required("device"): vol.In(choices)})
        if user_input is not None:
            selected = user_input["device"]
            if selected not in choices:
                return self.async_show_form(step_id="user", data_schema=schema,
                                            errors={"device": "invalid_device"})
            await self.async_set_unique_id(f"manual_energy_{selected}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Consumi {choices[selected]}", data={"upstream_device_id": selected}
            )
        return self.async_show_form(step_id="user", data_schema=schema)
