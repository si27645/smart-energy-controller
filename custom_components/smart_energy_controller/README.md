# Smart Energy Controller — Home Assistant integration

Initial (Community/free) version: a deterministic, explainable rules engine.
Each rule watches **one sensor**, and when the condition becomes true, it calls
**one service** on a target entity — and always logs why.

## Installation (MVP — manual, ahead of HACS)

1. Copy the `custom_components/smart_energy_controller` folder into `<config>/custom_components/`.
2. Restart Home Assistant.
3. Settings → Devices & Services → Add Integration → "Smart Energy Controller".

No YAML needed — the integration is set up through the UI. A previous `configuration.yaml`-based setup still works: it's automatically imported into a config entry on first startup.

## Adding rules (via the UI)

Once the integration is set up: **Settings → Devices & Services → Smart Energy Controller → Configure → Add rule**.

Each rule asks for:

| Field | What it is |
|---|---|
| Rule name | So you can identify the rule in logs/events. |
| Entity to watch | The sensor whose condition will be tested (e.g. `sensor.solar_surplus_kw`). |
| Above / Below / State equals | The condition — set at least one. |
| Service to call | `domain.service`, e.g. `switch.turn_on`. |
| Target entity for the service | The entity the service acts on (e.g. `switch.wallbox_charging`) — distinct from the watched entity. Only optional for services with no target, like `notify.*`. |
| Explanation | Free text, optional — shown in the decision event. |

## Configuration example via YAML (legacy, still supported)

```yaml
smart_energy_controller:
  scan_interval: 60  # seconds between evaluations
  rules:
    - name: "Solar surplus → charge EV"
      entity_id: sensor.solar_surplus_kw
      above: 3.2
      service: switch.turn_on
      service_data:
        entity_id: switch.wallbox_charging
      explain: "Solar surplus above 3.2 kW"

    - name: "Battery > 80% → turn on water heater"
      entity_id: sensor.battery_soc
      above: 80
      service: switch.turn_on
      service_data:
        entity_id: switch.water_heater
      explain: "Battery above 80% charge"

    - name: "Low price at 03:00 → charge battery from the grid"
      entity_id: sensor.current_electricity_price
      below: 0.08
      service: switch.turn_on
      service_data:
        entity_id: switch.charge_battery_from_grid
      explain: "Electricity price below €0.08/kWh"
```

## Example for homes without a battery

Without a battery there's nowhere to "store" the surplus — so these rules use the water heater/heat pump as thermal storage, notify you for manual loads (washer/dishwasher), and still optimize EV charging by price, since the grid is the only buffer available. Create each one via the UI (see the table above) or by YAML:

```yaml
smart_energy_controller:
  scan_interval: 60
  rules:
    - name: "Solar surplus, no battery → heat water tank to the max"
      entity_id: sensor.solar_surplus_kw
      above: 1.5
      service: water_heater.set_temperature
      service_data:
        entity_id: water_heater.tank
        temperature: 65
      explain: "Solar surplus above 1.5 kW with no battery to store it — use it now"

    - name: "High solar surplus → notify to run washer/dishwasher"
      entity_id: sensor.solar_surplus_kw
      above: 2.5
      service: notify.mobile_app_your_phone
      service_data:
        message: "High solar surplus right now — good time to run the washer or dishwasher."
      explain: "Solar surplus above 2.5 kW"

    - name: "Low price at night → charge the EV straight from the grid"
      entity_id: sensor.current_electricity_price
      below: 0.08
      service: switch.turn_on
      service_data:
        entity_id: switch.wallbox_charging
      explain: "Price below €0.08/kWh — no battery to buffer, take the cheap grid price instead of the sun"
```

## Available services

- `smart_energy_controller.evaluate_now` — forces an immediate evaluation of all rules, without waiting for the next `scan_interval`.

## How to know why a decision was made

Every time a rule fires, the `smart_energy_controller_decision` event is emitted with `rule`, `service`, and `reason`. Use it in an automation to notify ("Smart Energy Controller turned on the water heater because the battery is at 84%") or log it to the `logbook`.

## Tests

Requires Python 3.12+ (`pytest-homeassistant-custom-component` tracks core HA's minimum Python version, newer than the rest of this project's):

```bash
python3.12 -m venv .venv-ha && source .venv-ha/bin/activate
pip install -r ../../tests/requirements.txt
python -m pytest ../../tests/ -q
```

Tests run against a real Home Assistant core (not mocked): setting up the integration via the UI, adding/removing rules, importing legacy YAML, and the service actually firing on the right target entity.

## Roadmap for this integration

- [x] Deterministic rules engine (thresholds and state).
- [x] `config_flow` — set up and manage rules through the UI, no YAML.
- [ ] Solar forecasts (Forecast.Solar) and dynamic prices (OMIE) as a condition — already exist in the [Cloud Optimizer](../../cloud-service/README.md), just need wiring in here.
- [ ] Lovelace card with a visual explanation of each decision.
- [ ] Publish to HACS.

See more in the [project's main README](../../README.md).
