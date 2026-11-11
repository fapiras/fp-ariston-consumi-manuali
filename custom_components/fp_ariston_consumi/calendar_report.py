"""Calendar alignment verified against a dated Ariston app export.

The monthly series ends at the last closed month; the daily series ends at
yesterday. Two-hour buckets use UTC interval endings. Keep the capture date
with the computed mapping: never re-date cached readings on restart.
"""
from datetime import datetime, timedelta, timezone
import math
from zoneinfo import ZoneInfo

MONTH_NAMES = ('Gennaio','Febbraio','Marzo','Aprile','Maggio','Giugno',
               'Luglio','Agosto','Settembre','Ottobre','Novembre','Dicembre')


def month_label(key):
    year, month = map(int, key.split('-'))
    return f'{MONTH_NAMES[month-1]} {year}'


def _pair(detail):
    hp = detail.get('pompa_di_calore_kwh')
    rs = detail.get('resistenza_kwh')
    if not hp or not rs or len(hp) != len(rs):
        return None
    return hp, rs


def _record(hp, rs, partial=False):
    return {'pdc':round(math.fsum(hp),3), 'resistenza':round(math.fsum(rs),3),
            'totale':round(math.fsum([*hp,*rs]),3), 'parziale':partial}


def calendar_months(details, captured_at, time_zone):
    """Return available named months and clearly mark the current partial month."""
    local = captured_at.astimezone(ZoneInfo(time_zone))
    months = {}
    closed = _pair(details.get('year_kwh',{}))
    if closed:
        hp, rs = closed
        # Month indexes use year*12 + zero-based month; one before current.
        last_index = local.year*12 + local.month-2
        for index,(h,r) in enumerate(zip(hp,rs,strict=True)):
            month_index = last_index-len(hp)+1+index
            year, month = divmod(month_index,12)
            months[f'{year:04d}-{month+1:02d}'] = _record([h],[r])

    daily = _pair(details.get('month_kwh',{}))
    hourly = _pair(details.get('day_kwh',{}))
    if daily and hourly:
        dh, dr = daily
        hh, hr = hourly
        # The export's daily rows end at yesterday. Require coverage from the
        # first of this month and guard against changed server aggregation.
        if local.day-1 <= len(dh) <= 62:
            daily_hp, daily_rs = [], []
            for i,(h,r) in enumerate(zip(dh,dr,strict=True)):
                day = local.date()-timedelta(days=len(dh)-i)
                if (day.year,day.month)==(local.year,local.month):
                    daily_hp.append(h)
                    daily_rs.append(r)
            utc = captured_at.astimezone(timezone.utc)
            boundary = utc.replace(minute=0,second=0,microsecond=0)
            if utc != boundary:
                boundary += timedelta(hours=1)
            if boundary.hour % 2:
                boundary += timedelta(hours=1)
            # Validate that hourly data span midnight, rather than treating a
            # truncated current-day sequence as the whole current day.
            first = (boundary-timedelta(hours=2*(len(hh)-1))).astimezone(ZoneInfo(time_zone))
            if first.date() < local.date() and len(hh)<=48:
                for i,(h,r) in enumerate(zip(hh,hr,strict=True)):
                    ending = (boundary-timedelta(hours=2*(len(hh)-1-i))).astimezone(ZoneInfo(time_zone))
                    if ending.date()==local.date():
                        daily_hp.append(h)
                        daily_rs.append(r)
                months[f'{local.year:04d}-{local.month:02d}'] = _record(daily_hp,daily_rs,True)
    return months
