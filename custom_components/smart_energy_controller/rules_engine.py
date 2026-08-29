"""Deterministic, explainable rules engine.

Each rule watches one entity, compares it against a threshold or state,
and — when true — calls a Home Assistant service. Every decision is
logged and fired as an event so the reasoning is never a black box.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant

from .const import EVENT_DECISION

_LOGGER = logging.getLogger(__name__)


@dataclass
class Rule:
    """A single "SE ... ENTÃO ..." rule."""

    name: str
    entity_id: str
    service: str  # e.g. "switch.turn_on"
    above: float | None = None
    below: float | None = None
    state: str | None = None
    service_data: dict[str, Any] = field(default_factory=dict)
    explain: str | None = None

    # avoids re-firing the same service call every scan while the
    # condition stays true
    _last_result: bool | None = field(default=None, init=False, repr=False)

    def evaluate(self, hass: HomeAssistant) -> bool:
        """Return True if the rule's condition currently holds."""
        current = hass.states.get(self.entity_id)
        if current is None:
            _LOGGER.debug("Rule '%s': entity %s not found", self.name, self.entity_id)
            return False

        if self.state is not None:
            return current.state == self.state

        try:
            value = float(current.state)
        except (TypeError, ValueError):
            _LOGGER.debug(
                "Rule '%s': state of %s ('%s') is not numeric",
                self.name,
                self.entity_id,
                current.state,
            )
            return False

        if self.above is not None and value <= self.above:
            return False
        if self.below is not None and value >= self.below:
            return False
        return True

    def explanation(self, hass: HomeAssistant) -> str:
        if self.explain:
            return self.explain
        current = hass.states.get(self.entity_id)
        value = current.state if current else "desconhecido"
        return f"{self.entity_id} = {value}"


class RulesEngine:
    """Evaluates a set of rules on every scan and triggers their actions."""

    def __init__(self, hass: HomeAssistant, rules: list[Rule]) -> None:
        self._hass = hass
        self._rules = rules

    @property
    def rules(self) -> list[Rule]:
        return self._rules

    def replace_rules(self, rules: list[Rule]) -> None:
        """Swap in a new rule list — used when rules are added/removed via the UI."""
        self._rules = rules

    async def async_evaluate_all(self) -> None:
        """Evaluate every rule; call its service on a false→true transition."""
        for rule in self._rules:
            result = rule.evaluate(self._hass)

            if result and rule._last_result is not True:
                await self._async_trigger(rule)

            rule._last_result = result

    async def _async_trigger(self, rule: Rule) -> None:
        domain, _, service = rule.service.partition(".")
        if not domain or not service:
            _LOGGER.warning("Rule '%s': invalid service '%s'", rule.name, rule.service)
            return

        reason = rule.explanation(self._hass)
        _LOGGER.info("Smart Energy Controller: '%s' → %s (%s)", rule.name, rule.service, reason)

        await self._hass.services.async_call(domain, service, rule.service_data)

        self._hass.bus.async_fire(
            EVENT_DECISION,
            {
                "rule": rule.name,
                "service": rule.service,
                "reason": reason,
            },
        )
