"""Period snapshots are separate from core controls and lifetime statistics."""
from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.const import UnitOfEnergy
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN, MANUAL_ENERGY, PERIOD_KEYS
from .entity import AristonEntity
from .hybrid_report import REPORT_SOURCE
from .calendar_report import month_label

COMPONENT_KEYS = {f'{component}_{key}':(key,component)
                  for key in PERIOD_KEYS for component in ('pdc','resistenza')}

SENSOR_TYPES = tuple(
    SensorEntityDescription(key=key, name=f'Consumo periodo {label}',
        device_class=SensorDeviceClass.ENERGY, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR)
    for key, label in zip(PERIOD_KEYS, ('giornaliero', 'settimanale', 'mensile', 'annuale'), strict=True)
) + (
    SensorEntityDescription(key='stato', name='Stato lettura consumi', icon='mdi:cloud-check'),
    SensorEntityDescription(key='ultimo_aggiornamento', name='Ultimo aggiornamento consumi', device_class=SensorDeviceClass.TIMESTAMP),
)

SENSOR_TYPES += tuple(
    SensorEntityDescription(key=f'{component}_{key}', name=f'Consumo {label} periodo {period_label}',
        device_class=SensorDeviceClass.ENERGY, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon='mdi:heat-pump' if component=='pdc' else 'mdi:heating-coil')
    for key,period_label in zip(PERIOD_KEYS,('giornaliero','settimanale','mensile','annuale'),strict=True)
    for component,label in (('pdc','PDC'),('resistenza','resistenza'))
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
            return self.coordinator.value_for(key)
        if key in COMPONENT_KEYS:
            period, component = COMPONENT_KEYS[key]
            return self.coordinator.value_for(period,component)
        if key == 'stato':
            return self.coordinator.state
        if self.coordinator.last_success_utc:
            return datetime.fromisoformat(self.coordinator.last_success_utc)
        return None

    @property
    def extra_state_attributes(self):
        c = self.coordinator
        key = self.entity_description.key
        key = COMPONENT_KEYS.get(key,(key,None))[0]
        is_period = key in PERIOD_KEYS
        fresh_period = (key in c.updated_periods and c.state in ('aggiornato', 'aggiornato_parzialmente'))
        period_stamp = c.period_success_utc.get(key)
        if key=='month_kwh':
            period_stamp = c.months.get(c.selected_month,{}).get('last_success_utc')
            fresh_period = bool(period_stamp and period_stamp==c.last_success_utc and c.state in ('aggiornato','aggiornato_parzialmente'))
        return {'solo_su_richiesta': True, 'dato_non_aggiornato': not fresh_period if is_period else c.stale,
                'ultimo_tentativo_utc': c.last_attempt_utc,
                'ultimo_successo_utc': period_stamp if is_period else c.last_success_utc,
                'ultimo_successo_periodo_utc': period_stamp if is_period else None,
                'periodi_aggiornati': c.updated_periods,
                'periodi_non_disponibili': c.missing_periods,
                'ultimo_errore': c.last_error,
                'struttura_report': c.report_diagnostics,
                'fonte_report': REPORT_SOURCE,
                'dettaglio_periodo': c.period_details.get(key) if is_period else None,
                'mese_selezionato': month_label(c.selected_month) if c.selected_month else None,
                'mese_parziale': c.months.get(c.selected_month,{}).get('parziale') if key=='month_kwh' else None,
                'anno_riferimento': c.reference_year if key=='year_kwh' else None,
                'dettaglio_mese_selezionato': c.months.get(c.selected_month) if key=='month_kwh' else None,
                'nota': 'Mensile: mese selezionato; annuale: dati disponibili nell’anno corrente; letture manuali'}
