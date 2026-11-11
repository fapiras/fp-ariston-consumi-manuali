"""Own Ariston login and device selection; no other integration is required."""
from __future__ import annotations

import voluptuous as vol
from aiohttp import ClientError
from homeassistant import config_entries
from homeassistant.const import CONF_DEVICE, CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import callback

from .vendor.ariston_net_api import Ariston, DeviceAttribute, SystemType
from .vendor.ariston_net_api.const import ARISTON_API_URL, ARISTON_USER_AGENT, VelisDeviceAttribute, WheType
from .vendor.ariston_net_api.ariston_api import ConnectionException
from .const import API_URL_SETTING, API_USER_AGENT, DOMAIN, DEFAULT_SCAN_INTERVAL_SECONDS, MIN_SCAN_INTERVAL_SECONDS

SCHEMA = vol.Schema({vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str})


class FPAristonConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure each Lydos with this integration's own account client."""

    VERSION = 2

    def __init__(self):
        self.credentials = {}
        self.devices = {}

    async def async_step_reauth(self, entry_data):
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.credentials = {
                CONF_USERNAME: user_input[CONF_USERNAME].strip(),
                CONF_PASSWORD: user_input[CONF_PASSWORD],
                API_URL_SETTING: ARISTON_API_URL,
                API_USER_AGENT: ARISTON_USER_AGENT,
            }
            client = Ariston()
            try:
                ok = await client.async_connect(
                    self.credentials[CONF_USERNAME], self.credentials[CONF_PASSWORD]
                )
                if not ok:
                    errors['base'] = 'invalid_auth'
                else:
                    discovered = await client.async_discover()
                    self.devices = {
                        str(d[DeviceAttribute.GW]): d for d in discovered
                        if d.get(DeviceAttribute.SYS) == SystemType.VELIS.value
                        and d.get(VelisDeviceAttribute.WHE_TYPE) == WheType.LydosHybrid.value
                    }
                    if not self.devices:
                        errors['base'] = 'no_devices'
                    else:
                        return await self.async_step_select()
            except (ClientError, ConnectionException, TimeoutError):
                errors['base'] = 'cannot_connect'
            except Exception:
                errors['base'] = 'unknown'
        return self.async_show_form(step_id='user', data_schema=SCHEMA, errors=errors)

    async def async_step_select(self, user_input=None):
        errors = {}
        if user_input is not None:
            gateway = user_input['select_device']
            if gateway not in self.devices:
                errors['base'] = 'invalid_device'
            else:
                device = self.devices[gateway]
                if self.source == config_entries.SOURCE_REAUTH:
                    entry = self._get_reauth_entry()
                    expected = entry.data.get(CONF_DEVICE, {}).get(DeviceAttribute.GW)
                    expected = expected or entry.data.get('upstream_device_id')
                    if expected and str(expected) != gateway:
                        errors['base'] = 'wrong_device'
                    else:
                        return self.async_update_reload_and_abort(
                            entry, data_updates={**self.credentials, CONF_DEVICE: device},
                        )
                else:
                    await self.async_set_unique_id(f'{DOMAIN}:{gateway}')
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=device[DeviceAttribute.NAME],
                        data={**self.credentials, CONF_DEVICE: device},
                    )
        choices = {gw: d[DeviceAttribute.NAME] for gw, d in self.devices.items()}
        return self.async_show_form(
            step_id='select', data_schema=vol.Schema({vol.Required('select_device'): vol.In(choices)}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return FPAristonOptionsFlow()


class FPAristonOptionsFlow(config_entries.OptionsFlow):
    """Only core state polling can be configured, never energy polling."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title='', data=user_input)
        return self.async_show_form(step_id='init', data_schema=vol.Schema({
            vol.Optional(CONF_SCAN_INTERVAL, default=self.config_entry.options.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS
            )): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL_SECONDS)),
        }))
