"""Gestione orari: in DB tutto in UTC naive, in UI/email ora locale (Europe/Rome)."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from config import TIMEZONE

TZ = ZoneInfo(TIMEZONE)
GIORNI = ["lunedì","martedì","mercoledì","giovedì","venerdì","sabato","domenica"]
MESI = ["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio",
        "agosto","settembre","ottobre","novembre","dicembre"]

def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def local_now() -> datetime:
    return datetime.now(TZ)

def to_local(dt_utc: datetime) -> datetime:
    return dt_utc.replace(tzinfo=timezone.utc).astimezone(TZ)

def local_to_utc(dt_local_naive: datetime) -> datetime:
    return dt_local_naive.replace(tzinfo=TZ).astimezone(timezone.utc).replace(tzinfo=None)

def fmt_long(dt_utc: datetime) -> str:
    d = to_local(dt_utc)
    return f"{GIORNI[d.weekday()]} {d.day} {MESI[d.month-1]} {d.year}, ore {d:%H:%M}"

def fmt_short(dt_utc: datetime) -> str:
    return to_local(dt_utc).strftime("%d/%m/%Y %H:%M")
