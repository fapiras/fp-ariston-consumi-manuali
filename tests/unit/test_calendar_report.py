"""Calendar alignment, current-day split, month/year boundaries and gaps."""
import importlib
import sys
from pathlib import Path
from types import ModuleType
from datetime import datetime, timezone

pkg = ModuleType('fp_calendar_test')
pkg.__path__ = [str(Path(__file__).parents[2]/'custom_components/fp_ariston_consumi')]
sys.modules['fp_calendar_test'] = pkg
calendar = importlib.import_module('fp_calendar_test.calendar_report')


def detail(hp, rs=None):
    return {'pompa_di_calore_kwh':hp,'resistenza_kwh':[0]*len(hp) if rs is None else rs}


def test_dated_export_shape_has_22_closed_months_and_november_from_daily_and_hourly():
    rows = {'year_kwh':detail(list(range(22))),
            'month_kwh':detail([100]*31+[2]*10), 'day_kwh':detail([1]*24)}
    months = calendar.calendar_months(rows,datetime(2026,11,11,13,59,tzinfo=timezone.utc),'Europe/Rome')
    assert list(months)[0]=='2025-01'
    assert months['2026-10']['pdc']==21
    assert months['2026-11']['pdc']==28  # 10 completed days + 8 UTC-ending buckets today
    assert months['2026-11']['parziale']
    assert calendar.month_label('2026-10')=='Ottobre 2026'


def test_january_rollover_and_cache_dates_are_not_based_on_current_clock():
    months = calendar.calendar_months({'year_kwh':detail([7,8])},datetime(2027,1,3,tzinfo=timezone.utc),'Europe/Rome')
    assert list(months)==['2026-11','2026-12']


def test_insufficient_current_month_coverage_does_not_create_false_total():
    months = calendar.calendar_months({'year_kwh':detail([4]),'month_kwh':detail([2]),'day_kwh':detail([1])},
        datetime(2026,11,11,13,59,tzinfo=timezone.utc),'Europe/Rome')
    assert '2026-11' not in months
    assert months['2026-10']['totale']==4
