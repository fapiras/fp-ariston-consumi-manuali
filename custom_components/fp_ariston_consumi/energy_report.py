"""Strict parsing of undocumented Ariston period reports."""
import math
from typing import Any

PERIOD_KEYS = ("day_kwh", "week_kwh", "month_kwh", "year_kwh")

def parse_period_report(payload: Any) -> dict[str, float]:
    """Validate period buckets; never silently count incomplete data as zero."""
    if not isinstance(payload, list) or len(payload) != 4:
        raise ValueError('Expected four Ariston period records')
    totals = {}
    for key, record in zip(PERIOD_KEYS, payload, strict=True):
        if not isinstance(record, dict) or not isinstance(record.get('v'), list) or not record['v']:
            raise ValueError(f'Invalid {key} report')
        values = record['v']
        if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values):
            raise ValueError(f'Incomplete or invalid {key} report')
        total = math.fsum(values)
        if not math.isfinite(total):
            raise ValueError('Invalid total')
        totals[key] = round(total, 3)
    return totals

