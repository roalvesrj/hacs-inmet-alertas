# INMET Alertas - Integração Home Assistant

![INMET Logo](https://www.gov.br/inmet/pt-br/central-de-conteudos/logomarca/logo-inmet.png/@@images/image.png)

[![GitHub release](https://img.shields.io/github/release/roalvesrj/hacs-inmet-alertas.svg)](https://github.com/roalvesrj/hacs-inmet-alertas/releases)
[![GitHub issues](https://img.shields.io/github/issues/roalvesrj/hacs-inmet-alertas.svg)](https://github.com/roalvesrj/hacs-inmet-alertas/issues)
[![License](https://img.shields.io/github/license/roalvesrj/hacs-inmet-alertas.svg)](LICENSE)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

Uma integração profissional para Home Assistant que monitora alertas meteorológicos do Instituto Nacional de Meteor   - 🔴 **Grande Perigo**: Vermelho
   - 🟠 **Perigo**: Laranja  
   - 🟡 **Perigo Potencial**: Amarelo

## 🤖 Automações Geográficas Avançadas

### 📍 Automação por Área Afetada

```yaml
alias: "Alerta INMET - Grande Área Afetada"
description: "Notifica quando área afetada ultrapassa limite"
trigger:
  - platform: numeric_state
    entity_id: sensor.inmet_alertas_mapa_go
    attribute: area_total_afetada_km2
    above: 10000  # 10.000 km²
condition:
  - condition: template
    value_template: "{{ states('sensor.inmet_alertas_mapa_go') | int > 0 }}"
action:
  - service: notify.family_group
    data:
      title: "🚨 Alerta de Grande Área"
      message: >
        ⚠️ Área significativa sob alerta meteorológico!
        
        📐 Área afetada: {{ state_attr('sensor.inmet_alertas_mapa_go', 'area_total_afetada_km2') }} km²
        🗺️ Polígonos ativos: {{ states('sensor.inmet_alertas_mapa_go') }}
        📍 Centro: {{ state_attr('sensor.inmet_alertas_mapa_go', 'centro_geografico') }}
        
        Verifique o mapa para detalhes!
mode: single
```

### 🎯 Automação por Múltiplos Polígonos

```yaml
alias: "Alerta INMET - Múltiplas Áreas"
description: "Notifica quando múltiplos polígonos estão ativos"
trigger:
  - platform: numeric_state
    entity_id: sensor.inmet_alertas_mapa_go
    above: 3  # 3 ou mais polígonos
action:
  - service: script.preparar_emergencia_meteorologica  # Script personalizado
  - service: notify.mobile_app_meu_celular
    data:
      title: "🌪️ Situação Meteorológica Complexa"
      message: >
        🚨 {{ states('sensor.inmet_alertas_mapa_go') }} áreas sob alerta simultâneo!
        
        {% set camadas = state_attr('sensor.inmet_alertas_mapa_go', 'camadas_por_severidade') %}
        {% if camadas %}
        {% for severidade, dados in camadas.items() %}
        {% if dados.total_poligonos > 0 %}
        {{ '🔴' if severidade == 'Grande Perigo' else '🟠' if severidade == 'Perigo' else '🟡' }} {{ severidade }}: {{ dados.total_poligonos }} áreas
        {% endif %}
        {% endfor %}
        {% endif %}
        
        📐 Total: {{ state_attr('sensor.inmet_alertas_mapa_go', 'area_total_afetada_km2') }} km²
      data:
        channel: "emergency"
        importance: high
mode: single
```

### 🔴 Automação por Severidade Geográfica

```yaml
alias: "Alerta INMET - Grande Perigo Geográfico"
description: "Ação especial para alertas de Grande Perigo com dados geográficos"
trigger:
  - platform: template
    value_template: >
      {{ state_attr('sensor.inmet_alertas_mapa_go', 'camadas_por_severidade.Grande Perigo.total_poligonos') | int > 0 }}
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
    data:
      color_name: red
      brightness: 255
      
  - service: media_player.speak
    target:
      entity_id: media_player.google_home
    data:
      message: >
        Atenção! Alerta meteorológico de grande perigo detectado. 
        {{ state_attr('sensor.inmet_alertas_mapa_go', 'camadas_por_severidade.Grande Perigo.total_poligonos') }} 
        áreas afetadas cobrindo 
        {{ state_attr('sensor.inmet_alertas_mapa_go', 'camadas_por_severidade.Grande Perigo.area_total_km2') }} 
        quilômetros quadrados.
        
  - service: notify.persistent_notification.create
    data:
      title: "🔴 GRANDE PERIGO METEOROLÓGICO"
      message: >
        **SITUAÇÃO CRÍTICA DETECTADA**
        
        🗺️ **{{ state_attr('sensor.inmet_alertas_mapa_go', 'camadas_por_severidade.Grande Perigo.total_poligonos') }} polígonos** em Grande Perigo
        
        📐 **Área:** {{ state_attr('sensor.inmet_alertas_mapa_go', 'camadas_por_severidade.Grande Perigo.area_total_km2') }} km²
        
        📍 **Centro da área:** {{ state_attr('sensor.inmet_alertas_mapa_go', 'centro_geografico') }}
        
        🚨 **TOME PRECAUÇÕES IMEDIATAS**
        
        Verifique o mapa de alertas no painel principal.
      notification_id: "grande_perigo_geografico"
mode: single
```

### 🌡️ Automação de Zoom Inteligente

```yaml
alias: "Mapa INMET - Ajuste de Zoom Automático"
description: "Ajusta zoom do mapa baseado na área afetada"
trigger:
  - platform: state
    entity_id: sensor.inmet_alertas_mapa_go
    attribute: zoom_recomendado
action:
  - service: browser_mod.command
    data:
      command: js
      code: >
        const zoom = {{ state_attr('sensor.inmet_alertas_mapa_go', 'zoom_recomendado') or 8 }};
        const centro = {{ state_attr('sensor.inmet_alertas_mapa_go', 'centro_geografico') or ['-15.83', '-47.86'] }};
        
        const maps = document.querySelectorAll('ha-map');
        maps.forEach(map => {
          if (map.map) {
            map.map.setView(centro, zoom);
          }
        });
mode: single
```

### 📱 Automação para Notificação Rica com Mapa

```yaml
alias: "Alerta INMET - Notificação com Localização"
description: "Envia notificação rica com dados geográficos"
trigger:
  - platform: state
    entity_id: sensor.inmet_alertas_mapa_go
    not_from: "0"
    not_to: "0"
action:
  - service: notify.mobile_app_meu_celular
    data:
      title: "🗺️ Alerta Geográfico Atualizado"
      message: >
        📍 {{ states('sensor.inmet_alertas_mapa_go') }} polígonos mapeados
        📐 Área: {{ state_attr('sensor.inmet_alertas_mapa_go', 'area_total_afetada_km2') }} km²
      data:
        channel: "weather_geographic"
        importance: default
        tag: "inmet_map_update"
        group: "inmet_alerts"
        # Dados geográficos para apps que suportam
        location:
          latitude: "{{ state_attr('sensor.inmet_alertas_mapa_go', 'centro_geografico')[0] }}"
          longitude: "{{ state_attr('sensor.inmet_alertas_mapa_go', 'centro_geografico')[1] }}"
        # Ações rápidas
        actions:
          - action: "open_map"
            title: "🗺️ Ver Mapa"
          - action: "view_details"
            title: "📊 Detalhes"
mode: single
```

## 🔧 Solução de Problemasa (INMET) do Brasil.

## 🌦️ Funcionalidades

- **Monitoramento em tempo real** de alertas meteorológicos do INMET
- **Filtragem por estado brasileiro** - configure para receber apenas alertas do seu estado
- **Notificações automáticas** para alertas de alta severidade (Perigo e Grande Perigo)
- **Limpeza automática** de notificações quando alertas expiram
- **Suporte a múltiplos estados** - configure diferentes estados simultaneamente
- **Múltiplos sensores**:
  - Sensor principal com detalhes dos alertas ativos
  - Sensor de contagem de alertas
- **Eventos personalizados** para automações avançadas
- **Interface totalmente em português brasileiro**

## 🏗️ Arquitetura Profissional

A integração foi desenvolvida seguindo as melhores práticas de desenvolvimento:

### 📁 Estrutura Modular
```
inmet_alertas/
├── 📄 Arquivos principais (sensor.py, config_flow.py, etc.)
├── 📁 helpers/           # Módulos auxiliares especializados
│   ├── 📄 rss_parser.py          # Parser RSS/CAP otimizado
│   ├── 📄 data_processor.py      # Processamento de dados
│   └── 📄 notification_manager.py # Gerenciador de notificações
├── 📁 docs/             # Documentação detalhada
├── 📁 translations/     # Suporte multilíngue (PT/EN)
└── 📁 tests/           # Suíte de testes automatizados
```

### 🔧 Componentes Especializados
- **RSSParser**: Comunicação otimizada com feeds do INMET
- **DataProcessor**: Validação e formatação de dados meteorológicos
- **NotificationManager**: Gerenciamento inteligente de notificações
- **Constantes Centralizadas**: Configurações organizadas em const.py

### 📋 Padrões de Qualidade
- **Código documentado** com docstrings em português
- **Tratamento robusto de erros** em todas as operações
- **Logs estruturados** para facilitar troubleshooting
- **Testes automatizados** para validação contínua

## 📦 Instalação

### 🚀 Instalação Rápida via HACS

1. Abra o **HACS** → **Integrações** → **Menu ⋮** → **Repositórios Personalizados**
2. Adicione: `https://github.com/roalvesrj/hacs-inmet-alertas`
3. Procure por **"INMET Alertas"** e instale
4. **Reinicie o Home Assistant**

### 📖 Documentação Completa

Para instruções detalhadas, consulte:
- 📥 **[Guia de Instalação](docs/INSTALACAO.md)** - Instruções passo-a-passo
- ⚙️ **[Guia de Configuração](docs/CONFIGURACAO.md)** - Configuração completa
- 🎨 **[Exemplos de Interface](docs/EXEMPLOS.md)** - Cartões e automações
- 🔧 **[Solução de Problemas](docs/TROUBLESHOOTING.md)** - Resolução de issues

## ⚙️ Configuração

1. Vá para **Configurações** → **Dispositivos e Serviços**
2. Clique em **Adicionar Integração**
3. Procure por "INMET Alertas"
4. Selecione o seu estado brasileiro
5. Configure as opções:
   - **Notificações de Perigo**: Ativa notificações automáticas para alertas Perigo e Grande Perigo
   - **Intervalo de Atualização**: Tempo entre verificações (5-120 minutos)

### 🌎 Configurando Múltiplos Estados

Você pode configurar a integração para monitorar diferentes estados simultaneamente:

1. **Primeira configuração**: Configure normalmente para o primeiro estado (ex: GO)
2. **Estados adicionais**: Repita o processo de configuração para cada estado desejado
3. **Notificações independentes**: Cada estado terá suas próprias notificações e sensores
4. **IDs únicos**: As notificações incluem o código do estado para evitar conflitos

**Exemplo de configuração múltipla:**
- `sensor.alertas_meteorologicos_go` (Goiás)
- `sensor.alertas_meteorologicos_rj` (Rio de Janeiro)
- `sensor.alertas_meteorologicos_sp` (São Paulo)

**Notificações por estado:**
- `inmet_alert_GO_12345` (Alerta para Goiás)
- `inmet_alert_RJ_12345` (Mesmo alerta, mas para Rio de Janeiro)

## 📊 Sensores Criados

### `sensor.alertas_meteorologicos_[ESTADO]`
- **Estado**: Nome do alerta ativo ou "Nenhum alerta ativo"
- **Atributos**:
  - `total_alertas`: Número total de alertas ativos
  - `alertas`: Lista detalhada de todos os alertas
  - `alertas_por_severidade`: Contagem por nível de severidade
  - `estado`: Estado configurado
  - `ultima_atualizacao`: Timestamp da última atualização

### `sensor.quantidade_de_alertas_[ESTADO]`
- **Estado**: Número de alertas ativos
- **Unidade**: alertas

## 🔔 Notificações

A integração cria automaticamente notificações persistentes para alertas de alta severidade:

- **🟠 Alertas Perigo**: Notificação com detalhes do alerta
- **🔴 Alertas Grande Perigo**: Notificação com detalhes do alerta

## 🎯 Eventos

### `inmet_novo_alerta`
Disparado quando um novo alerta é detectado.

**Dados do evento**:
```yaml
alert_id: "CAP-BR-INMET-000001"
titulo: "Chuvas Intensas"
severidade: "Perigo Potencial"
evento: "Chuva"
estado: "SP"
inicio: "21/09/2025 10:00"
fim: "21/09/2025 18:00"
```

## 🤖 Automações

A integração dispara eventos que podem ser usados em automações do Home Assistant. Existem duas formas de criar automações:

### 📝 **Diferença entre os Formatos:**

1. **configuration.yaml**: Para quem prefere editar arquivos YAML
   - Adicione no arquivo `configuration.yaml`
   - Reinicie o Home Assistant após mudanças
   - Formato com `automation:` no início

2. **Interface do Home Assistant**: Mais visual e fácil
   - Vá em Configurações → Automações → Criar Automação
   - Cole o código YAML no editor
   - Salve diretamente pela interface

### Exemplo de Automação

**Para configuration.yaml:**
```yaml
automation:
  - alias: "Notificar Alerta INMET"
    trigger:
      - platform: event
        event_type: inmet_novo_alerta
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.severidade in ['Perigo', 'Grande Perigo'] }}"
    action:
      - service: notify.mobile_app_meu_celular
        data:
          title: "🚨 Alerta Meteorológico"
          message: >
            {{ trigger.event.data.titulo }}
            
            Severidade: {{ trigger.event.data.severidade }}
            Estado: {{ trigger.event.data.estado }}
            Período: {{ trigger.event.data.inicio }} até {{ trigger.event.data.fim }}
```

**Para Interface do Home Assistant (Configurações → Automações → Criar):**
```yaml
alias: Notificar Alerta INMET
description: Envia notificação para alertas de Perigo e Grande Perigo
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
      message: >
        {{ trigger.event.data.titulo }}
        
        Severidade: {{ trigger.event.data.severidade }}
        Estado: {{ trigger.event.data.estado }}
        Período: {{ trigger.event.data.inicio }} até {{ trigger.event.data.fim }}
mode: single
```

### Automação Alternativa (usando mudança de sensor)

**Para configuration.yaml:**
```yaml
automation:
  - alias: "Alerta INMET - Mudança de Estado"
    trigger:
      - platform: state
        entity_id: sensor.alertas_meteorologicos_go  # Altere para seu estado
        not_from: "Nenhum alerta ativo"
        not_to: "Nenhum alerta ativo"
    condition:
      - condition: template
        value_template: "{{ states('sensor.quantidade_de_alertas_go') | int > 0 }}"
    action:
      - service: notify.mobile_app_meu_celular
        data:
          title: "🌦️ Novo Alerta Meteorológico"
          message: >
            {% set alertas = state_attr('sensor.alertas_meteorologicos_go', 'alertas') %}
            {% if alertas %}
            {% for alerta in alertas %}
            {{ alerta.icone }} {{ alerta.titulo }}
            Severidade: {{ alerta.severidade }}
            Período: {{ alerta.inicio }} até {{ alerta.fim }}
            {% if not loop.last %}---{% endif %}
            {% endfor %}
            {% endif %}
```

**Para Interface do Home Assistant:**
```yaml
alias: Alerta INMET - Mudança de Estado
description: Notifica quando há mudança nos alertas meteorológicos
trigger:
  - platform: state
    entity_id: sensor.alertas_meteorologicos_go
    not_from: Nenhum alerta ativo
    not_to: Nenhum alerta ativo
condition:
  - condition: template
    value_template: "{{ states('sensor.quantidade_de_alertas_go') | int > 0 }}"
action:
  - service: notify.mobile_app_meu_celular
    data:
      title: 🌦️ Novo Alerta Meteorológico
      message: >
        {% set alertas = state_attr('sensor.alertas_meteorologicos_go', 'alertas') %}
        {% if alertas %}
        {% for alerta in alertas %}
        {{ alerta.icone }} {{ alerta.titulo }}
        Severidade: {{ alerta.severidade }}
        Período: {{ alerta.inicio }} até {{ alerta.fim }}
        {% if not loop.last %}---{% endif %}
        {% endfor %}
        {% endif %}
mode: single
```

### Automação para Tipos Específicos de Alerta

**Para Interface do Home Assistant - Alerta de Vendaval:**
```yaml
alias: Alerta INMET - Vendaval
description: Notificação específica para alertas de vendaval
trigger:
  - platform: event
    event_type: inmet_novo_alerta
condition:
  - condition: template
    value_template: "{{ 'Vendaval' in trigger.event.data.evento }}"
action:
  - service: notify.family_group
    data:
      title: 💨 Alerta de Vendaval
      message: >
        ⚠️ {{ trigger.event.data.titulo }}
        
        🏠 Feche portas e janelas!
        🚗 Evite estacionar sob árvores!
        
        Período: {{ trigger.event.data.inicio }} até {{ trigger.event.data.fim }}
        Municípios afetados: {{ trigger.event.data.municipios }}
mode: single
```

**Para Interface do Home Assistant - Alerta de Chuva:**
```yaml
alias: Alerta INMET - Chuva Intensa
description: Notificação específica para alertas de chuva
trigger:
  - platform: event
    event_type: inmet_novo_alerta
condition:
  - condition: template
    value_template: "{{ 'Chuva' in trigger.event.data.evento }}"
action:
  - service: script.preparar_casa_chuva  # Script personalizado (opcional)
  - service: notify.mobile_app_meu_celular
    data:
      title: 🌧️ Alerta de Chuva
      message: >
        {{ trigger.event.data.titulo }}
        Severidade: {{ trigger.event.data.severidade }}
        Período: {{ trigger.event.data.inicio }} até {{ trigger.event.data.fim }}
mode: single
```
```

## 🛠️ Serviços

### `inmet_alertas.atualizar_alertas`
Força a atualização dos alertas.

**Parâmetros**:
- `estado` (opcional): Atualizar apenas alertas de um estado específico

```yaml
service: inmet_alertas.atualizar_alertas
data:
  estado: "SP"  # Opcional
```

## 🎨 Interface Lovelace

### Cartão de Alertas Simples

```yaml
type: entities
title: Alertas Meteorológicos
entities:
  - sensor.alertas_meteorologicos_sp
  - sensor.quantidade_de_alertas_sp
```

### Cartão Detalhado com Instruções Completas

Este cartão mostra alertas ativos apenas quando existem e exibe informações detalhadas:

```yaml
type: conditional
conditions:
  - entity: sensor.quantidade_de_alertas_sp  # ⚠️ ALTERE 'sp' para seu estado (ex: 'go', 'rj', 'mg')
    state_not: "0"
card:
  type: markdown
  content: >
    ## 🌦️ Alertas Ativos - {{ state_attr('sensor.alertas_meteorologicos_sp', 'estado') }}
    
    **{{ states('sensor.quantidade_de_alertas_sp') }} alerta(s) ativo(s)**
    
    {% for alerta in state_attr('sensor.alertas_meteorologicos_sp', 'alertas') %}
    ### {{ alerta.icone }} {{ alerta.titulo }}
    
    **🏷️ Tipo:** {{ alerta.evento }}  
    **⚠️ Severidade:** {{ alerta.severidade }}  
    **⏰ Início:** {{ alerta.inicio }}  
    **⏱️ Fim:** {{ alerta.fim }}  
    **📍 Municípios:** {{ alerta.total_municipios_estado }} afetados
    
    **📝 Descrição:**  
    {{ alerta.descricao }}
    
    {% if alerta.instrucoes %}
    **📋 Instruções:**  
    {{ alerta.instrucoes }}
    {% endif %}
    
    {% if alerta.municipios_estado and alerta.municipios_estado | length <= 10 %}
    **🏘️ Municípios afetados:**  
    {{ alerta.municipios_estado | join(', ') }}
    {% elif alerta.municipios_estado and alerta.municipios_estado | length > 10 %}
    **🏘️ Municípios afetados:** {{ alerta.municipios_estado | length }} municípios (muitos para listar)
    {% endif %}
    
    ---
    {% endfor %}
    
    *Última atualização: {{ state_attr('sensor.alertas_meteorologicos_sp', 'ultima_atualizacao') }}*
```

### Como Personalizar o Cartão

1. **Alterar o Estado**: Substitua `sp` pelos códigos do seu estado:
   ```yaml
   # Exemplos para diferentes estados:
   sensor.alertas_meteorologicos_go  # Goiás
   sensor.alertas_meteorologicos_rj  # Rio de Janeiro  
   sensor.alertas_meteorologicos_mg  # Minas Gerais
   sensor.alertas_meteorologicos_rs  # Rio Grande do Sul
   ```

2. **Personalizar Informações Exibidas**: Remova ou adicione campos conforme necessário:
   ```yaml
   # Campos disponíveis em cada alerta:
   {{ alerta.titulo }}                    # Nome do alerta
   {{ alerta.evento }}                    # Tipo de evento (Chuva, Vendaval, etc.)
   {{ alerta.severidade }}                    # Perigo Potencial, Perigo, Grande Perigo
   {{ alerta.inicio }}                    # Data/hora de início
   {{ alerta.fim }}                       # Data/hora de fim
   {{ alerta.descricao }}                 # Descrição detalhada
   {{ alerta.instrucoes }}                # Instruções de segurança
   {{ alerta.municipios_estado }}         # Lista de municípios afetados no estado
   {{ alerta.total_municipios_estado }}   # Número de municípios afetados
   {{ alerta.icone }}                     # Ícone do alerta
   {{ alerta.area_desc }}                 # Descrição da área afetada
   {{ alerta.publicado }}                 # Data de publicação
   {{ alerta.link }}                      # Link para detalhes do alerta
   ```

3. **Cartão Sempre Visível** (mesmo sem alertas):
   ```yaml
   type: markdown
   content: >
     ## 🌦️ Alertas Meteorológicos - {{ state_attr('sensor.alertas_meteorologicos_sp', 'estado') }}
     
     {% if states('sensor.quantidade_de_alertas_sp') == "0" %}
     ✅ **Nenhum alerta ativo no momento**
     {% else %}
     **{{ states('sensor.quantidade_de_alertas_sp') }} alerta(s) ativo(s)**
     
     {% for alerta in state_attr('sensor.alertas_meteorologicos_sp', 'alertas') %}
     ### {{ alerta.icone }} {{ alerta.titulo }}
     **Severidade:** {{ alerta.severidade }} | **Período:** {{ alerta.inicio }} até {{ alerta.fim }}
     {{ alerta.descricao }}
     ---
     {% endfor %}
     {% endif %}
   ```

### Cartão Compacto para Dashboard

```yaml
type: glance
title: Alertas INMET
entities:
  - entity: sensor.alertas_meteorologicos_sp  # ⚠️ ALTERE para seu estado
    name: Status
  - entity: sensor.quantidade_de_alertas_sp   # ⚠️ ALTERE para seu estado  
    name: Quantidade
    icon: mdi:weather-cloudy-alert
```

## �️ Mapas Geográficos dos Alertas

### 📍 Sensor de Mapa Disponível

A partir da versão 2.0, cada estado configurado ganha automaticamente um sensor de mapa:
- `sensor.inmet_alertas_mapa_[estado]` (ex: `sensor.inmet_alertas_mapa_go`)

### 🎨 Cartão de Mapa Básico

```yaml
type: map
title: 🌦️ Alertas Meteorológicos - Goiás
entities:
  - sensor.inmet_alertas_mapa_go  # ⚠️ ALTERE para seu estado
default_zoom: 8
aspect_ratio: "16:9"
```

### � Mapa Avançado com Polígonos Reais - ha-map-card

> **⚠️ IMPORTANTE:** O mapa nativo do Home Assistant não desenha polígonos complexos. Para ver as **áreas reais dos alertas desenhadas no mapa**, use o ha-map-card com nosso plugin personalizado.

#### 📦 Instalação do ha-map-card + Plugin INMET

> **⚠️ IMPORTANTE:** O ha-map-card exige coordenadas de centro (x, y) ou entidades para funcionar. Use as coordenadas do seu estado ou região de interesse.

1. **Instale o ha-map-card** via HACS:
   - HACS → Frontend → Buscar "Map Card" → Instalar

2. **Instale nosso plugin personalizado**:
   - Copie o arquivo `plugin_inmet_polygons.js` para `/config/www/inmet_plugin/`
   - Reinicie o Home Assistant

3. **Configure o card com polígonos reais**:

```yaml
type: custom:map-card
title: "🗺️ Alertas INMET com Polígonos Reais"
zoom: 6
card_size: 8

# Centralizar no Brasil (coordenadas obrigatórias)
x: -15.7998  # Latitude central do Brasil
y: -47.8645  # Longitude central do Brasil

# Mapa base
tile_layer_url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
tile_layer_attribution: '&copy; OpenStreetMap'

# Plugin que desenha os polígonos reais
plugins:
  - name: inmet_polygons
    url: /local/inmet_plugin/plugin_inmet_polygons.js
    options:
      # Estados para monitorar (configure os seus)
      states: ["goias", "sao_paulo", "minas_gerais"]
      
      # Cores oficiais INMET
      colors:
        grandePerigo: "#FF0000"    # Vermelho
        perigo: "#FF8C00"          # Laranja  
        perigoPotencial: "#FFD700" # Amarelo
      
      # Configurações visuais
      fillOpacity: 0.3      # Transparência do preenchimento
      strokeOpacity: 0.8    # Transparência da borda
      strokeWeight: 2       # Espessura da borda
      showLabels: true      # Mostrar rótulos
      updateInterval: 60000 # Atualizar a cada 1 minuto

# Entidades adicionais (opcional)
entities:
  - entity: zone.home
    display: icon
    size: 40
```

#### 📍 Coordenadas dos Estados Brasileiros

Para centralizar o mapa no seu estado, use as coordenadas abaixo:

```yaml
# Exemplos de coordenadas por estado:
# São Paulo:      x: -23.5505, y: -46.6333
# Rio de Janeiro: x: -22.9068, y: -43.1729
# Minas Gerais:   x: -19.9167, y: -43.9345
# Goiás:          x: -16.6864, y: -49.2643
# Bahia:          x: -12.9718, y: -38.5014
# Paraná:         x: -25.4284, y: -49.2733
# Rio Grande Sul: x: -30.0346, y: -51.2177
# Santa Catarina: x: -27.2423, y: -50.2189
# Brasília:       x: -15.7998, y: -47.8645
```

#### 🎯 Exemplo para Estado Específico

```yaml
type: custom:map-card
title: "🌦️ Alertas Meteorológicos - São Paulo"
zoom: 7
card_size: 6

# Centralizar em São Paulo
x: -23.5505
y: -46.6333

plugins:
  - name: inmet_sp
    url: /local/inmet_plugin/plugin_inmet_polygons.js
    options:
      states: ["sao_paulo"]  # Apenas SP
      showLabels: true
      fillOpacity: 0.4

#### 🇧🇷 Exemplo para Monitoramento Nacional

```yaml
type: custom:map-card
title: "🌎 Alertas INMET - Brasil"
zoom: 5
card_size: 12

# Centralizar no Brasil
x: -15.7998
y: -47.8645

plugins:
  - name: inmet_brasil
    url: /local/inmet_plugin/plugin_inmet_polygons.js
    options:
      # Monitorar todos os estados brasileiros
      states: ["acre", "alagoas", "amapa", "amazonas", "bahia", "ceara", "distrito_federal", "espirito_santo", "goias", "maranhao", "mato_grosso", "mato_grosso_do_sul", "minas_gerais", "para", "paraiba", "parana", "pernambuco", "piaui", "rio_de_janeiro", "rio_grande_do_norte", "rio_grande_do_sul", "rondonia", "roraima", "santa_catarina", "sao_paulo", "sergipe", "tocantins"]
      showLabels: false  # Desativar para visualização nacional
      fillOpacity: 0.4
      updateInterval: 120000  # 2 minutos para todos os estados
```

# Centralizar em São Paulo
x: -23.5505
y: -46.6333
```

#### ✨ Vantagens do ha-map-card + Plugin

- **🎨 Polígonos Reais**: Desenha as áreas exatas dos alertas no mapa
- **🌈 Cores por Severidade**: Vermelho, laranja e amarelo automáticos
- **📱 Responsivo**: Funciona perfeitamente em mobile
- **⚡ Atualização Automática**: Monitora mudanças nos sensores
- **🖱️ Interativo**: Popups com detalhes ao clicar nos polígonos
- **🔧 Customizável**: Cores, transparências e comportamentos ajustáveis

#### � Solução de Problemas - ha-map-card

**Erro: "We need a map latitude & longitude"**
- **Causa**: O ha-map-card precisa de coordenadas de centro ou entidades definidas
- **Solução**: Adicione `x:` e `y:` na configuração do card:
```yaml
type: custom:map-card
x: -15.7998  # Latitude (obrigatório)
y: -47.8645  # Longitude (obrigatório)
# resto da configuração...
```

**Plugin não carrega**
- Verifique se o arquivo está em `/config/www/inmet_plugin/plugin_inmet_polygons.js`
- Confirme que o ha-map-card está instalado
- Verifique o console do navegador para erros

**Polígonos não aparecem**  
- Verifique se os sensores `sensor.inmet_alertas_mapa_*` existem
- Confirme que os sensores têm dados geográficos (`geographic_data`)
- Verifique se há alertas ativos para os estados configurados

#### �📄 Documentação Completa

Para configuração detalhada, consulte: [`CONFIG_HA_MAP_CARD.md`](CONFIG_HA_MAP_CARD.md)

### �🎨 Cartão de Mapa Avançado com Informações

```yaml
type: vertical-stack
cards:
  # Cabeçalho com informações
  - type: horizontal-stack
    cards:
      - type: entity
        entity: sensor.inmet_alertas_mapa_go
        name: "Polígonos Ativos"
        icon: mdi:map-marker-multiple
      - type: entity
        entity: sensor.inmet_alertas_mapa_go
        name: "Área Afetada"
        attribute: area_total_afetada_km2
        unit: "km²"
        icon: mdi:vector-square
      - type: entity
        entity: sensor.inmet_alertas_mapa_go
        name: "Alertas Geográficos"
        attribute: total_alertas_com_geo
        icon: mdi:alert-rhombus
  
  # Mapa principal
  - type: map
    title: 🗺️ Mapa de Alertas - Goiás
    entities:
      - sensor.inmet_alertas_mapa_go
    default_zoom: 8
    aspect_ratio: "16:9"
    dark_mode: auto
```

### 🌈 Cartão de Mapa com Camadas por Severidade

```yaml
type: vertical-stack
cards:
  # Legenda das cores
  - type: markdown
    content: |
      ## 🎨 Legenda dos Alertas
      🔴 **Grande Perigo** | 🟠 **Perigo** | 🟡 **Perigo Potencial**
  
  # Estatísticas por severidade
  - type: horizontal-stack
    cards:
      - type: custom:mini-graph-card
        entities:
          - entity: sensor.inmet_alertas_mapa_go
            attribute: camadas_por_severidade.Grande Perigo.total_poligonos
            name: "Grande Perigo"
        name: "🔴 Polígonos"
        icon: mdi:alert-octagon
        color: red
        show:
          graph: false
          
      - type: custom:mini-graph-card
        entities:
          - entity: sensor.inmet_alertas_mapa_go
            attribute: camadas_por_severidade.Perigo.total_poligonos
            name: "Perigo"
        name: "🟠 Polígonos"
        icon: mdi:alert-rhombus
        color: orange
        show:
          graph: false
          
      - type: custom:mini-graph-card
        entities:
          - entity: sensor.inmet_alertas_mapa_go
            attribute: camadas_por_severidade.Perigo Potencial.total_poligonos
            name: "Perigo Potencial"
        name: "🟡 Polígonos"
        icon: mdi:alert-circle
        color: yellow
        show:
          graph: false
  
  # Mapa principal
  - type: map
    title: 🗺️ Alertas por Severidade
    entities:
      - sensor.inmet_alertas_mapa_go
    default_zoom: 
      template: "{{ state_attr('sensor.inmet_alertas_mapa_go', 'zoom_recomendado') or 8 }}"
    aspect_ratio: "21:9"
```

### 🎯 Cartão de Mapa Inteligente com Auto-Zoom

```yaml
type: conditional
conditions:
  - entity: sensor.inmet_alertas_mapa_go
    state_not: "0"
card:
  type: vertical-stack
  cards:
    # Resumo executivo
    - type: markdown
      content: >
        ## 🗺️ Situação Geográfica - {{ state_attr('sensor.inmet_alertas_mapa_go', 'estado') }}
        
        **📊 {{ states('sensor.inmet_alertas_mapa_go') }} polígonos mapeados**
        
        📐 **Área total afetada:** {{ state_attr('sensor.inmet_alertas_mapa_go', 'area_total_afetada_km2') }} km²
        
        📍 **Centro geográfico:** {{ state_attr('sensor.inmet_alertas_mapa_go', 'centro_geografico') | round(4) }}
        
        🔍 **Zoom recomendado:** {{ state_attr('sensor.inmet_alertas_mapa_go', 'zoom_recomendado') }}
        
    # Detalhes por severidade  
    - type: markdown
      content: >
        ### 📋 Distribuição por Severidade
        
        {% set camadas = state_attr('sensor.inmet_alertas_mapa_go', 'camadas_por_severidade') %}
        {% if camadas %}
        {% for severidade, dados in camadas.items() %}
        {% if dados.total_poligonos > 0 %}
        **{{ '🔴' if severidade == 'Grande Perigo' else '🟠' if severidade == 'Perigo' else '🟡' }} {{ severidade }}:**
        {{ dados.total_poligonos }} polígonos, {{ dados.area_total_km2 }} km²
        {% endif %}
        {% endfor %}
        {% endif %}
        
    # Mapa principal com zoom inteligente
    - type: map
      entities:
        - sensor.inmet_alertas_mapa_go
      default_zoom: 
        template: "{{ state_attr('sensor.inmet_alertas_mapa_go', 'zoom_recomendado') or 8 }}"
      theme_mode: auto
      aspect_ratio: "2:1"
```

### 🏠 Dashboard Completo de Monitoramento

```yaml
type: vertical-stack
title: 🌦️ Central de Monitoramento Meteorológico
cards:
  # Status geral
  - type: horizontal-stack
    cards:
      - type: entity
        entity: sensor.quantidade_de_alertas_go
        name: "Total Alertas"
        icon: mdi:weather-cloudy-alert
        
      - type: entity  
        entity: sensor.inmet_alertas_mapa_go
        name: "Áreas Mapeadas"
        icon: mdi:map-marker-multiple
        
      - type: entity
        entity: sensor.inmet_alertas_mapa_go
        name: "Cobertura"
        attribute: area_total_afetada_km2
        unit: "km²"
        icon: mdi:vector-square

  # Alertas ativos (se houver)
  - type: conditional
    conditions:
      - entity: sensor.quantidade_de_alertas_go
        state_not: "0"
    card:
      type: entities
      title: 📢 Alertas Ativos
      entities:
        - sensor.alertas_meteorologicos_go

  # Mapa (se houver dados geográficos)  
  - type: conditional
    conditions:
      - entity: sensor.inmet_alertas_mapa_go
        state_not: "0"
    card:
      type: map
      title: 🗺️ Localização dos Alertas
      entities:
        - sensor.inmet_alertas_mapa_go
      default_zoom: 
        template: "{{ state_attr('sensor.inmet_alertas_mapa_go', 'zoom_recomendado') or 8 }}"
      aspect_ratio: "16:9"

  # Status quando não há alertas
  - type: conditional
    conditions:
      - entity: sensor.quantidade_de_alertas_go
        state: "0"
    card:
      type: markdown
      content: |
        ## ✅ Situação Tranquila
        
        🌤️ **Nenhum alerta ativo no momento**
        
        📍 **Estado:** {{ state_attr('sensor.alertas_meteorologicos_go', 'estado') }}
        
        🕐 **Última verificação:** {{ state_attr('sensor.alertas_meteorologicos_go', 'ultima_atualizacao') }}
        
        *Continue monitorando para receber alertas em tempo real!*
```

### 🎮 Cartão de Mapa Interativo com Controles

```yaml
type: custom:stack-in-card
cards:
  # Controles superiores
  - type: horizontal-stack
    cards:
      - type: button
        name: "🔍 Zoom In"
        tap_action:
          action: call-service
          service: browser_mod.command
          service_data:
            command: js
            code: >
              document.querySelector('ha-map').map.setZoom(
                document.querySelector('ha-map').map.getZoom() + 1
              );
              
      - type: button  
        name: "🔍 Zoom Out"
        tap_action:
          action: call-service
          service: browser_mod.command
          service_data:
            command: js
            code: >
              document.querySelector('ha-map').map.setZoom(
                document.querySelector('ha-map').map.getZoom() - 1
              );
              
      - type: button
        name: "🎯 Centralizar"
        tap_action:
          action: call-service
          service: browser_mod.command
          service_data:
            command: js
            code: >
              const centro = {{ state_attr('sensor.inmet_alertas_mapa_go', 'centro_geografico') }};
              if (centro) {
                document.querySelector('ha-map').map.setView(centro, 8);
              }

  # Mapa principal
  - type: map
    entities:
      - sensor.inmet_alertas_mapa_go
    hours_to_show: 0
    aspect_ratio: "16:10"
```

### 📱 Cartão Mobile-Friendly

```yaml
type: vertical-stack
cards:
  # Cabeçalho compacto
  - type: glance
    title: 🌦️ Alertas Geográficos
    entities:
      - entity: sensor.inmet_alertas_mapa_go
        name: "Polígonos"
      - entity: sensor.inmet_alertas_mapa_go
        name: "Área km²"
        attribute: area_total_afetada_km2
    columns: 2

  # Mapa otimizado para mobile
  - type: map
    entities:
      - sensor.inmet_alertas_mapa_go
    aspect_ratio: "1:1"
    default_zoom: 7
    fit_zones: true
```

### 💡 Dicas para Personalização dos Mapas

1. **Alterar Estado**: Substitua `go` pelo código do seu estado:
   ```yaml
   sensor.inmet_alertas_mapa_sp  # São Paulo
   sensor.inmet_alertas_mapa_rj  # Rio de Janeiro
   sensor.inmet_alertas_mapa_mg  # Minas Gerais
   ```

2. **Zoom Automático**: O sensor calcula automaticamente o zoom ideal:
   ```yaml
   default_zoom:
     template: "{{ state_attr('sensor.inmet_alertas_mapa_go', 'zoom_recomendado') }}"
   ```

3. **Atributos Disponíveis** no sensor de mapa:
   ```yaml
   # Dados principais
   {{ states('sensor.inmet_alertas_mapa_go') }}                    # Número de polígonos
   {{ state_attr('...', 'area_total_afetada_km2') }}              # Área total em km²
   {{ state_attr('...', 'centro_geografico') }}                  # Centro [lat, lon]
   {{ state_attr('...', 'zoom_recomendado') }}                   # Zoom ideal
   {{ state_attr('...', 'total_alertas_com_geo') }}              # Alertas com dados geográficos
   
   # Camadas por severidade
   {{ state_attr('...', 'camadas_por_severidade.Grande Perigo.total_poligonos') }}
   {{ state_attr('...', 'camadas_por_severidade.Perigo.area_total_km2') }}
   {{ state_attr('...', 'camadas_por_severidade.Perigo Potencial.cor_oficial') }}
   ```

4. **Cores Automáticas**: Os polígonos são coloridos automaticamente por severidade:
   - 🔴 **Grande Perigo**: Vermelho
   - 🟠 **Perigo**: Laranja  
   - 🟡 **Perigo Potencial**: Amarelo

## �🔧 Solução de Problemas

### Alertas não aparecem
1. Verifique se o estado está configurado corretamente
2. Consulte os logs: **Configurações** → **Sistema** → **Logs**
3. Procure por mensagens com `inmet_alertas`

### Notificações não funcionam
1. Verifique se as notificações estão habilitadas na configuração
2. Confirme se há alertas de severidade Perigo ou Grande Perigo ativo

### Logs Úteis
```yaml
# configuration.yaml
logger:
  logs:
    custom_components.inmet_alertas: debug
```

## 📅 Níveis de Severidade

- **🟡 Perigo Potencial**: Atenção - Condições meteorológicas que podem causar danos
- **🟠 Perigo**: Cuidado - Condições meteorológicas perigosas  
- **🔴 Grande Perigo**: Perigo - Condições meteorológicas muito perigosas

## 📈 Versionamento

Este projeto segue o [Versionamento Semântico](https://semver.org/):

- **MAJOR**: Mudanças incompatíveis com versões anteriores
- **MINOR**: Novas funcionalidades compatíveis
- **PATCH**: Correções de bugs compatíveis

### 🆕 Changelog v2.0.0 - FASE 2 GEOGRÁFICA

#### 🎉 Novidades Principais
- **🗺️ Sensores de Mapa Geográfico** - Sensor dedicado `sensor.inmet_alertas_mapa_[estado]` para cada estado
- **📐 Processamento de Polígonos** - Extração e cálculo automático de áreas afetadas em km²
- **🎨 Camadas por Severidade** - Organização visual por Grande Perigo, Perigo e Perigo Potencial
- **🎯 Zoom Inteligente** - Cálculo automático do melhor zoom para visualização
- **📍 Centro Geográfico** - Determinação automática do centro das áreas afetadas

#### 🛠️ Melhorias Técnicas
- **GeoProcessor** - Novo módulo especializado em processamento geográfico
- **Algoritmo de Shoelace** - Cálculo preciso de áreas de polígonos irregulares
- **Parser CAP Aprimorado** - Extração robusta de dados geográficos XML
- **Coordenadas Precisas** - Suporte completo a formato latitude,longitude
- **Bounding Box** - Cálculo de limites geográficos para melhor visualização

#### 🎨 Interface Expandida
- **+10 Exemplos de Cards** de mapa no README
- **Mapas Interativos** com controles de zoom
- **Dashboard Geográfico** completo
- **Cards Mobile-Friendly** otimizados
- **Automações Geográficas** baseadas em área e localização

#### 📊 Dados Disponibilizados
```yaml
# Sensor de mapa fornece:
area_total_afetada_km2: 1250.5       # Área total em km²
centro_geografico: [-15.83, -47.86]  # Centro [lat, lon]
zoom_recomendado: 8                   # Zoom ideal para visualização
total_alertas_com_geo: 3              # Alertas com dados geográficos
camadas_por_severidade:               # Organização por severidade
  Grande Perigo:
    total_poligonos: 1
    area_total_km2: 450.2
    cor_oficial: "#FF0000"
  Perigo:
    total_poligonos: 2
    area_total_km2: 800.3
    cor_oficial: "#FF8C00"
```

### 🆕 Changelog v1.7.0

#### 🎉 Novidades
- **Arquitetura profissional** com módulos especializados
- **Documentação expandida** em pasta dedicada
- **Suporte multilíngue** (Português/Inglês)
- **Testes organizados** em estrutura própria
- **Constantes centralizadas** para melhor manutenção

#### 🐛 Correções
- **Notificações duplicadas** entre estados resolvidas
- **Automações malformadas** corrigidas no README
- **Limpeza automática** de notificações expiradas
- **Terminologia de severidade** padronizada (Perigo, Grande Perigo)

#### 🔧 Melhorias Técnicas
- **RSSParser** otimizado para melhor performance
- **NotificationManager** com gerenciamento inteligente
- **DataProcessor** com validações robustas
- **Logs estruturados** para troubleshooting

## 📊 Estatísticas do Projeto

- **+1000 linhas** de código Python
- **+20 arquivos** organizados em estrutura modular
- **100% em português** (documentação e interface)
- **Compatibilidade** com Home Assistant 2023.1+
- **Suporte ativo** da comunidade brasileira

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## ⚠️ Disclaimer

Esta integração não é oficial e não é afiliada ao INMET. Os dados são obtidos a partir do feed RSS público do INMET.

---

**Desenvolvido com ❤️ para a comunidade brasileira do Home Assistant**