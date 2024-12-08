# INMET Alertas

**INMET Alertas** é uma integração personalizada para o Home Assistant que permite monitorar os alertas meteorológicos emitidos pelo INMET (Instituto Nacional de Meteorologia) através do feed RSS oficial. A integração exibe informações como o status, evento, severidade, início, fim e descrição do alerta.

## Funcionalidades

- Monitora automaticamente os alertas emitidos pelo INMET: [https://apiprevmet3.inmet.gov.br/avisos/rss](https://apiprevmet3.inmet.gov.br/avisos/rss)
- Exibe apenas alertas válidos, ou seja, que estão no período entre a data de início e de fim.
- Informa detalhes de cada alerta, incluindo:
  - **Alerta**: título do alerta.
  - **Evento**: tipo do evento meteorológico.
  - **Severidade**: nível de gravidade do alerta.
  - **Início**: data e hora do início da validade.
  - **Fim**: data e hora do fim da validade.
  - **Descrição**: resumo do alerta.
  - **Área**: área de cobertura do alerta.

## Requisitos

- **Home Assistant** instalado.
- O aiohttp é instalado automaticamente pela integração.

## Instalação

1. Clone ou baixe este repositório no diretório `custom_components` do seu Home Assistant:

   ```bash
   cd config/custom_components
   git clone https://github.com/roalvesrj/hacs-inmet-alertas

2. Reinicie o Home Assistant para que a integração seja carregada.

3. Adicione a configuração no arquivo configuration.yaml:
sensor:
  - platform: inmet_alertas

4. Reinicie o Home Assistant novamente.

Exibição no Lovelace

*Card de Alerta*

Use um card de Markdown no Lovelace para exibir os detalhes de cada alerta:
type: markdown
title: Alertas do INMET
content: >
  {% if state_attr('sensor.inmet_alertas', 'alertas') %}

  {% for alerta in state_attr('sensor.inmet_alertas', 'alertas') %} -
  **Alerta**: {{ alerta.status }}

  **Severidade**: {{ alerta.severidade }}

  **Evento**: {{ alerta.evento }}

  **Início**: {{ alerta.inicio }}

  **Fim**: {{ alerta.fim }}

  **Descrição**: {{ alerta.descricao }}

  **Área**: {{ alerta.area }}


  {% endfor %} {% else %} Nenhum alerta ativo no momento. {% endif %}

*Card de Contagem de Alertas*

Você também pode usar um card de entidades para exibir a contagem total de alertas:
type: entities
entities:
  - entity: sensor.inmet_alertas
    name: Total de Alertas


Como Funciona

    A integração utiliza o feed RSS oficial do INMET para obter os alertas.
    Somente os alertas válidos (com início e fim no período atual) são exibidos.
    Os alertas são armazenados como atributos do sensor sensor.inmet_alertas.

Contribuição

Sinta-se à vontade para abrir issues ou pull requests neste repositório. Sugestões e melhorias são bem-vindas!

Licença

Este projeto é distribuído sob a licença MIT. Consulte o arquivo LICENSE para mais detalhes.