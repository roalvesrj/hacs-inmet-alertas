# INMET Alertas - Integração Home Assistant

![INMET Logo](https://www.gov.br/inmet/pt-br/central-de-conteudos/logomarca/logo-inmet.png/@@images/image.png)

[![GitHub release](https://img.shields.io/github/release/roalvesrj/hacs-inmet-alertas.svg)](https://github.com/roalvesrj/hacs-inmet-alertas/releases)
[![GitHub issues](https://img.shields.io/github/issues/roalvesrj/hacs-inmet-alertas.svg)](https://github.com/roalvesrj/hacs-inmet-alertas/issues)
[![License](https://img.shields.io/github/license/roalvesrj/hacs-inmet-alertas.svg)](LICENSE)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

Uma integração profissional para Home Assistant que monitora alertas meteorológicos do Instituto Nacional de Meteorologia (INMET) do Brasil.

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

## 🔧 Solução de Problemas

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