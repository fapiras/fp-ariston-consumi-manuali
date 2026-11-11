"""Period snapshots are separate from core controls and lifetime statistics."""
from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.const import UnitOfEnergy
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN, MANUAL_ENERGY, PERIOD_KEYS
from .entity import AristonEntity
from .hybrid_report import REPORT_SOURCE

SENSOR_TYPES = tuple(
    SensorEntityDescription(key=key, name=f'Consumo periodo {label}',
        device_class=SensorDeviceClass.ENERGY, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR)
    for key, label in zip(PERIOD_KEYS, ('giornaliero', 'settimanale', 'mensile', 'annuale'), strict=True)
) + (
    SensorEntityDescription(key='stato', name='Stato lettura consumi', icon='mdi:cloud-check'),
    SensorEntityDescription(key='ultimo_aggiornamento', name='Ultimo aggiornamento consumi', device_class=SensorDeviceClass.TIMESTAMP),
)


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data[DOMAIN][entry.unique_id]
    device_info = AristonEntity(runtime[COORDINATOR], SENSOR_TYPES[0]).device_info
    async_add_entities(FPManualEnergySensor(runtime[MANUAL_ENERGY], entry, d, device_info) for d in SENSOR_TYPES)


class FPManualEnergySensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, description, device_info):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f'{DOMAIN}:{coordinator.device.gateway}:energy:{description.key}'
        self._attr_device_info = device_info

    @property
    def native_value(self):
        key = self.entity_description.key
        if key in PERIOD_KEYS:
            return self.coordinator.data.get(key)
        if key == 'stato':
            return self.coordinator.state
        if self.coordinator.last_success_utc:
            return datetime.fromisoformat(self.coordinator.last_success_utc)
        return None

    @property
    def extra_state_attributes(self):
        c = self.coordinator
        key = self.entity_description.key
        is_period = key in PERIOD_KEYS
        fresh_period = (key in c.updated_periods and c.state in ('aggiornato', 'aggiornato_parzialmente'))
        return {'solo_su_richiesta': True, 'dato_non_aggiornato': not fresh_period if is_period else c.stale,
                'ultimo_tentativo_utc': c.last_attempt_utc,
                'ultimo_successo_utc': c.period_success_utc.get(key) if is_period else c.last_success_utc,
                'ultimo_successo_periodo_utc': c.period_success_utc.get(key) if is_period else None,
                'periodi_aggiornati': c.updated_periods,
                'periodi_non_disponibili': c.missing_periods,
                'ultimo_errore': c.last_error,
                'struttura_report': c.report_diagnostics,
                'fonte_report': REPORT_SOURCE,
                'dettaglio_periodo': c.period_details.get(key) if is_period else None,
                'nota': 'Totali dei periodi API; non contatore dalla prima installazione'}
