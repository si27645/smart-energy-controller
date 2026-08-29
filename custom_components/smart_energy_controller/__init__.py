"""The Smart Energy Controller integration.

Set up once via the UI (config flow); rules are added/removed afterwards
from Settings → Devices & Services → Configure — no YAML required. An
existing configuration.yaml is still accepted and imported automatically
into a config entry, for anyone upgrading from the pre-0.2 YAML-only setup.
"""
from __future__ import annotations

import logging
from datetime import timedelta

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval

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
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    SERVICE_EVALUATE_NOW,
)
from .rules_engine import Rule, RulesEngine

_LOGGER = logging.getLogger(__name__)

RULE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Required(CONF_SERVICE): cv.service,
        vol.Optional(CONF_ABOVE): vol.Coerce(float),
        vol.Optional(CONF_BELOW): vol.Coerce(float),
        vol.Optional(CONF_STATE): cv.string,
        vol.Optional(CONF_SERVICE_DATA, default={}): dict,
        vol.Optional(CONF_EXPLAIN): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL_SECONDS): cv.positive_int,
                vol.Required(CONF_RULES): vol.All(cv.ensure_list, [RULE_SCHEMA]),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Import configuration.yaml into a config entry, if present. No YAML → no-op."""
    if DOMAIN not in config:
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=config[DOMAIN],
        )
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Start the engine for this config entry, and keep it in sync with its options."""
    engine = RulesEngine(hass, _build_rules(entry))
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = engine

    scan_interval = timedelta(seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS))

    async def _async_scan(now=None) -> None:
        await engine.async_evaluate_all()

    entry.async_on_unload(async_track_time_interval(hass, _async_scan, scan_interval))
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    if not hass.services.has_service(DOMAIN, SERVICE_EVALUATE_NOW):

        async def _async_handle_evaluate_now(call: ServiceCall) -> None:
            for eng in hass.data.get(DOMAIN, {}).values():
                await eng.async_evaluate_all()

        hass.services.async_register(DOMAIN, SERVICE_EVALUATE_NOW, _async_handle_evaluate_now)

    _LOGGER.info(
        "Smart Energy Controller a correr com %d regra(s), a cada %ds",
        len(engine.rules),
        scan_interval.total_seconds(),
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Rebuild the rule list in place when a rule is added or removed via the UI."""
    engine: RulesEngine = hass.data[DOMAIN][entry.entry_id]
    engine.replace_rules(_build_rules(entry))


def _build_rules(entry: ConfigEntry) -> list[Rule]:
    return [
        Rule(
            name=r[CONF_NAME],
            entity_id=r[CONF_ENTITY_ID],
            service=r[CONF_SERVICE],
            above=r.get(CONF_ABOVE),
            below=r.get(CONF_BELOW),
            state=r.get(CONF_STATE),
            service_data=r.get(CONF_SERVICE_DATA) or {},
            explain=r.get(CONF_EXPLAIN),
        )
        for r in entry.options.get(CONF_RULES, [])
    ]
