"""Manual reports: only an explicit button action can start an energy request."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import logging
import math
from urllib.parse import quote
from zoneinfo import ZoneInfo

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import API_URL_SETTING, DOMAIN, PERIOD_KEYS
from .vendor.ariston_net_api.const import ARISTON_API_URL

_LOGGER = logging.getLogger(__name__)


from .energy_report import ReportValidationError, report_structure
from .hybrid_report import HYBRID_REPORT_PATH, REPORT_SOURCE, parse_hybrid_report
from .calendar_report import calendar_months


def concise_error(error: Exception) -> str:
    """Expose an actionable error without copying cloud response bodies."""
    message = str(error).lower()
    if isinstance(error, ReportValidationError):
        return str(error)
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
        self.report_diagnostics = None
        self.updated_periods = []
        self.missing_periods = []
        self.period_success_utc = dict.fromkeys(PERIOD_KEYS)
        self.period_details = {}
        self.component_values = {key:{'pdc':None,'resistenza':None} for key in PERIOD_KEYS}
        self.months = {}
        self.selected_month = None
        self.calendar_capture_utc = None
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
            # Generic Dhw reports in beta.1..3 may contain unrelated zeroes.
            # Never restore them as validated Hybrid electricity consumption.
            if stored.get('report_source') != REPORT_SOURCE:
                return
            readings = stored['readings']
            valid = {key: readings[key] for key in PERIOD_KEYS}
            if any(v is not None and (type(v) not in (int, float) or not math.isfinite(v) or v < 0) for v in valid.values()):
                raise ValueError('Invalid cache')
            if all(v is None for v in valid.values()):
                raise ValueError('Empty cache')
            stamp = datetime.fromisoformat(stored['last_success_utc'])
            if stamp.tzinfo is None:
                raise ValueError('Invalid timestamp')
            saved_periods = stored.get('period_success_utc')
            period_times = dict.fromkeys(PERIOD_KEYS)
            for key, value in valid.items():
                if value is None:
                    continue
                # Older complete snapshots had one timestamp for all periods.
                period_stamp = datetime.fromisoformat(saved_periods[key]) if isinstance(saved_periods, dict) else stamp
                if period_stamp.tzinfo is None:
                    raise ValueError('Invalid period timestamp')
                period_times[key] = period_stamp.isoformat()
        except (KeyError, TypeError, ValueError, OSError):
            _LOGGER.warning('Previous manual energy snapshot is missing or invalid')
            return
        self.last_success_utc = stamp.isoformat()
        self.period_success_utc = period_times
        self.months = stored.get('calendar_months', {})
        self.selected_month = stored.get('selected_month')
        if self.selected_month not in self.months:
            self.selected_month = max(self.months,default=None)
        self.component_values = stored.get('component_values', self.component_values)
        self.calendar_capture_utc = stored.get('calendar_capture_utc')
        self.state = 'dati_memorizzati'
        self.async_set_updated_data(valid)

    def value_for(self, period, component='totale'):
        """One source for totals, separated channels and the selected month."""
        if period == 'month_kwh':
            return self.months.get(self.selected_month,{}).get(component)
        if period == 'year_kwh':
            if not self.calendar_capture_utc:
                return None
            year = self.reference_year
            values = [v[component] for key,v in self.months.items() if key.startswith(str(year)+'-')]
            return round(math.fsum(values),3) if values else None
        if component == 'totale':
            return self.data.get(period)
        return self.component_values.get(period,{}).get(component)

    @property
    def reference_year(self):
        if not self.calendar_capture_utc:
            return None
        return datetime.fromisoformat(self.calendar_capture_utc).astimezone(
            ZoneInfo(self.hass.config.time_zone)).year

    async def async_save_snapshot(self):
        await self._store.async_save({
            'readings':self.data, 'last_success_utc':self.last_success_utc,
            'period_success_utc':self.period_success_utc, 'report_source':REPORT_SOURCE,
            'component_values':self.component_values, 'calendar_months':self.months,
            'selected_month':self.selected_month, 'calendar_capture_utc':self.calendar_capture_utc,
        })

    async def async_select_month(self, key):
        if key not in self.months:
            raise HomeAssistantError('Mese non disponibile')
        self.selected_month = key
        self.async_update_listeners()
        try:
            await self.async_save_snapshot()
        except (ValueError,OSError,HomeAssistantError):
            raise HomeAssistantError('Mese selezionato; salvataggio locale fallito') from None

    async def async_update_manually(self):
        if self._busy:
            raise HomeAssistantError('Aggiornamento consumi già in corso')
        self._busy = True
        self.updated_periods = []
        self.missing_periods = []
        self.report_diagnostics = None
        self.last_attempt_utc = datetime.now(timezone.utc).isoformat()
        self.state = 'lettura_in_corso'
        self.async_update_listeners()
        try:
            base = self.entry.data.get(API_URL_SETTING, ARISTON_API_URL)
            if not isinstance(base, str) or not base.startswith('https://'):
                raise ValueError('Invalid API URL')
            url = base.rstrip('/') + HYBRID_REPORT_PATH.format(gateway=quote(str(self.device.gateway), safe=''))
            payload = await self.device.api._async_get(url)
            self.report_diagnostics = report_structure(payload)
            fresh, self.period_details = parse_hybrid_report(payload)
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
            self.updated_periods = [key for key, value in fresh.items() if value is not None]
            self.missing_periods = [key for key, value in fresh.items() if value is None]
            merged = dict(self.data)
            for key in self.updated_periods:
                merged[key] = fresh[key]
                self.period_success_utc[key] = self.last_success_utc
                detail = self.period_details[key]
                self.component_values[key] = {
                    'pdc':round(math.fsum(detail['pompa_di_calore_kwh']),3),
                    'resistenza':round(math.fsum(detail['resistenza_kwh']),3),
                }
            current_months = calendar_months(self.period_details,
                datetime.fromisoformat(self.last_success_utc),self.hass.config.time_zone)
            for record in current_months.values():
                record['last_success_utc'] = self.last_success_utc
            self.months.update(current_months)
            self.calendar_capture_utc = self.last_success_utc
            if self.selected_month not in self.months:
                self.selected_month = max(self.months,default=None)
            self.state = 'aggiornato_parzialmente' if self.missing_periods else 'aggiornato'
            # A valid cloud snapshot is visible even if persisting it fails.
            self.async_set_updated_data(merged)
            try:
                await self.async_save_snapshot()
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
