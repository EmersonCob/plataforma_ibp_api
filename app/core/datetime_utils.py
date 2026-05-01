from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import settings


def display_timezone() -> ZoneInfo:
    return ZoneInfo(settings.display_timezone)


def to_display_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=ZoneInfo("UTC")).astimezone(display_timezone())
    return value.astimezone(display_timezone())


def format_display_datetime(value: datetime) -> str:
    localized = to_display_timezone(value)
    return localized.strftime("%d/%m/%Y às %H:%M")
