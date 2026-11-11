"""Exercise the complete pure parser module, not extracted AST functions."""
import importlib.util
import math
from pathlib import Path

import pytest

SOURCE = Path(__file__).parents[2] / 'custom_components/fp_ariston_consumi/energy_report.py'
spec = importlib.util.spec_from_file_location('fp_energy_report', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_totals_and_zero_are_valid():
    assert module.parse_period_report([{'v': [0.1, 0.2]}, {'v': [0]}, {'v':[2, 3]}, {'v': [12.5]}]) == {
        'day_kwh': 0.3, 'week_kwh': 0, 'month_kwh': 5, 'year_kwh': 12.5,
    }


def test_empty_report_has_specific_safe_error():
    with pytest.raises(module.ReportValidationError, match='Nessun report'):
        module.parse_period_report(None)


def test_missing_buckets_have_specific_safe_error():
    with pytest.raises(module.ReportValidationError, match='1 valori mancanti su 2'):
        module.parse_period_report([{'v':[1,None]}]*4)


def test_structure_does_not_expose_response_values_or_unknown_keys():
    payload = {'secret-token':'secret-value','reports':[{'gw':'private-device'}]}
    assert module.report_structure(payload) == {'tipo':'dict','elementi':2,'campi_noti':{'reports':'list'}}
    assert module.report_structure([{'v':[123,None]}]) == {'tipo':'list','elementi':1,'periodi':[{'tipo':'dict','valori':2}]}


@pytest.mark.parametrize('value', [None, True, False, -1, math.nan, math.inf, -math.inf, '1', {}, []])
def test_invalid_buckets_cannot_become_energy(value):
    with pytest.raises(ValueError):
        module.parse_period_report([{'v': [1, value]}] * 4)


@pytest.mark.parametrize('payload', [None, {}, [], [{'v': [1]}] * 3, [{'v': [1]}] * 5, [{'v': []}] * 4, [{'v': None}] * 4])
def test_missing_or_ambiguous_periods_are_rejected(payload):
    with pytest.raises(ValueError):
        module.parse_period_report(payload)
