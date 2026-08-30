# ☁️ Cloud Optimizer

The only part of the product that runs outside the user's home: aggregates solar forecasts + dynamic prices and computes a next-day plan, for both profiles (with and without a battery). The local engine (`custom_components/`) stays free and functional without this — this service is what backs the optional **Cloud Copilot** plan, which exists because aggregating and optimizing this data requires ongoing infrastructure, unlike logic that runs in the user's own home.

## Running locally

```bash
cd cloud-service
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Tests (no network, synthetic data + a real OMIE file captured as a fixture):

```bash
python -m pytest -q
```

## Endpoints

| Endpoint | What it does |
|---|---|
| `GET /health` | Simple health check. |
| `GET /forecast/solar?lat=&lon=&declination=&azimuth=&kwp=` | Hourly solar forecast (kW), via [Forecast.Solar](https://doc.forecast.solar/) (public API, no key, limited to ~12 requests/hour per IP). |
| `GET /prices/omie?market=pt` | Hourly Iberian market prices (€/kWh), via OMIE's daily public file. |
| `POST /optimize` | Takes solar forecast + prices + consumption + flexible loads (+ battery, optional) and returns the 24h plan, with one reason per decision. |

Tested against real, live data on 2026-08-30 — all three endpoints and `/optimize` end-to-end (real solar forecast → real OMIE prices → optimized plan) worked as documented below.

### Example `/optimize` request

```json
{
  "profile": "with_battery",
  "solar_forecast_kw": [0, 0, 0, 0, 0, 0, 0, 0, 0.3, 0.6, 1.1, 1.7, 1.8, 1.8, 2.3, 2.5, 2.4, 1.9, 1.3, 0.7, 0.2, 0, 0, 0],
  "price_eur_per_kwh": [0.18, 0.18, 0.20, 0.20, 0.20, 0.18, 0.18, 0.18, 0.18, 0.18, 0.18, 0.18, 0.18, 0.18, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17],
  "consumption_kw": [0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.5, 0.8, 0.5, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.5, 0.8, 1.2, 1.5, 1.2, 0.9, 0.6, 0.4, 0.3],
  "flexible_loads": [{"name": "EV", "energy_kwh": 8, "power_kw": 3.6, "earliest_hour": 8, "deadline_hour": 20}],
  "battery": {"capacity_kwh": 10, "soc_pct": 30, "max_charge_kw": 3, "max_discharge_kw": 3, "reserve_soc_pct": 20}
}
```

For the no-battery profile, just omit `battery` and set `"profile": "without_battery"` — flexible loads (water heater, EV, etc.) are still optimized by solar surplus first, cheapest price second.

## How the optimizer works

A greedy, explainable heuristic (not an opaque model), in [`app/optimizer/engine.py`](app/optimizer/engine.py):

1. **Flexible loads first**, most urgent (earliest deadline) first: each one tries to fit into hours with leftover solar surplus; whatever's left goes to the cheapest hours in its window.
2. **Battery** (`with_battery` profile only): charges from leftover solar surplus, then tops up from the grid in the cheapest hours of the day, and discharges into the priciest hours that still have an unmet deficit — never below the configured reserve.

Every hour of the plan comes with a sentence explaining the decision — the same explainability principle as the local engine.

## Known limitations (MVP)

- **No partial blending within the hour**: if a load (e.g. an EV at 3.6 kW) exceeds the instantaneous solar surplus (e.g. 2 kW), the whole hour falls back to price logic instead of taking the free 2 kW and buying only the difference. Seen in a real test — the EV in the example above never used solar because peak production (~2.5 kW) never reached the wallbox's 3.6 kW.
- **Greedy heuristic, not a globally optimal solver**: it can fill the battery more than necessary if there's no pricey deficit later in the day to justify it. Explainability is prioritized over absolute optimality — a deliberate choice, not a bug.
- **The OMIE file's column order (Spain/Portugal) isn't documented by OMIE itself** — the parser assumes a default order; confirm before relying on it in production (see the comment in [`app/providers/price_feed.py`](app/providers/price_feed.py)).
- **Free Forecast.Solar**: only covers today/tomorrow and has a request limit — fine for a daily plan, not for historical data.
- Only plans **one day** at a time — it doesn't look ahead when deciding to "save the battery for tomorrow" (that still lives as a separate rule in the local engine).
