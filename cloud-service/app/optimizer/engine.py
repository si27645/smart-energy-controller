"""Deterministic, explainable day-ahead optimizer.

Not a black-box ML model — a greedy, auditable heuristic: every kWh moved
comes with a one-line reason, matching the "explain every decision"
principle of the local rules engine. Handles both profiles:

- ``with_battery``: schedules flexible loads, then charges/discharges the
  battery around solar surplus and price.
- ``without_battery``: schedules flexible loads only — surplus that no
  load can absorb is simply lost, which the response calls out explicitly.
"""
from __future__ import annotations

import math

from ..models import HourDecision, OptimizeRequest, OptimizeResponse

HOURS_PER_DAY = 24


def optimize(req: OptimizeRequest) -> OptimizeResponse:
    solar = req.solar_forecast_kw
    price = req.price_eur_per_kwh
    consumption = req.consumption_kw or [0.0] * HOURS_PER_DAY

    # What the house would pay with zero flexibility: only the plain
    # consumption/solar gap, bought from the grid hour by hour.
    baseline_grid_kwh = [max(0.0, consumption[h] - solar[h]) for h in range(HOURS_PER_DAY)]
    baseline_cost = sum(baseline_grid_kwh[h] * price[h] for h in range(HOURS_PER_DAY))

    remaining_surplus = [max(0.0, solar[h] - consumption[h]) for h in range(HOURS_PER_DAY)]
    decisions = [{"battery_action_kw": 0.0, "loads_on": [], "reasons": []} for _ in range(HOURS_PER_DAY)]

    flex_grid_cost, flex_grid_kwh = _schedule_flexible_loads(req, remaining_surplus, price, decisions)

    battery_charge_grid_cost = battery_charge_grid_kwh = 0.0
    battery_discharge_savings = battery_discharge_kwh = 0.0
    if req.profile == "with_battery" and req.battery is not None:
        (
            battery_charge_grid_cost,
            battery_charge_grid_kwh,
            battery_discharge_savings,
            battery_discharge_kwh,
        ) = _schedule_battery(req, remaining_surplus, price, baseline_grid_kwh, decisions)

    total_cost = baseline_cost + flex_grid_cost + battery_charge_grid_cost - battery_discharge_savings
    total_grid_kwh = (
        sum(baseline_grid_kwh) + flex_grid_kwh + battery_charge_grid_kwh - battery_discharge_kwh
    )

    schedule = [
        HourDecision(
            hour=h,
            battery_action_kw=round(decisions[h]["battery_action_kw"], 3),
            loads_on=decisions[h]["loads_on"],
            reason="; ".join(decisions[h]["reasons"]) or "Sem ação — nada a otimizar nesta hora",
        )
        for h in range(HOURS_PER_DAY)
    ]

    notes = []
    if req.profile == "without_battery":
        notes.append(
            "Sem bateria: o excedente que nenhuma carga flexível conseguiu absorver é considerado "
            "perdido (injetado na rede a troco de quase nada)."
        )

    return OptimizeResponse(
        profile=req.profile,
        schedule=schedule,
        estimated_cost_eur=round(max(total_cost, 0.0), 4),
        estimated_grid_import_kwh=round(max(total_grid_kwh, 0.0), 3),
        notes=notes,
    )


