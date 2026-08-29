"""Client for the free Forecast.Solar public API.

Docs: https://doc.forecast.solar/ — the no-key "public" endpoint is rate
limited (12 requests/hour/IP as of writing) and only forecasts today and
tomorrow, which is enough for a day-ahead optimizer.

Verified against a live response on 2026-08-30 — the API returns a
``result.watts`` map keyed by local timestamp strings, with a few
sub-hour entries (sunrise/sunset) mixed in among the on-the-hour ones.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import httpx

FORECAST_SOLAR_BASE = "https://api.forecast.solar/estimate"


async def fetch_solar_forecast_kw(
    lat: float,
    lon: float,
    declination: float,
    azimuth: float,
    kwp: float,
    *,
    timeout: float = 10.0,
) -> list[float]:
    """Return 24 hourly solar production estimates in kW, starting this hour.

    Args:
        lat, lon: panel location.
        declination: panel tilt in degrees (0 = flat, 90 = vertical).
        azimuth: panel direction in degrees (-180..180, 0 = south).
        kwp: installed peak power in kWp.
    """
    url = f"{FORECAST_SOLAR_BASE}/{lat}/{lon}/{declination}/{azimuth}/{kwp}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        payload = resp.json()

    return _to_hourly_kw(payload["result"]["watts"])


def _to_hourly_kw(watts_by_timestamp: dict[str, float]) -> list[float]:
    """Keep only on-the-hour samples and align them to the next 24 hours."""
    on_the_hour: dict[datetime, float] = {}
    for ts, watts in watts_by_timestamp.items():
        dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        if dt.minute == 0 and dt.second == 0:
            on_the_hour[dt] = watts

    start = datetime.now().replace(minute=0, second=0, microsecond=0)
    return [round(on_the_hour.get(start + timedelta(hours=i), 0.0) / 1000, 3) for i in range(24)]
