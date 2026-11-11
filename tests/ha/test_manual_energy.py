"""Verify manual-only behavior, cache and error isolation in real HA."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.fp_ariston_consumi.reader import ManualEnergyCoordinator


def make_coordinator(hass, gateway='test-gateway'):
    entry = SimpleNamespace(data={})
    device = SimpleNamespace(gateway=gateway, api=SimpleNamespace(_async_get=AsyncMock(return_value=[{'v':[1,2]}]*4)))
    return ManualEnergyCoordinator(hass, entry, device)


async def test_startup_listener_refresh_never_reads_energy(hass):
    c = make_coordinator(hass)
    c._store = SimpleNamespace(async_load=AsyncMock(return_value=None), async_save=AsyncMock())
    await c.async_restore_cache()
    unsub = c.async_add_listener(lambda: None)
    await c.async_refresh()
    await c.async_request_refresh()
    assert c.update_interval is None
    assert all(v is None for v in c.data.values())
    c.device.api._async_get.assert_not_awaited()
    unsub()


async def test_button_fetches_once_and_restart_restores_without_cloud(hass):
    c = make_coordinator(hass)
    await c.async_update_manually()
    c.device.api._async_get.assert_awaited_once()
    assert c.data['month_kwh'] == 3
    assert c.state == 'aggiornato'
    assert '/api/v2/velis/reports/test-gateway?usages=Dhw&appId=' in c.device.api._async_get.call_args.args[0]
    restored = make_coordinator(hass)
    await restored.async_restore_cache()
    assert restored.data == c.data
    assert restored.last_success_utc == c.last_success_utc
    assert restored.stale
    restored.device.api._async_get.assert_not_awaited()


@pytest.mark.parametrize('error', [RuntimeError('HTTP 500 secret-token'), RuntimeError('429 secret-token'), TimeoutError(), ValueError()])
async def test_failure_keeps_last_valid_snapshot_and_timestamp(hass, error):
    c = make_coordinator(hass)
    await c.async_update_manually()
    previous, stamp = dict(c.data), c.last_success_utc
    c.device.api._async_get.side_effect = error
    with pytest.raises(HomeAssistantError, match='.') as raised:
        await c.async_update_manually()
    assert 'secret-token' not in str(raised.value)
    assert c.data == previous
    assert c.last_success_utc == stamp
    assert c.state == 'errore'
    await c.async_refresh()
    assert c.device.api._async_get.await_count == 2


async def test_two_devices_have_independent_caches(hass):
    a, b = make_coordinator(hass, 'a'), make_coordinator(hass, 'b')
    await a.async_update_manually()
    await b.async_restore_cache()
    assert a.data['day_kwh'] == 3
    assert b.data['day_kwh'] is None
    b.device.api._async_get.assert_not_awaited()


async def test_duplicate_press_and_cancellation_leave_coordinator_usable(hass):
    c = make_coordinator(hass)
    started, finish = asyncio.Event(), asyncio.Event()
    async def delayed(*args):
        started.set()
        await finish.wait()
        return [{'v':[1]}]*4
    c.device.api._async_get.side_effect = delayed
    task = asyncio.create_task(c.async_update_manually())
    await started.wait()
    with pytest.raises(HomeAssistantError, match='già in corso'):
        await c.async_update_manually()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert c.state == 'errore'
    assert c._busy is False
    c.device.api._async_get.side_effect = None
    await c.async_update_manually()
    assert c.state == 'aggiornato'


async def test_corrupt_cache_does_not_contact_cloud(hass):
    c = make_coordinator(hass)
    c._store = SimpleNamespace(async_load=AsyncMock(return_value={'readings':{}, 'last_success_utc':'not-a-date'}))
    await c.async_restore_cache()
    assert c.last_success_utc is None
    c.device.api._async_get.assert_not_awaited()


async def test_empty_response_is_distinguished_without_overwriting_cache(hass):
    c = make_coordinator(hass)
    await c.async_update_manually()
    previous = dict(c.data)
    c.device.api._async_get.return_value = None
    with pytest.raises(HomeAssistantError, match='Nessun report energetico restituito'):
        await c.async_update_manually()
    assert c.data == previous
    assert c.report_diagnostics == {'tipo':'NoneType'}


async def test_user_report_shape_updates_month_year_and_restores_partial_cache(hass):
    c = make_coordinator(hass)
    c.device.api._async_get.return_value = [{'v':[]}, {'v':[]}, {'v':[1]*15}, {'v':[2]*12}]
    await c.async_update_manually()
    assert c.state == 'aggiornato_parzialmente'
    assert c.data == {'day_kwh':None, 'week_kwh':None, 'month_kwh':15, 'year_kwh':24}
    assert c.updated_periods == ['month_kwh','year_kwh']
    assert c.missing_periods == ['day_kwh','week_kwh']
    assert c.period_success_utc['day_kwh'] is None
    assert c.period_success_utc['month_kwh'] == c.last_success_utc
    restored = make_coordinator(hass)
    await restored.async_restore_cache()
    assert restored.data == c.data
    assert restored.period_success_utc == c.period_success_utc
    assert restored.updated_periods == []
    restored.device.api._async_get.assert_not_awaited()


async def test_partial_read_preserves_missing_period_values_dates_and_marks_stale(hass):
    from custom_components.fp_ariston_consumi.manual_sensor import FPManualEnergySensor, SENSOR_TYPES
    c = make_coordinator(hass)
    await c.async_update_manually()
    old_stamp = c.period_success_utc['day_kwh']
    c.device.api._async_get.return_value = [{'v':[]}, {'v':[]}, {'v':[8]}, {'v':[90]}]
    await c.async_update_manually()
    assert c.data == {'day_kwh':3, 'week_kwh':3, 'month_kwh':8, 'year_kwh':90}
    day = FPManualEnergySensor(c, None, SENSOR_TYPES[0], None)
    month = FPManualEnergySensor(c, None, SENSOR_TYPES[2], None)
    assert day.extra_state_attributes['dato_non_aggiornato'] is True
    assert day.extra_state_attributes['ultimo_successo_utc'] == old_stamp
    assert month.extra_state_attributes['dato_non_aggiornato'] is False
    assert month.extra_state_attributes['ultimo_successo_utc'] == c.last_success_utc


async def test_all_empty_reports_keep_previous_snapshot_and_dates(hass):
    c = make_coordinator(hass)
    await c.async_update_manually()
    previous, dates, stamp = dict(c.data), dict(c.period_success_utc), c.last_success_utc
    c.device.api._async_get.return_value = [{'v':[]}]*4
    with pytest.raises(HomeAssistantError, match='tutti gli elenchi sono vuoti'):
        await c.async_update_manually()
    assert c.data == previous
    assert c.period_success_utc == dates
    assert c.last_success_utc == stamp
    assert c.updated_periods == []


async def test_storage_failure_keeps_valid_reading_visible(hass):
    c = make_coordinator(hass)
    c._store = SimpleNamespace(async_save=AsyncMock(side_effect=OSError('disk full')))
    await c.async_update_manually()
    assert c.data['day_kwh'] == 3
    assert c.last_success_utc is not None
    assert c.state == 'aggiornato_non_salvato'
    assert c.stale


async def test_cancelled_storage_does_not_mix_old_values_with_new_timestamp(hass):
    c = make_coordinator(hass)
    started, finish = asyncio.Event(), asyncio.Event()
    async def save(*args):
        started.set()
        await finish.wait()
    c._store = SimpleNamespace(async_save=save)
    task = asyncio.create_task(c.async_update_manually())
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert c.data['day_kwh'] == 3
    assert c.last_success_utc is not None
    assert c.state == 'aggiornato_non_salvato'
    assert c._busy is False
