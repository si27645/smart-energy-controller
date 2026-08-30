# ⚡ Smart Energy Controller

> The "brain" solar homes are missing: decides on its own when to charge the car, turn on the water heater, or save the battery — based on solar production, electricity price, and what's already in your home.

A decision engine for [Home Assistant](https://www.home-assistant.io/), with or without a battery. Connects to the inverter, wallbox, and heat pump you already have, and automatically decides things like:

- "I have 3.2 kW of solar surplus → charge the EV."
- "Battery > 80% → turn on the water heater."
- "Electricity price at 03:00 is low → charge the battery (or the EV) from the grid."
- "No battery and there's surplus right now → heat the water tank to the max instead of exporting it to the grid for nothing."

Every decision comes with an explanation — never a black box.

## Why this exists

Home Assistant already gives you all the data (solar production, battery SoC, tariff). What's missing is something that pulls that data together and acts on it in real time, without you having to write and maintain dozens of YAML automations. That's what this project does.

## Repository layout

| Folder | What it is |
|---|---|
| [`custom_components/smart_energy_controller/`](custom_components/smart_energy_controller/README.md) | The Home Assistant integration — the local rules engine, free and open-source. Set up via the UI (`config_flow`), no YAML required. |
| [`cloud-service/`](cloud-service/README.md) | Optional service (Cloud Copilot): aggregates solar forecasts (Forecast.Solar) + dynamic prices (OMIE) and computes an optimized day-ahead plan. |
| [`website/`](website/index.html) | Product landing page. |

## Quick install

1. Copy `custom_components/smart_energy_controller/` into `<config>/custom_components/` on your Home Assistant instance.
2. Restart Home Assistant.
3. Settings → Devices & Services → Add Integration → **Smart Energy Controller**.
4. Configure → Add rule.

Details, configuration examples (with and without a battery), and the list of available services: [custom_components/smart_energy_controller/README.md](custom_components/smart_energy_controller/README.md).

## With a battery or without — the engine adapts

Not every solar home has a battery. The engine doesn't assume one exists:

- **With a battery**: optimizes charge/discharge (when to top up from the grid, when to save for the night).
- **Without a battery**: uses the water heater and heat pump as a "thermal battery" — heats water/the house whenever there's surplus, instead of exporting it to the grid for nothing — and still optimizes EV charging by price.

## Integrations

FoxESS · Victron · Shelly · Wallbox (or OpenEVSE / go-eCharger) · heat pumps via Home Assistant · OMIE / Indexa (dynamic tariffs). None are required — the engine uses whatever exists.

## Differentiation

- **[EVCC](https://evcc.io/)** — great for EV charging, but narrowly focused on EVs, with no central multi-device engine.
- **Proprietary solutions** (Solar Manager and similar) — closed to a single ecosystem, don't integrate with Home Assistant.
- **Native HA Energy Dashboard** — shows data, doesn't decide anything on its own.

## Free and open-source, with an optional cloud add-on

The rules engine (`custom_components/`) is **free forever** and runs entirely locally — your consumption data never leaves your home. The [Cloud Optimizer](cloud-service/README.md) is a separate, optional service, for anyone who wants aggregated forecasts and a real day-ahead optimizer instead of just thresholds. It isn't required for the local engine to work.

## Tests

```bash
# Rules engine / cloud-service — Python 3.9+
cd cloud-service && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pytest -q

# Home Assistant integration — requires Python 3.12+ (pytest-homeassistant-custom-component)
python3.12 -m venv .venv-ha && source .venv-ha/bin/activate
pip install -r tests/requirements.txt && python -m pytest tests/ -q
```

## HACS publishing status

- [x] Structure, `manifest.json`, `hacs.json`, `LICENSE`, and validation CI (`hacs/action` + `hassfest`).
- [x] `config_flow` — no YAML required.
- [ ] **Icon/logo in [home-assistant/brands](https://github.com/home-assistant/brands)** — external process with manual review by the Home Assistant team; until then, `hacs/action` deliberately ignores this check (`ignore: brands` in the workflow).
- [ ] Submission to [hacs/default](https://github.com/hacs/default) to show up in HACS search without pasting the repository URL.

Until those last two are sorted, install it as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories/) in HACS.

## Contributing

Issues and PRs are welcome. CI (`.github/workflows/validate.yml`) runs `hacs/action`, `hassfest`, and the integration tests on every push.

## License

[MIT](LICENSE)