def _schedule_flexible_loads(
    req: OptimizeRequest,
    remaining_surplus: list[float],
    price: list[float],
    decisions: list[dict],
) -> tuple[float, float]:
    """Assign each flexible load to its cheapest hours, free surplus first.

    Most urgent loads (earliest deadline) are placed first, so a tight EV
    deadline doesn't lose its best hours to a water heater that could run
    anytime. Returns (grid_cost_added, grid_kwh_added).
    """
    grid_cost = grid_kwh = 0.0

    for load in sorted(req.flexible_loads, key=lambda l: l.deadline_hour):
        window = list(range(load.earliest_hour, load.deadline_hour))
        hours_needed = math.ceil(load.energy_kwh / load.power_kw)

        free_hours = sorted(
            (h for h in window if remaining_surplus[h] >= load.power_kw),
            key=lambda h: -remaining_surplus[h],
        )
        chosen = free_hours[:hours_needed]
        if len(chosen) < hours_needed:
            candidates = [h for h in window if h not in chosen]
            chosen += sorted(candidates, key=lambda h: price[h])[: hours_needed - len(chosen)]

        if len(chosen) < hours_needed:
            for h in chosen:
                decisions[h]["reasons"].append(
                    f"{load.name}: janela [{load.earliest_hour}h-{load.deadline_hour}h] "
                    f"não chega para as {hours_needed}h necessárias"
                )

        for h in chosen:
            decisions[h]["loads_on"].append(load.name)
            if remaining_surplus[h] >= load.power_kw:
                remaining_surplus[h] -= load.power_kw
                decisions[h]["reasons"].append(f"{load.name}: excedente solar cobre a carga (0 €)")
            else:
                grid_cost += load.power_kw * price[h]
                grid_kwh += load.power_kw
                decisions[h]["reasons"].append(
                    f"{load.name}: sem excedente suficiente, preço da hora é {price[h]:.3f} €/kWh"
                )

    return grid_cost, grid_kwh


def _schedule_battery(
    req: OptimizeRequest,
    remaining_surplus: list[float],
    price: list[float],
    baseline_grid_kwh: list[float],
    decisions: list[dict],
) -> tuple[float, float, float, float]:
    """Charge from surplus, top up from cheap grid hours, discharge during pricey ones.

    Returns (charge_grid_cost, charge_grid_kwh, discharge_savings, discharge_kwh).
    """
    battery = req.battery
    soc_kwh = battery.capacity_kwh * battery.soc_pct / 100
    reserve_kwh = battery.capacity_kwh * battery.reserve_soc_pct / 100

    # 1) Free first: soak up leftover solar surplus, biggest surplus hours first.
    for h in sorted(range(HOURS_PER_DAY), key=lambda h: -remaining_surplus[h]):
        if soc_kwh >= battery.capacity_kwh or remaining_surplus[h] <= 0:
            continue
        charge = min(battery.max_charge_kw, remaining_surplus[h], battery.capacity_kwh - soc_kwh)
        if charge <= 0:
            continue
        soc_kwh += charge
        remaining_surplus[h] -= charge
        decisions[h]["battery_action_kw"] += charge
        decisions[h]["reasons"].append(f"Excedente solar de {charge:.1f} kW a carregar a bateria")

    # 2) Still below capacity? Top up from the grid in the cheapest hours left.
    charge_grid_cost = charge_grid_kwh = 0.0
    for h in sorted(range(HOURS_PER_DAY), key=lambda h: price[h]):
        if soc_kwh >= battery.capacity_kwh:
            break
        if decisions[h]["battery_action_kw"] > 0:
            continue  # already charged from solar this hour
        charge = min(battery.max_charge_kw, battery.capacity_kwh - soc_kwh)
        if charge <= 0:
            continue
        soc_kwh += charge
        charge_grid_cost += charge * price[h]
        charge_grid_kwh += charge
        decisions[h]["battery_action_kw"] += charge
        decisions[h]["reasons"].append(f"Preço baixo ({price[h]:.3f} €/kWh) — a carregar a bateria da rede")

    # 3) Discharge into the priciest hours that still have an unmet grid deficit.
    discharge_savings = discharge_kwh = 0.0
    for h in sorted(range(HOURS_PER_DAY), key=lambda h: -price[h]):
        deficit = baseline_grid_kwh[h]
        if deficit <= 0 or soc_kwh <= reserve_kwh:
            continue
        discharge = min(battery.max_discharge_kw, deficit, soc_kwh - reserve_kwh)
        if discharge <= 0:
            continue
        soc_kwh -= discharge
        discharge_savings += discharge * price[h]
        discharge_kwh += discharge
        decisions[h]["battery_action_kw"] -= discharge
        decisions[h]["reasons"].append(
            f"Preço alto ({price[h]:.3f} €/kWh) — a descarregar a bateria em vez de comprar à rede"
        )

    return charge_grid_cost, charge_grid_kwh, discharge_savings, discharge_kwh
