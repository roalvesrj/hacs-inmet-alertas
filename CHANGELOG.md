# Changelog

## v1.13.1 - 17/07/2026

### 🐛 Correções de Erros
- Corrigido import incorreto em `__init__.py` que impedia a integração de carregar no Home Assistant (`voluptuous.as cv` → `homeassistant.helpers.config_validation as cv`)

## v1.13.0 - 16/07/2026

### ✨ Novos Recursos
- Suporte a repositório oficial HACS - estrutura de publicação oficial
- `hacs.json` com configurações para descoberta no HACS
- `brand/icon.png` - logotipo nos padrões Home Assistant

### 🐛 Correções de Erros
- README duplicado removido de dentro da pasta `custom_components/`
- Caminho da logo corrigido (agora aponta para `brand/icon.png`)
- Documentação atualizada com sensores de mapa e eventos faltantes

## v1.12.0

### ✨ Novos Recursos
- **Sensor de Mapa Geográfico** - `sensor.inmet_alertas_mapa_[estado]` para cada estado configurado
- **Polígonos Reais** - extração automática de coordenadas geográficas dos alertas INMET
- **Cálculo de Área** - área total afetada em km² usando algoritmo Shoelace
- **Zoom Inteligente** - zoom automático ideal para visualização no mapa
- **Plugin Leaflet** - `plugin_inmet_polygons.js` para ha-map-card com cores por severidade
- **Camadas por Severidade** - polígonos organizados por Grande Perigo, Perigo e Perigo Potencial

### 🐛 Correções de Erros
- Notificações duplicadas entre estados resolvidas
- Rate limiting tratado com fila de retry inteligente
- Persistência de alertas entre ciclos de atualização mantida
- Limpeza automática de notificações expiradas
- Terminologia de severidade padronizada (Perigo, Grande Perigo)

## v1.7.0

### ✨ Novos Recursos
- Arquitetura modular com helpers especializados (RSSParser, DataProcessor, NotificationManager)
- Documentação expandida em pasta dedicada (`docs/`)
- Suporte multilíngue (Português e Inglês)
- Testes automatizados organizados em estrutura própria
- Eventos personalizados (`inmet_novo_alerta`, `inmet_alerta_perigoso`)
- Constantes centralizadas para melhor manutenção
- Serviço `atualizar_alertas` para atualização manual

### 🐛 Correções de Erros
- Logs estruturados para facilitar troubleshooting
- Tratamento robusto de erros em todas as operações com RSS

## v1.0.2

### ✨ Novos Recursos
- Primeira versão pública da integração
- Monitoramento em tempo real de alertas do INMET
- Configuração por estado brasileiro
- Sensor principal com detalhes dos alertas
- Sensor de contagem de alertas
- Suporte a múltiplos estados
- Notificações persistentes para alertas de Perigo e Grande Perigo
- Interface em português brasileiro
- Integração via HACS (repositório personalizado)
