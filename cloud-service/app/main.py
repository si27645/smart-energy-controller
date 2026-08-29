"""Smart Energy Controller — cloud optimizer API.

This is the *only* part of the product that costs money to run (see
../../docs/cloud-layer.md): normalizing forecast/price feeds and computing
a real day-ahead schedule. The local Home Assistant integration stays free
and works without this service — it just gets smarter with it.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .models import OptimizeRequest, OptimizeResponse
from .optimizer.engine import optimize
from .providers.price_feed import fetch_omie_prices_today
from .providers.solar_forecast import fetch_solar_forecast_kw

app = FastAPI(
    title="Smart Energy Controller — Cloud Optimizer",
    version="0.1.0",
    description="Agrega previsão solar + preços dinâmicos e calcula o plano ótimo do dia seguinte.",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/optimize", response_model=OptimizeResponse)
async def optimize_endpoint(req: OptimizeRequest) -> OptimizeResponse:
    return optimize(req)


@app.get("/forecast/solar")
async def solar_forecast(lat: float, lon: float, declination: float, azimuth: float, kwp: float) -> dict:
    try:
        forecast = await fetch_solar_forecast_kw(lat, lon, declination, azimuth, kwp)
    except Exception as exc:  # noqa: BLE001 - surfaced to the caller as a 502
        raise HTTPException(status_code=502, detail=f"Falha ao obter previsão solar: {exc}") from exc
    return {"solar_forecast_kw": forecast}


@app.get("/prices/omie")
async def omie_prices(market: str = "pt") -> dict:
    try:
        prices = await fetch_omie_prices_today(market=market)
    except Exception as exc:  # noqa: BLE001 - surfaced to the caller as a 502
        raise HTTPException(status_code=502, detail=f"Falha ao obter preços OMIE: {exc}") from exc
    return {"price_eur_per_kwh": prices}
