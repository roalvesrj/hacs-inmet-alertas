# INMET Alertas - Home Assistant

<img src="custom_components/inmet_alertas/brand/icon.png" alt="INMET Logo" width="200"/>

[![GitHub release](https://img.shields.io/github/release/roalvesrj/hacs-inmet-alertas.svg)](https://github.com/roalvesrj/hacs-inmet-alertas/releases)
[![GitHub issues](https://img.shields.io/github/issues/roalvesrj/hacs-inmet-alertas.svg)](https://github.com/roalvesrj/hacs-inmet-alertas/issues)
[![License](https://img.shields.io/github/license/roalvesrj/hacs-inmet-alertas.svg)](LICENSE)
[![HACS](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/default)

Monitora alertas meteorológicos do INMET (Instituto Nacional de Meteorologia) no Home Assistant.

[![Abrir no Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?category=integration&repository=roalvesrj%2Fhacs-inmet-alertas)

---

## Funcionalidades

- Filtragem por estado brasileiro (ou múltiplos estados)
- 3 sensores por estado: alertas, contagem e mapa geográfico
- Notificações automáticas para Perigo e Grande Perigo
- Eventos para automações (`inmet_novo_alerta`, `inmet_alerta_perigoso`, `inmet_alerta_expirado`)
- Plugin para visualizar polígonos dos alertas no mapa (ha-map-card)
- Interface e documentação em português

## Instalação

1. No HACS, vá em **⋮ → Repositórios Personalizados** e adicione `https://github.com/roalvesrj/hacs-inmet-alertas`
2. Procure por **INMET Alertas** e instale
3. Reinicie o Home Assistant

Docs detalhadas: [Instalação](custom_components/inmet_alertas/docs/INSTALACAO.md) · [Configuração](custom_components/inmet_alertas/docs/CONFIGURACAO.md) · [Automações](custom_components/inmet_alertas/examples/automations.md)

## Configuração

**Configurações → Dispositivos e Serviços → Adicionar Integração → INMET Alertas**

- Selecione o estado
- Ative notificações para alertas Perigo/Grande Perigo (opcional)
- Ajuste o intervalo de atualização (5-120 min, padrão 30)

Para monitorar mais de um estado, repita o processo.

## Sensores

### `sensor.alertas_meteorologicos_[ESTADO]`
Estado: nome do alerta ativo ou "Nenhum alerta ativo".  
Atributos: `total_alertas`, `alertas`, `alertas_por_severidade`, `severidade_maxima`, `municipios_unicos`, `estado`, `ultima_atualizacao`.

### `sensor.quantidade_de_alertas_[ESTADO]`
Número de alertas ativos (unidade: alertas).

### `sensor.inmet_alertas_mapa_[ESTADO]`
Número de polígonos geográficos ativos.  
Atributos: `area_total_afetada_km2`, `centro_geografico`, `zoom_recomendado`, `camadas_por_severidade`, `total_alertas_com_geo`, `poligonos`.

## Eventos

| Evento | Quando |
|---|---|
| `inmet_novo_alerta` | Novo alerta detectado |
| `inmet_alerta_perigoso` | Alerta de Perigo ou Grande Perigo |
| `inmet_alerta_expirado` | Alerta removido por expiração |

```yaml
alert_id: "CAP-BR-INMET-000001"
titulo: "Chuvas Intensas"
severidade: "Perigo Potencial"
evento: "Chuva"
estado: "SP"
inicio: "21/09/2025 10:00"
fim: "21/09/2025 18:00"
```

## Serviços

`inmet_alertas.atualizar_alertas` — força a atualização. Parâmetro opcional: `estado`.

```yaml
service: inmet_alertas.atualizar_alertas
data:
  estado: "SP"
```

## Automação

Cole no editor de automações do Home Assistant:

```yaml
alias: Notificar Alerta INMET
trigger:
  - platform: event
    event_type: inmet_novo_alerta
condition:
  - condition: template
    value_template: "{{ trigger.event.data.severidade in ['Perigo', 'Grande Perigo'] }}"
action:
  - service: notify.mobile_app_meu_celular
    data:
      title: 🚨 Alerta Meteorológico
      message: "{{ trigger.event.data.titulo }} - {{ trigger.event.data.severidade }} em {{ trigger.event.data.estado }}"
mode: single
```

Mais exemplos em [`examples/automations.md`](custom_components/inmet_alertas/examples/automations.md).

## Interface Lovelace

### Cartão simples

```yaml
type: entities
title: Alertas Meteorológicos
entities:
  - sensor.alertas_meteorologicos_sp
  - sensor.quantidade_de_alertas_sp
```

### Cartão condicional com detalhes

```yaml
type: conditional
conditions:
  - entity: sensor.quantidade_de_alertas_sp
    state_not: "0"
card:
  type: markdown
  content: >
    {% for alerta in state_attr('sensor.alertas_meteorologicos_sp', 'alertas') %}
    ### {{ alerta.icone }} {{ alerta.titulo }}
    **Severidade:** {{ alerta.severidade }} · **Período:** {{ alerta.inicio }} até {{ alerta.fim }}
    {{ alerta.descricao }}
    ---
    {% endfor %}
```

### Mapa básico

```yaml
type: map
entities:
  - sensor.inmet_alertas_mapa_go
default_zoom: 8
```

### Mapa com polígonos reais

Instale o **ha-map-card** via HACS e use o plugin incluso na integração:

```yaml
type: custom:map-card
zoom: 6
x: -15.7998
y: -47.8645
plugins:
  - name: inmet_polygons
    url: /hacsfiles/inmet_alertas/plugin_inmet_polygons.js
    options:
      states: ["goias", "sao_paulo"]
```

## Solução de Problemas

- **Alertas não aparecem**: verifique o estado configurado e os logs em Configurações → Sistema → Logs (procure por `inmet_alertas`)
- **Notificações não funcionam**: confirme se estão habilitadas e se há alertas Perigo/Grande Perigo ativos
- **Logs de debug**: adicione ao `configuration.yaml`:
  ```yaml
  logger:
    logs:
      custom_components.inmet_alertas: debug
  ```

## Severidades

| Nível | Cor |
|---|---|
| Perigo Potencial | 🟡 Atenção |
| Perigo | 🟠 Cuidado |
| Grande Perigo | 🔴 Perigo |

## Licença

MIT. Veja o arquivo [LICENSE](LICENSE).

## Disclaimer

Integração não oficial, não afiliada ao INMET. Dados obtidos do feed RSS público do INMET.
