# ⚡ Smart Energy Controller

> O "cérebro" que falta às casas com solar: decide sozinho quando carregar o carro, ligar o termoacumulador ou poupar a bateria — com base na produção solar, no preço da eletricidade e no que já tens em casa.

Motor de decisão energética para [Home Assistant](https://www.home-assistant.io/), com ou sem bateria. Liga-se ao inversor, à wallbox e à bomba de calor que já tens, e decide automaticamente coisas como:

- "Tenho 3,2 kW de excedente solar → carregar o EV."
- "Bateria > 80% → ligar o termoacumulador."
- "Preço da eletricidade às 03:00 é baixo → carregar a bateria (ou o EV) da rede."
- "Sem bateria e há excedente agora → aquecer o termoacumulador ao máximo em vez de o injetar de graça na rede."

Cada decisão vem com uma explicação — nunca é uma caixa preta.

## Porque existe isto

Home Assistant já te dá os dados todos (produção solar, SoC da bateria, tarifário). O que falta é alguém a juntar esses dados e a agir sobre eles em tempo real, sem teres de escrever e manter dezenas de automações YAML. É isso que este projeto faz.

## Estrutura do repositório

| Pasta | O que é |
|---|---|
| [`custom_components/smart_energy_controller/`](custom_components/smart_energy_controller/README.md) | A integração de Home Assistant — motor de regras local, grátis e open-source. Configura-se pela interface (`config_flow`), sem YAML. |
| [`cloud-service/`](cloud-service/README.md) | Serviço opcional (Cloud Copilot): agrega previsão solar (Forecast.Solar) + preços dinâmicos (OMIE) e calcula um plano otimizado do dia seguinte. |
| [`website/`](website/index.html) | Landing page do produto. |

## Instalação rápida

1. Copia `custom_components/smart_energy_controller/` para `<config>/custom_components/` na tua instalação de Home Assistant.
2. Reinicia o Home Assistant.
3. Definições → Dispositivos e Serviços → Adicionar integração → **Smart Energy Controller**.
4. Configurar → Adicionar regra.

Detalhes, exemplos de configuração (com e sem bateria) e a lista de serviços disponíveis: [custom_components/smart_energy_controller/README.md](custom_components/smart_energy_controller/README.md).

## Com bateria ou sem bateria — o motor adapta-se

Nem toda a casa com solar tem bateria. O motor não assume que existe:

- **Com bateria**: otimiza carga/descarga (quando encher da rede, quando poupar para a noite).
- **Sem bateria**: usa o termoacumulador e a bomba de calor como "bateria térmica" — aquece água/casa sempre que há excedente, em vez de o injetar de graça na rede — e continua a otimizar o carregamento do EV pelo preço.

## Integrações

FoxESS · Victron · Shelly · Wallbox (ou OpenEVSE / go-eCharger) · bombas de calor via Home Assistant · OMIE / Indexa (tarifário dinâmico). Nenhuma é obrigatória — o motor usa o que existir.

## Diferenciação

- **[EVCC](https://evcc.io/)** — ótimo para carregamento EV, mas foco estreito no EV, sem motor central multi-dispositivo.
- **Soluções proprietárias** (Solar Manager e semelhantes) — fechadas a um ecossistema, não integram com o Home Assistant.
- **HA Energy Dashboard nativo** — mostra dados, não decide nada sozinho.

## Grátis e open-source, com um add-on cloud opcional

O motor de regras (`custom_components/`) é **grátis para sempre** e corre inteiramente local — os teus dados de consumo não saem de casa. O [Cloud Optimizer](cloud-service/README.md) é um serviço opcional à parte, para quem quer previsão agregada e um otimizador real do dia seguinte em vez de só limiares. Não é preciso para o motor local funcionar.

## Testes

```bash
# Motor de regras / cloud-service — Python 3.9+
cd cloud-service && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pytest -q

# Integração Home Assistant — requer Python 3.12+ (pytest-homeassistant-custom-component)
python3.12 -m venv .venv-ha && source .venv-ha/bin/activate
pip install -r tests/requirements.txt && pytest tests/ -q
```

## Contribuir

Issues e PRs são bem-vindos. O CI (`.github/workflows/validate.yml`) corre `hacs/action`, `hassfest` e os testes de integração em cada push.

## Licença

[MIT](LICENSE)
