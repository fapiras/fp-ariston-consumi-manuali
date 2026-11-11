"""Lydos Hybrid consumption channels, keyed explicitly by API kind and period.

Keys 8/9 and period codes 1..4 follow the vendored upstream client.
Period boundaries are provided by Ariston; no calendar month is inferred.
"""
import math

from .energy_report import PERIOD_KEYS, ReportValidationError

REPORT_SOURCE = 'lydos_hybrid_channels_v1'
HYBRID_REPORT_PATH = '/remote/reports/{gateway}/consSequencesApi8?usages=DhwHeatingPumpElec%2CDhwResistorElec'


def parse_hybrid_report(payload):
    """Require both electricity channels before publishing a period total."""
    if not isinstance(payload, list) or not payload:
        raise ReportValidationError('Nessuna sequenza energetica Lydos Hybrid disponibile')
    sequences = {}
    for row in payload:
        if not isinstance(row, dict):
            raise ReportValidationError('Sequenza Lydos Hybrid non valida')
        kind, period = row.get('k'), row.get('p')
        if type(kind) is not int or kind not in (8, 9):
            continue
        if type(period) is not int or period not in (1, 2, 3, 4):
            continue
        pair = (kind, period)
        if pair in sequences:
            raise ReportValidationError('Sequenza energetica duplicata; totale non calcolato')
        values = row.get('v')
        if not isinstance(values, list):
            raise ReportValidationError('Elenco consumi Lydos Hybrid non valido')
        if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values):
            raise ReportValidationError('Valori Lydos Hybrid mancanti o non validi; totale non calcolato')
        sequences[pair] = values
    totals, details = {}, {}
    for period, key in enumerate(PERIOD_KEYS, 1):
        hp, resistor = sequences.get((8, period)), sequences.get((9, period))
        details[key] = {
            'pompa_di_calore_kwh': hp,
            'resistenza_kwh': resistor,
            'codice_periodo_api': period,
        }
        # Empty/missing channels are not zero. Mismatched bucket counts cannot
        # establish that the two sequences cover the same reporting interval.
        if not hp or not resistor or len(hp) != len(resistor):
            totals[key] = None
            continue
        try:
            total = math.fsum([*hp, *resistor])
        except OverflowError as error:
            raise ReportValidationError('Totale Lydos Hybrid non valido') from error
        if not math.isfinite(total):
            raise ReportValidationError('Totale Lydos Hybrid non valido')
        totals[key] = round(total, 3)
    if all(value is None for value in totals.values()):
        raise ReportValidationError('Nessun periodo completo con pompa di calore e resistenza disponibili')
    return totals, details
