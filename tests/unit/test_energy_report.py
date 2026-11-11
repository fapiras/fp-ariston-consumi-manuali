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


@pytest.mark.parametrize('value', [None, True, False, -1, math.nan, math.inf, -math.inf, '1', {}, []])
def test_invalid_buckets_cannot_become_energy(value):
    with pytest.raises(ValueError):
        module.parse_period_report([{'v': [1, value]}] * 4)


@pytest.mark.parametrize('payload', [None, {}, [], [{'v': [1]}] * 3, [{'v': [1]}] * 5, [{'v': []}] * 4, [{'v': None}] * 4])
def test_missing_or_ambiguous_periods_are_rejected(payload):
    with pytest.raises(ValueError):
        module.parse_period_report(payload)
