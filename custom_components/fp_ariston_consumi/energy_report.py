"""Strict parsing of undocumented Ariston period reports."""
import math
from typing import Any

PERIOD_KEYS = ("day_kwh", "week_kwh", "month_kwh", "year_kwh")

class ReportValidationError(ValueError):
    """A safe, specific explanation containing no response values or identifiers."""


def report_structure(payload: Any) -> dict:
    """Describe only types/counts and allowlisted field names, never raw data."""
    result = {'tipo': type(payload).__name__}
    if isinstance(payload, (list, dict)):
        result['elementi'] = len(payload)
    if isinstance(payload, dict):
        result['campi_noti'] = {key: type(payload[key]).__name__ for key in (
            'data', 'reports', 'result', 'items', 'v'
        ) if key in payload}
    if isinstance(payload, list):
        result['periodi'] = [
            {'tipo': type(row).__name__, 'valori': len(row['v']) if isinstance(row, dict)
             and isinstance(row.get('v'), list) else None}
            for row in payload[:4]
        ]
    return result

def parse_period_report(payload: Any) -> dict[str, float | None]:
    """Validate period buckets; never silently count incomplete data as zero."""
    if payload is None:
        raise ReportValidationError('Nessun report energetico restituito: risposta vuota o endpoint non disponibile')
    if not isinstance(payload, list):
        raise ReportValidationError('Formato report inatteso: ricevuto ' + type(payload).__name__ + ', attesa una lista di periodi')
    if len(payload) != 4:
        raise ReportValidationError(f'Report energetico: attesi 4 periodi, ricevuti {len(payload)}')
    totals = {}
    for key, record in zip(PERIOD_KEYS, payload, strict=True):
        if not isinstance(record, dict) or not isinstance(record.get('v'), list):
            raise ReportValidationError(f'Report {key}: elenco dei consumi assente o non valido')
        values = record['v']
        if not values:
            totals[key] = None
            continue
        if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values):
            missing = sum(v is None for v in values)
            if missing:
                raise ReportValidationError(f'Report {key}: {missing} valori mancanti su {len(values)}; totale non calcolato')
            raise ReportValidationError(f'Report {key}: valori non numerici, negativi o non finiti; totale non calcolato')
        total = math.fsum(values)
        if not math.isfinite(total):
            raise ValueError('Invalid total')
        totals[key] = round(total, 3)
    if all(value is None for value in totals.values()):
        raise ReportValidationError('Nessun periodo energetico disponibile: tutti gli elenchi sono vuoti')
    return totals

