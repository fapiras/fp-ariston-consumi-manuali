"""Manual-only, read-only consumption snapshots from the Ariston NET client.

No scheduled polling and no network calls during setup or sensor reads.
The endpoint is an undocumented historical Lydos API: it may no longer work.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import logging
import math
from typing import Any
from urllib.parse import quote

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import LEGACY_REPORT_PATH, PERIOD_KEYS, UPSTREAM_DOMAIN

_LOGGER = logging.getLogger(__name__)


def parse_period_report(payload: Any) -> dict[str, float]:
    """Parse four consumption periods (day/week/month/year) in kWh.

    Historical endpoint returns one list of numeric buckets per period.
    No lifetime cumulative meter is provided; never invent missing readings.
    """
    if not isinstance(payload, list) or len(payload) < 4:
        raise ValueError("Expected four Ariston period records")

    totals: dict[str, float] = {}
    for idx, key in enumerate(PERIOD_KEYS):
        row = payload[idx]
        if not isinstance(row, dict) or not isinstance(row.get("v"), list):
            raise ValueError(f"Invalid {key} report record")
        readings = row["v"]
        if not readings:
            raise ValueError(f"Missing {key} readings")

        valid: list[float] = []
        for number in readings:
            if number is None:
                continue
            if isinstance(number, bool) or not isinstance(number, (int, float)):
                raise ValueError(f"Non-numeric {key} reading")
            value = float(number)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"Invalid {key} reading")
            valid.append(value)
        if not valid:
            raise ValueError(f"No valid {key} readings")
        totals[key] = round(math.fsum(valid), 3)
    return totals


def concise_error(error: Exception) -> str:
    """Summarize an error without exposing account tokens or gateway IDs."""
    msg = str(error).lower()
    if "500" in msg:
        return "HTTP 500 dal cloud Ariston"
    if "429" in msg or ("rate" in msg and "limit" in msg):
        return "HTTP 429: limite richieste cloud"
    if "401" in msg or "403" in msg:
        return "Accesso al cloud non autorizzato"
    if "dns" in msg or "name resolution" in msg:
        return "Errore DNS"
    if isinstance(error, ValueError):
        return "Risposta energetica mancante o non valida"
    if isinstance(error, RuntimeError):
        return "Ariston NET non disponibile o dispositivo non supportato"
    if isinstance(error, (TimeoutError, asyncio.TimeoutError)):
        return "Timeout cloud Ariston"
    return f"Richiesta fallita ({type(error).__name__})"


class ManualEnergyCoordinator(DataUpdateCoordinator[dict[str, float | None]]):
    """Coordinator with update_interval=None; invoked only by the button."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass, _LOGGER, name=f"FP Consumi {entry.title}", update_interval=None
        )
        self.target_unique_id = entry.data["upstream_device_id"]
        suffix = hashlib.sha256(self.target_unique_id.encode()).hexdigest()[:20]
        self._store = Store(hass, 1, f"fp_ariston_consumi_{suffix}")
        self._cached: dict[str, float | None] = dict.fromkeys(PERIOD_KEYS)
        self.data = dict(self._cached)
        self.last_success_utc: str | None = None
        self.last_attempt_utc: str | None = None
        self.last_error: str | None = None
        self.state = "mai_aggiornato"
        self._press_lock = asyncio.Lock()
        self._busy = False

    @property
    def stale(self) -> bool:
        return self.state != "aggiornato"

    async def async_restore_cache(self) -> None:
        """Restore previous measurements locally without contacting Ariston."""
        try:
            stored = await self._store.async_load()
        except (ValueError, OSError) as exc:
            _LOGGER.warning("Cannot load previous Ariston report: %s", type(exc).__name__)
            return
        if not isinstance(stored, dict):
            return
        values = stored.get("readings")
        if isinstance(values, dict):
            for key in PERIOD_KEYS:
                value = values.get(key)
                if (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                    and value >= 0
                ):
                    self._cached[key] = float(value)
        if isinstance(stored.get("last_success_utc"), str):
            self.last_success_utc = stored["last_success_utc"]
        self.data = dict(self._cached)
        self.state = "dati_memorizzati" if self.last_success_utc else "mai_aggiornato"

    def _resolve_device(self):
        """Find Mauro's current client even after a reload of Ariston NET."""
        entry = next(
            (
                e for e in self.hass.config_entries.async_entries(UPSTREAM_DOMAIN)
                if e.unique_id == self.target_unique_id
            ),
            None,
        )
        if entry is None:
            raise RuntimeError("Ariston NET entry is missing")
        upstream = self.hass.data.get(UPSTREAM_DOMAIN, {})
        coordinator = (upstream.get(entry.unique_id) or {}).get("coordinator")
        if coordinator is None or coordinator.device is None:
            raise RuntimeError("Ariston NET device is not connected")
        device = coordinator.device
        from ariston_net_api import SystemType
        from ariston_net_api.const import WheType
        if device.system_type != SystemType.VELIS or device.whe_type != WheType.LydosHybrid:
            raise RuntimeError("The legacy report is only for Lydos Hybrid")
        return device, entry

    async def async_update_manually(self) -> None:
        """Reject duplicate button presses; initiate one snapshot request."""
        if self._busy:
            raise HomeAssistantError("Aggiornamento consumi già in corso")
        self._busy = True
        try:
            async with self._press_lock:
                await self.async_refresh()
                if self.last_error is not None:
                    raise HomeAssistantError(self.last_error)
        finally:
            self._busy = False

    async def _async_update_data(self) -> dict[str, float | None]:
        """Fetch on demand only and preserve last good snapshot on any error."""
        self.last_attempt_utc = datetime.now(timezone.utc).isoformat()
        self.state = "lettura_in_corso"
        self.async_update_listeners()
        try:
            device, upstream_entry = self._resolve_device()
            from ariston_net_api.const import ARISTON_API_URL

            base_url = upstream_entry.data.get("api_url_setting", ARISTON_API_URL)
            if not isinstance(base_url, str) or not base_url.startswith("https://"):
                raise ValueError("Unexpected Ariston API base URL")
            url = (
                f"{base_url.rstrip('/')}"
                + LEGACY_REPORT_PATH.format(gateway=quote(str(device.gateway), safe=""))
            )
            # Use the authenticated account client's request serialization and
            # its rate-limit handling. This is a private API of Mauro's library.
            payload = await device.api._async_get(url)  # noqa: SLF001
            fresh = parse_period_report(payload)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.last_error = concise_error(exc)
            self.state = "errore"
            _LOGGER.warning("Manual Lydos energy read failed: %s", self.last_error)
            return dict(self._cached)

        self._cached = dict(fresh)
        self.last_success_utc = datetime.now(timezone.utc).isoformat()
        self.last_error = None
        self.state = "aggiornato"
        try:
            await self._store.async_save({
                "readings": self._cached,
                "last_success_utc": self.last_success_utc,
            })
        except (ValueError, OSError) as exc:
            _LOGGER.warning("Cannot persist Ariston report: %s", type(exc).__name__)
        return dict(self._cached)
