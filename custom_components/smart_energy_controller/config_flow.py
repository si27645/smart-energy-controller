"""Config flow: set up once via the UI, then add/remove rules as options.

No YAML required. Existing configuration.yaml setups are imported
automatically into a config entry the first time Home Assistant starts
(see `async_step_import` and `async_setup` in __init__.py).
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ABOVE,
    CONF_BELOW,
    CONF_ENTITY_ID,
    CONF_EXPLAIN,
    CONF_NAME,
    CONF_RULES,
    CONF_SCAN_INTERVAL,
    CONF_SERVICE,
    CONF_SERVICE_DATA,
    CONF_STATE,
    CONF_TARGET_ENTITY_ID,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
)


class SmartEnergyControllerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """One config entry per Home Assistant install — the engine runs all rules together."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(
                title="Smart Energy Controller",
                data={},
                options={CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL], CONF_RULES: []},
            )

        schema = vol.Schema({vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL_SECONDS): int})
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_import(self, import_config: dict[str, Any]) -> config_entries.ConfigFlowResult:
        """Import configuration.yaml (back-compat) into a config entry."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        return self.async_create_entry(
            title="Smart Energy Controller (YAML)",
            data={},
            options={
                CONF_SCAN_INTERVAL: import_config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS),
                CONF_RULES: import_config.get(CONF_RULES, []),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "SmartEnergyControllerOptionsFlow":
        return SmartEnergyControllerOptionsFlow()


class SmartEnergyControllerOptionsFlow(config_entries.OptionsFlow):
    """Add or remove rules from the UI — Settings → Devices & Services → Configure."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        return self.async_show_menu(step_id="init", menu_options=["add_rule", "remove_rule"])

    async def async_step_add_rule(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if not any(user_input.get(k) not in (None, "") for k in (CONF_ABOVE, CONF_BELOW, CONF_STATE)):
                errors["base"] = "condition_required"
            else:
                target = user_input.get(CONF_TARGET_ENTITY_ID)
                rules = list(self.config_entry.options.get(CONF_RULES, []))
                rules.append(
                    {
                        CONF_NAME: user_input[CONF_NAME],
                        CONF_ENTITY_ID: user_input[CONF_ENTITY_ID],
                        CONF_ABOVE: user_input.get(CONF_ABOVE),
                        CONF_BELOW: user_input.get(CONF_BELOW),
                        CONF_STATE: user_input.get(CONF_STATE) or None,
                        CONF_SERVICE: user_input[CONF_SERVICE],
                        CONF_SERVICE_DATA: {"entity_id": target} if target else {},
                        CONF_EXPLAIN: user_input.get(CONF_EXPLAIN) or None,
                    }
                )
                new_options = dict(self.config_entry.options)
                new_options[CONF_RULES] = rules
                return self.async_create_entry(title="", data=new_options)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_ENTITY_ID): selector.EntitySelector(),
                vol.Optional(CONF_ABOVE): vol.Coerce(float),
                vol.Optional(CONF_BELOW): vol.Coerce(float),
                vol.Optional(CONF_STATE): str,
                # There is no dedicated "pick a service" selector in HA core —
                # only the full action/target selectors, which capture far more
                # than the plain "domain.service" string this engine calls.
                vol.Required(CONF_SERVICE): selector.TextSelector(),
                # The entity the service acts ON — distinct from entity_id above,
                # which is the sensor the *condition* watches. Optional because
                # some services (e.g. notify.*) don't take an entity target.
                vol.Optional(CONF_TARGET_ENTITY_ID): selector.EntitySelector(),
                vol.Optional(CONF_EXPLAIN): str,
            }
        )
        return self.async_show_form(step_id="add_rule", data_schema=schema, errors=errors)

    async def async_step_remove_rule(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        rules = self.config_entry.options.get(CONF_RULES, [])
        if not rules:
            return self.async_abort(reason="no_rules")

        labels = {str(i): rule[CONF_NAME] for i, rule in enumerate(rules)}
        if user_input is not None:
            keep = [rule for i, rule in enumerate(rules) if str(i) not in user_input["rule"]]
            new_options = dict(self.config_entry.options)
            new_options[CONF_RULES] = keep
            return self.async_create_entry(title="", data=new_options)

        schema = vol.Schema(
            {
                vol.Required("rule"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[{"value": k, "label": v} for k, v in labels.items()],
                        multiple=True,
                    )
                )
            }
        )
        return self.async_show_form(step_id="remove_rule", data_schema=schema)
