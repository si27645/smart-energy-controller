"""End-to-end test of the config flow + options flow against a real Home
Assistant core (not mocked) — proves the UI setup actually wires the engine
up and that adding a rule from the UI makes it fire.
"""
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smart_energy_controller.const import DOMAIN


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] == "form"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"scan_interval": 30})
    assert result["type"] == "create_entry"
    assert result["options"]["scan_interval"] == 30
    assert result["options"]["rules"] == []


async def test_only_one_instance_allowed(hass: HomeAssistant) -> None:
    MockConfigEntry(domain=DOMAIN, options={"scan_interval": 60, "rules": []}).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    assert result["type"] == "abort"
    assert result["reason"] == "single_instance_allowed"


async def test_add_rule_via_options_flow_triggers_the_service(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, options={"scan_interval": 60, "rules": []})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    hass.states.async_set("sensor.excedente_solar_kw", "5.0")
    hass.states.async_set("switch.wallbox_carregamento", "off")

    calls = []
    hass.services.async_register("switch", "turn_on", lambda call: calls.append(call))

    menu = await hass.config_entries.options.async_init(entry.entry_id)
    assert menu["type"] == "menu"

    form = await hass.config_entries.options.async_configure(menu["flow_id"], {"next_step_id": "add_rule"})
    assert form["type"] == "form"
    assert form["step_id"] == "add_rule"

    result = await hass.config_entries.options.async_configure(
        form["flow_id"],
        {
            "name": "Excedente solar → carregar EV",
            "entity_id": "sensor.excedente_solar_kw",
            "above": 3.2,
            "service": "switch.turn_on",
            "target_entity_id": "switch.wallbox_carregamento",
        },
    )
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()

    assert entry.options["rules"][0]["name"] == "Excedente solar → carregar EV"
    assert entry.options["rules"][0]["service_data"] == {"entity_id": "switch.wallbox_carregamento"}

    engine = hass.data[DOMAIN][entry.entry_id]
    await engine.async_evaluate_all()
    await hass.async_block_till_done()

    # The service must fire on the chosen target, not blindly on every switch.
    assert len(calls) == 1
    assert calls[0].data["entity_id"] == "switch.wallbox_carregamento"


async def test_add_rule_without_condition_shows_error(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, options={"scan_interval": 60, "rules": []})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    menu = await hass.config_entries.options.async_init(entry.entry_id)
    form = await hass.config_entries.options.async_configure(menu["flow_id"], {"next_step_id": "add_rule"})

    result = await hass.config_entries.options.async_configure(
        form["flow_id"],
        {"name": "Regra sem condição", "entity_id": "sensor.x", "service": "switch.turn_on"},
    )

    assert result["type"] == "form"
    assert result["errors"]["base"] == "condition_required"


async def test_remove_rule_via_options_flow(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        options={
            "scan_interval": 60,
            "rules": [{"name": "Regra A", "entity_id": "sensor.x", "above": 1, "service": "switch.turn_on"}],
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    menu = await hass.config_entries.options.async_init(entry.entry_id)
    form = await hass.config_entries.options.async_configure(menu["flow_id"], {"next_step_id": "remove_rule"})
    assert form["step_id"] == "remove_rule"

    result = await hass.config_entries.options.async_configure(form["flow_id"], {"rule": ["0"]})
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()

    assert entry.options["rules"] == []


async def test_yaml_config_is_imported_into_a_config_entry(hass: HomeAssistant) -> None:
    from custom_components.smart_energy_controller import async_setup

    config = {
        DOMAIN: {
            "scan_interval": 45,
            "rules": [{"name": "Regra YAML", "entity_id": "sensor.x", "above": 1, "service": "switch.turn_on"}],
        }
    }
    assert await async_setup(hass, config)
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].options["scan_interval"] == 45
    assert entries[0].options["rules"][0]["name"] == "Regra YAML"
