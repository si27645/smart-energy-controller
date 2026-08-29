"""Request/response contracts for the cloud optimizer API."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class FlexibleLoad(BaseModel):
    """A device that needs a fixed amount of energy delivered within a window.

    Covers EV charging, water heater, pool pump, etc. — with or without a
    battery, this is the thing the optimizer actually schedules.
    """

    name: str
    energy_kwh: float = Field(gt=0, description="Total energy this load needs, e.g. 20 for an EV top-up")
    power_kw: float = Field(gt=0, description="Power drawn while running")
    earliest_hour: int = Field(ge=0, le=23, default=0, description="Hour of day it may start (0-23)")
    deadline_hour: int = Field(ge=1, le=24, description="Hour by which energy_kwh must be delivered (1-24)")

    @model_validator(mode="after")
    def _window_is_valid(self) -> "FlexibleLoad":
        if self.deadline_hour <= self.earliest_hour:
            raise ValueError("deadline_hour must be after earliest_hour")
        return self


class BatteryConfig(BaseModel):
    capacity_kwh: float = Field(gt=0)
    soc_pct: float = Field(ge=0, le=100, description="Current state of charge, in %")
    max_charge_kw: float = Field(gt=0)
    max_discharge_kw: float = Field(gt=0)
    reserve_soc_pct: float = Field(default=20, ge=0, le=100, description="Never discharge below this SoC")


class OptimizeRequest(BaseModel):
    profile: Literal["with_battery", "without_battery"]
    solar_forecast_kw: list[float] = Field(min_length=24, max_length=24)
    price_eur_per_kwh: list[float] = Field(min_length=24, max_length=24)
    consumption_kw: Optional[list[float]] = Field(
        default=None, description="Baseline household consumption per hour; defaults to all zeros"
    )
    flexible_loads: list[FlexibleLoad] = Field(default_factory=list)
    battery: Optional[BatteryConfig] = None

    @model_validator(mode="after")
    def _battery_matches_profile(self) -> "OptimizeRequest":
        if self.profile == "with_battery" and self.battery is None:
            raise ValueError("profile 'with_battery' requires a battery config")
        if self.consumption_kw is not None and len(self.consumption_kw) != 24:
            raise ValueError("consumption_kw must have exactly 24 values")
        return self


class HourDecision(BaseModel):
    hour: int
    battery_action_kw: float = Field(default=0.0, description="Positive = charging, negative = discharging")
    loads_on: list[str] = Field(default_factory=list)
    reason: str


class OptimizeResponse(BaseModel):
    profile: str
    schedule: list[HourDecision]
    estimated_cost_eur: float
    estimated_grid_import_kwh: float
    notes: list[str] = Field(default_factory=list)
