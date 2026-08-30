"""Optimizer tests with synthetic 24h data — deterministic, no network."""
from app.models import BatteryConfig, FlexibleLoad, OptimizeRequest
from app.optimizer.engine import optimize


def _flat_price(cheap_hour: int = 3, cheap_price: float = 0.05, pricey_hour: int = 19, pricey_price: float = 0.15):
    price = [0.10] * 24
    price[cheap_hour] = cheap_price
    price[pricey_hour] = pricey_price
    return price


def test_without_battery_prefers_free_solar_surplus_for_ev_charging():
    solar = [0.0] * 24
    solar[11] = solar[12] = 3.0  # two hours of surplus, no baseline consumption

    req = OptimizeRequest(
        profile="without_battery",
        solar_forecast_kw=solar,
        price_eur_per_kwh=_flat_price(),
        flexible_loads=[
            FlexibleLoad(name="EV", energy_kwh=4, power_kw=2, earliest_hour=0, deadline_hour=24)
        ],
    )

    result = optimize(req)

    assert sorted(h.hour for h in result.schedule if "EV" in h.loads_on) == [11, 12]
    assert "solar surplus" in result.schedule[11].reason.lower()
    assert result.estimated_cost_eur == 0.0
    assert result.estimated_grid_import_kwh == 0.0
    assert any("lost" in note for note in result.notes)


def test_without_battery_falls_back_to_cheapest_hour_when_no_surplus():
    req = OptimizeRequest(
        profile="without_battery",
        solar_forecast_kw=[0.0] * 24,
        price_eur_per_kwh=_flat_price(),
        flexible_loads=[
            FlexibleLoad(name="Water heater", energy_kwh=2, power_kw=2, earliest_hour=0, deadline_hour=24)
        ],
    )

    result = optimize(req)
    on_hours = [h.hour for h in result.schedule if "Water heater" in h.loads_on]

    assert on_hours == [3]  # the single cheapest hour in the window
    assert result.estimated_cost_eur == round(2 * 0.05, 4)


def test_with_battery_charges_cheap_and_discharges_pricey():
    consumption = [0.0] * 24
    consumption[19] = 2.0  # a load that would otherwise cost the pricey-hour rate

    req = OptimizeRequest(
        profile="with_battery",
        solar_forecast_kw=[0.0] * 24,
        price_eur_per_kwh=_flat_price(),
        consumption_kw=consumption,
        battery=BatteryConfig(
            capacity_kwh=10, soc_pct=20, max_charge_kw=3, max_discharge_kw=3, reserve_soc_pct=20
        ),
    )

    result = optimize(req)
    by_hour = {h.hour: h.battery_action_kw for h in result.schedule}

    # Cheapest hours fill the battery first (3 -> 0 -> 1, 3kW/3kW/2kW to reach 10kWh from 2kWh)
    assert by_hour[3] == 3.0
    assert by_hour[0] == 3.0
    assert by_hour[1] == 2.0
    # The priciest hour discharges instead of buying from the grid
    assert by_hour[19] == -2.0
    assert "discharging the battery" in result.schedule[19].reason

    assert result.estimated_cost_eur == 0.65
    assert result.estimated_grid_import_kwh == 8.0


def test_battery_never_discharges_below_reserve():
    req = OptimizeRequest(
        profile="with_battery",
        solar_forecast_kw=[0.0] * 24,
        price_eur_per_kwh=_flat_price(),
        consumption_kw=[1.0] * 24,  # constant deficit all day
        battery=BatteryConfig(
            capacity_kwh=5, soc_pct=20, max_charge_kw=1, max_discharge_kw=5, reserve_soc_pct=20
        ),
    )

    result = optimize(req)

    # Battery starts exactly at its reserve (1 kWh of 5); it may charge, but
    # must never discharge past the 1 kWh reserve floor.
    min_soc_seen = 5 * 0.20
    soc = 5 * 0.20
    for h in result.schedule:
        soc += h.battery_action_kw
        min_soc_seen = min(min_soc_seen, soc)
    assert min_soc_seen >= 5 * 0.20 - 1e-6
