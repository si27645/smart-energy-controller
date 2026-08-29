"""Client for OMIE's free day-ahead marginal price files (Iberian market).

Verified against a live file on 2026-08-30
(``marginalpdbc_20240115.1``), format:

    MARGINALPDBC;
    YYYY;MM;DD;HH;PRICE_1;PRICE_2;
    ...
    *

HH runs 1..24 (hour-ending). PRICE_1/PRICE_2 are in EUR/MWh and are
identical outside interconnector congestion between Spain and Portugal.
OMIE's own file does not label which column is which market — verify the
current column order in OMIE's documentation before trusting `market` in
production; treat it as a best-effort default for now.
"""
from __future__ import annotations

from datetime import date

import httpx

OMIE_URL_TEMPLATE = (
    "https://www.omie.es/en/file-download?parents%5B0%5D=marginalpdbc&filename=marginalpdbc_{date}.1"
)


def parse_omie_marginalpdbc(text: str, *, market: str = "pt") -> list[float]:
    """Parse a `marginalpdbc_YYYYMMDD.1` file into 24 hourly prices in EUR/kWh."""
    column = 5 if market == "pt" else 4  # 0-indexed position within each row's parts
    prices: list[float | None] = [None] * 24

    for line in text.strip().splitlines():
        parts = [p for p in line.strip().split(";") if p != ""]
        if len(parts) < 6:
            continue  # header ("MARGINALPDBC;") or trailing marker ("*")
        try:
            hour = int(parts[3])
            price_mwh = float(parts[column])
        except (ValueError, IndexError):
            continue
        if 1 <= hour <= 24:
            prices[hour - 1] = round(price_mwh / 1000, 5)  # EUR/MWh -> EUR/kWh

    missing = [h + 1 for h, p in enumerate(prices) if p is None]
    if missing:
        raise ValueError(f"Ficheiro OMIE incompleto — faltam as horas: {missing}")
    return prices  # type: ignore[return-value]


async def fetch_omie_prices_today(*, market: str = "pt", timeout: float = 10.0) -> list[float]:
    """Fetch and parse today's day-ahead prices from OMIE."""
    today = date.today().strftime("%Y%m%d")
    url = OMIE_URL_TEMPLATE.format(date=today)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    return parse_omie_marginalpdbc(resp.text, market=market)
