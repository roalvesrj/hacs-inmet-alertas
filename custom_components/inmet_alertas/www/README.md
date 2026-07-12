# Plugin ha-map-card para INMET Alertas

Este plugin permite visualizar polígonos de alertas meteorológicos do INMET em mapas usando o ha-map-card.

## Instalação Automática

O plugin é instalado automaticamente quando você instala a integração INMET Alertas via HACS.

## Uso

```yaml
type: custom:map-card
title: "Alertas INMET"
zoom: 6
x: -15.7998  # Coordenada obrigatória
y: -47.8645  # Coordenada obrigatória

plugins:
  - name: inmet_polygons
    url: /hacsfiles/inmet_alertas/plugin_inmet_polygons.js  # URL automática
    options:
      states: ["rio_de_janeiro"]  # Seus estados
```

## Dependências

- Home Assistant
- HACS
- ha-map-card (instalado via HACS)
- Integração INMET Alertas

## Suporte

Para dúvidas sobre o plugin, abra um issue no repositório da integração INMET Alertas.