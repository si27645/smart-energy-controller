# Smart Energy Controller — integração para Home Assistant

Versão inicial (Community/free): motor de regras determinísticas e explicáveis.
Cada regra observa **um sensor** e, quando a condição passa a verdadeira, chama
**um serviço** do Home Assistant sobre uma entidade alvo — e regista sempre o porquê.

## Instalação (MVP — manual, antes do HACS)

1. Copia a pasta `custom_components/smart_energy_controller` para `<config>/custom_components/`.
2. Reinicia o Home Assistant.
3. Definições → Dispositivos e Serviços → Adicionar integração → "Smart Energy Controller".

Não precisas de YAML — a integração cria-se pela interface. Uma instalação anterior baseada em `configuration.yaml` continua a funcionar: é importada automaticamente para uma entrada de configuração no primeiro arranque.

## Adicionar regras (pela interface)

Depois de criada a integração: **Definições → Dispositivos e Serviços → Smart Energy Controller → Configurar → Adicionar regra**.

Cada regra pede:

| Campo | O que é |
|---|---|
| Nome da regra | Para identificares a regra nos logs/eventos. |
| Entidade a observar | O sensor cuja condição vai ser testada (ex.: `sensor.excedente_solar_kw`). |
| Acima de / Abaixo de / Estado igual a | A condição — define pelo menos uma. |
| Serviço a chamar | `domain.service`, ex.: `switch.turn_on`. |
| Entidade alvo do serviço | A entidade sobre a qual o serviço atua (ex.: `switch.wallbox_carregamento`) — distinta da entidade observada. Opcional só para serviços sem alvo, como `notify.*`. |
| Explicação | Texto livre, opcional — aparece no evento de decisão. |

## Exemplo de configuração via YAML (legado, ainda suportado)

```yaml
smart_energy_controller:
  scan_interval: 60  # segundos entre avaliações
  rules:
    - name: "Excedente solar → carregar EV"
      entity_id: sensor.excedente_solar_kw
      above: 3.2
      service: switch.turn_on
      service_data:
        entity_id: switch.wallbox_carregamento
      explain: "Excedente solar acima de 3.2 kW"

    - name: "Bateria > 80% → ligar termoacumulador"
      entity_id: sensor.bateria_soc
      above: 80
      service: switch.turn_on
      service_data:
        entity_id: switch.termoacumulador
      explain: "Bateria com mais de 80% de carga"

    - name: "Preço baixo às 03:00 → carregar bateria da rede"
      entity_id: sensor.preco_eletricidade_atual
      below: 0.08
      service: switch.turn_on
      service_data:
        entity_id: switch.carregar_bateria_rede
      explain: "Preço da eletricidade abaixo de 0.08 €/kWh"
```

## Exemplo para quem não tem bateria

Sem bateria não há onde "guardar" o excedente — por isso as regras usam o termoacumulador/bomba de calor como reserva térmica, notificam para cargas manuais (máquina de lavar/loiça) e continuam a otimizar o EV pelo preço, já que aí a rede é a única reserva disponível. Cria cada uma pela interface (ver tabela acima) ou por YAML:

```yaml
smart_energy_controller:
  scan_interval: 60
  rules:
    - name: "Excedente solar sem bateria → aquecer termoacumulador ao máximo"
      entity_id: sensor.excedente_solar_kw
      above: 1.5
      service: water_heater.set_temperature
      service_data:
        entity_id: water_heater.termoacumulador
        temperature: 65
      explain: "Excedente solar acima de 1.5 kW e sem bateria para o guardar — aproveitar agora"

    - name: "Excedente solar alto → avisar para ligar máquina de lavar/loiça"
      entity_id: sensor.excedente_solar_kw
      above: 2.5
      service: notify.mobile_app_o_teu_telemovel
      service_data:
        message: "Excedente solar alto agora — boa altura para ligar a máquina de lavar ou loiça."
      explain: "Excedente solar acima de 2.5 kW"

    - name: "Preço baixo à noite → carregar o EV direto da rede"
      entity_id: sensor.preco_eletricidade_atual
      below: 0.08
      service: switch.turn_on
      service_data:
        entity_id: switch.wallbox_carregamento
      explain: "Preço abaixo de 0.08 €/kWh — sem bateria a amortecer, aproveita-se o preço em vez do sol"
```

## Serviços disponíveis

- `smart_energy_controller.evaluate_now` — força uma avaliação imediata de todas as regras, sem esperar pelo próximo `scan_interval`.

## Como saber porque uma decisão foi tomada

Cada vez que uma regra dispara, é emitido o evento `smart_energy_controller_decision` com `rule`, `service` e `reason`. Podes usá-lo num automation para notificar ("O Smart Energy Controller ligou o termoacumulador porque a bateria está a 84%") ou registar num `logbook`.

## Testes

Requer Python 3.12+ (o `pytest-homeassistant-custom-component` acompanha a versão mínima do core, mais recente do que a do resto do projeto):

```bash
python3.12 -m venv .venv-ha && source .venv-ha/bin/activate
pip install -r ../../tests/requirements.txt
python -m pytest ../../tests/ -q
```

Os testes correm contra um Home Assistant core real (não simulado): criação da integração pela UI, adicionar/remover regras, importação de YAML legado, e o disparo efetivo do serviço na entidade alvo certa.

## Roadmap desta integração

- [x] Motor de regras determinísticas (limiares e estado).
- [x] `config_flow` — configuração e gestão de regras pela interface, sem YAML.
- [ ] Previsão solar (Forecast.Solar) e preços dinâmicos (OMIE) como condição — já existem no [Cloud Optimizer](../../cloud-service/README.md), falta ligar aqui.
- [ ] Card Lovelace com explicação visual de cada decisão.
- [ ] Publicação no HACS.

Ver mais no [README principal do projeto](../../README.md).
