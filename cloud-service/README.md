# ☁️ Cloud Optimizer

O único serviço do produto que corre fora de casa do utilizador: agrega previsão solar + preço dinâmico e calcula um plano do dia seguinte, para os dois perfis (com e sem bateria). O motor local (`custom_components/`) continua gratuito e funcional sem isto — este serviço é o que sustenta o plano opcional **Cloud Copilot**, que existe porque agregar e otimizar estes dados exige infraestrutura contínua, ao contrário da lógica que corre em casa do utilizador.

## Correr localmente

```bash
cd cloud-service
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Testes (sem rede, dados sintéticos + um ficheiro OMIE real capturado como fixture):

```bash
python -m pytest -q
```

## Endpoints

| Endpoint | O que faz |
|---|---|
| `GET /health` | Verificação simples. |
| `GET /forecast/solar?lat=&lon=&declination=&azimuth=&kwp=` | Previsão solar horária (kW), via [Forecast.Solar](https://doc.forecast.solar/) (API pública, sem chave, limitada a ~12 pedidos/hora por IP). |
| `GET /prices/omie?market=pt` | Preços horários do mercado ibérico (€/kWh), via ficheiro público diário da OMIE. |
| `POST /optimize` | Recebe previsão solar + preços + consumo + cargas flexíveis (+ bateria, opcional) e devolve o plano das 24h, com uma razão por decisão. |

Testado com dados reais ao vivo em 2026-08-30 — os três endpoints e o `/optimize` de ponta a ponta (previsão solar real → preços OMIE reais → plano otimizado) funcionaram tal como documentado abaixo.

### Exemplo de pedido a `/optimize`

```json
{
  "profile": "with_battery",
  "solar_forecast_kw": [0, 0, 0, 0, 0, 0, 0, 0, 0.3, 0.6, 1.1, 1.7, 1.8, 1.8, 2.3, 2.5, 2.4, 1.9, 1.3, 0.7, 0.2, 0, 0, 0],
  "price_eur_per_kwh": [0.18, 0.18, 0.20, 0.20, 0.20, 0.18, 0.18, 0.18, 0.18, 0.18, 0.18, 0.18, 0.18, 0.18, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17, 0.17],
  "consumption_kw": [0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.5, 0.8, 0.5, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.5, 0.8, 1.2, 1.5, 1.2, 0.9, 0.6, 0.4, 0.3],
  "flexible_loads": [{"name": "EV", "energy_kwh": 8, "power_kw": 3.6, "earliest_hour": 8, "deadline_hour": 20}],
  "battery": {"capacity_kwh": 10, "soc_pct": 30, "max_charge_kw": 3, "max_discharge_kw": 3, "reserve_soc_pct": 20}
}
```

Para o perfil sem bateria, basta omitir `battery` e pôr `"profile": "without_battery"` — as cargas flexíveis (termoacumulador, EV, etc.) continuam a ser otimizadas por excedente solar primeiro, preço mais barato depois.

## Como funciona o otimizador

Heurística gulosa e explicável (não um modelo opaco), em [`app/optimizer/engine.py`](app/optimizer/engine.py):

1. **Cargas flexíveis primeiro**, mais urgentes (deadline mais cedo) primeiro: cada uma tenta encaixar nas horas com excedente solar sobrante; o que faltar vai para as horas mais baratas da janela.
2. **Bateria** (só no perfil `with_battery`): carrega do excedente solar que sobrou, depois completa da rede nas horas mais baratas do dia, e descarrega nas horas mais caras que ainda têm défice por cobrir — nunca abaixo da reserva mínima configurada.

Cada hora do plano vem com uma frase em português a explicar a decisão — o mesmo princípio de explicabilidade do motor local.

## Limitações conhecidas (MVP)

- **Sem mistura parcial dentro da hora**: se a carga (ex.: EV a 3.6 kW) excede o excedente solar instantâneo (ex.: 2 kW), a hora inteira cai para a lógica de preço em vez de aproveitar os 2 kW grátis e comprar só a diferença. Visto isto em teste real — o EV do exemplo acima nunca usou solar porque a produção de pico (~2.5 kW) nunca chegou aos 3.6 kW da wallbox.
- **Heurística gulosa, não um solver ótimo global**: pode encher a bateria mais do que o necessário se não houver um défice caro mais tarde no dia para justificar. Prioriza-se a explicabilidade sobre a otimalidade absoluta — decisão consciente, não um bug.
- **Ordem das colunas do ficheiro OMIE (Espanha/Portugal) não está documentada pela própria OMIE** — o parser assume uma ordem por omissão; confirmar antes de usar em produção (ver comentário em [`app/providers/price_feed.py`](app/providers/price_feed.py)).
- **Forecast.Solar gratuito**: só cobre hoje/amanhã e tem limite de pedidos — adequado para um plano diário, não para histórico.
- Só planeia **um dia** de cada vez — não olha para o dia seguinte ao decidir "poupar a bateria para amanhã" (isso ainda vive como regra separada no motor local).
