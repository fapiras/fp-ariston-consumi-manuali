"""Manual reports: only an explicit button action can start an energy request."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import logging
import math
from urllib.parse import quote

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import API_URL_SETTING, DOMAIN, LEGACY_REPORT_PATH, PERIOD_KEYS
from .vendor.ariston_net_api.const import ARISTON_API_URL

_LOGGER = logging.getLogger(__name__)


from .energy_report import parse_period_report


def concise_error(error: Exception) -> str:
    """Expose an actionable error without copying cloud response bodies."""
    message = str(error).lower()
    if '500' in message:
        return 'HTTP 500 dal cloud Ariston'
    if '429' in message or ('rate' in message and 'limit' in message):
        return 'HTTP 429: limite richieste cloud; riprovare più tardi'
    if '401' in message or '403' in message:
        return 'Accesso al cloud non autorizzato'
    if isinstance(error, ValueError):
        return 'Risposta energetica incompleta o non valida'
    if isinstance(error, TimeoutError):
        return 'Timeout cloud Ariston'
    return f'Richiesta fallita ({type(error).__name__})'


class ManualEnergyCoordinator(DataUpdateCoordinator):
    """Cached local data; even generic HA refreshes cannot fetch energy."""

    def __init__(self, hass, entry, device):
        super().__init__(hass, _LOGGER, name=f'{DOMAIN} manual energy', update_interval=None)
        self.device = device
        self.entry = entry
        suffix = hashlib.sha256(str(device.gateway).encode()).hexdigest()[:20]
        self._store = Store(hass, 1, f'fp_ariston_consumi_{suffix}')
        self.data = dict.fromkeys(PERIOD_KEYS)
        self.last_success_utc = None
        self.last_attempt_utc = None
        self.last_error = None
        self.state = 'mai_aggiornato'
        self._busy = False

    @property
    def stale(self):
        return self.state != 'aggiornato'

    async def _async_update_data(self):
        """Generic entity updates and coordinator retries are local-only."""
        return dict(self.data)

    async def async_restore_cache(self):
        try:
            stored = await self._store.async_load()
            if not isinstance(stored, dict):
                return
            readings = stored['readings']
            valid = {key: readings[key] for key in PERIOD_KEYS}
            if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in valid.values()):
                raise ValueError('Invalid cache')
            stamp = datetime.fromisoformat(stored['last_success_utc'])
            if stamp.tzinfo is None:
                raise ValueError('Invalid timestamp')
        except (KeyError, TypeError, ValueError, OSError):
            _LOGGER.warning('Previous manual energy snapshot is missing or invalid')
            return
        self.last_success_utc = stamp.isoformat()
        self.state = 'dati_memorizzati'
        self.async_set_updated_data(valid)

    async def async_update_manually(self):
        if self._busy:
            raise HomeAssistantError('Aggiornamento consumi già in corso')
        self._busy = True
        self.last_attempt_utc = datetime.now(timezone.utc).isoformat()
        self.state = 'lettura_in_corso'
        self.async_update_listeners()
        try:
            base = self.entry.data.get(API_URL_SETTING, ARISTON_API_URL)
            if not isinstance(base, str) or not base.startswith('https://'):
                raise ValueError('Invalid API URL')
            url = base.rstrip('/') + LEGACY_REPORT_PATH.format(gateway=quote(str(self.device.gateway), safe=''))
            payload = await self.device.api._async_get(url)
            fresh = parse_period_report(payload)
        except asyncio.CancelledError:
            self.last_error = 'Lettura interrotta'
            self.state = 'errore'
            self.async_update_listeners()
            raise
        except Exception as error:
            self.last_error = concise_error(error)
            self.state = 'errore'
            self.async_update_listeners()
            raise HomeAssistantError(self.last_error) from None
        else:
            self.last_success_utc = datetime.now(timezone.utc).isoformat()
            self.last_error = None
            self.state = 'aggiornato'
            # A valid cloud snapshot is visible even if persisting it fails.
            self.async_set_updated_data(fresh)
            try:
                await self._store.async_save({'readings': fresh, 'last_success_utc': self.last_success_utc})
            except asyncio.CancelledError:
                self.state = 'aggiornato_non_salvato'
                self.last_error = 'Lettura riuscita; salvataggio locale interrotto'
                self.async_update_listeners()
                raise
            except (ValueError, OSError, HomeAssistantError):
                self.state = 'aggiornato_non_salvato'
                self.last_error = 'Lettura riuscita; salvataggio locale fallito'
                self.async_update_listeners()
        finally:
            self._busy = False
