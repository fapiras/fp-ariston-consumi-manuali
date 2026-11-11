"""Check Hybrid channels independently of the Home Assistant runtime."""
import importlib
import sys
from types import ModuleType
from pathlib import Path
import pytest

pkg = ModuleType('fp_energy_test')
pkg.__path__ = [str(Path(__file__).parents[2] / 'custom_components/fp_ariston_consumi')]
sys.modules['fp_energy_test'] = pkg
parser = importlib.import_module('fp_energy_test.hybrid_report')


def test_heat_pump_33_and_zero_resistor_are_added_and_order_is_irrelevant():
    rows = [{'k':9,'p':4,'v':[0]*12}, {'k':8,'p':4,'v':[0]*9+[33,0,0]}]
    totals, details = parser.parse_hybrid_report(rows)
    assert totals == {'day_kwh':None,'week_kwh':None,'month_kwh':None,'year_kwh':33}
    assert details['year_kwh']['pompa_di_calore_kwh'][9] == 33


@pytest.mark.parametrize('rows', [
    [{'k':8,'p':4,'v':[33]}],
    [{'k':8,'p':4,'v':[33]}, {'k':9,'p':4,'v':[]}],
    [{'k':8,'p':4,'v':[33]}, {'k':9,'p':4,'v':[0,0]}],
    [{'k':2,'p':4,'v':[0]}],
    [{'k':8,'p':4,'v':[None]}, {'k':9,'p':4,'v':[0]}],
    [{'k':8,'p':4,'v':[33]}, {'k':8,'p':4,'v':[33]}, {'k':9,'p':4,'v':[0]}],
    [{'v':[0]}]*4,
])
def test_incomplete_ambiguous_and_generic_channels_cannot_become_totals(rows):
    with pytest.raises(ValueError):
        parser.parse_hybrid_report(rows)


def test_missing_day_week_do_not_discard_two_complete_other_periods():
    rows = [{'k':8,'p':3,'v':[2,3]}, {'k':9,'p':3,'v':[0,1]},
            {'k':8,'p':4,'v':[33]}, {'k':9,'p':4,'v':[0]}]
    totals, _ = parser.parse_hybrid_report(rows)
    assert totals['month_kwh'] == 6
    assert totals['year_kwh'] == 33
    assert totals['day_kwh'] is None
