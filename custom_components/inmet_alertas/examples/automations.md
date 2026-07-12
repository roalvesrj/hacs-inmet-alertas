# Exemplos de Automações - INMET Alertas

## 1. Notificação via Telegram para Alertas Vermelhos

```yaml
automation:
  - alias: "INMET - Alerta Vermelho Telegram"
    description: "Envia notificação pelo Telegram para alertas vermelhos"
    trigger:
      platform: event
      event_type: inmet_novo_alerta
    condition:
      condition: template
      value_template: "{{ trigger.event.data.severidade == 'Vermelho' }}"
    action:
      - service: notify.telegram_bot
        data:
          message: >
            🚨 *ALERTA METEOROLÓGICO VERMELHO* 🚨
            
            📍 *Estado:* {{ trigger.event.data.estado }}
            🌦️ *Evento:* {{ trigger.event.data.evento }}
            📝 *Título:* {{ trigger.event.data.titulo }}
            
            ⏰ *Início:* {{ trigger.event.data.inicio }}
            ⏰ *Fim:* {{ trigger.event.data.fim }}
            
            ⚠️ *Tome precauções imediatas!*
          parse_mode: 'Markdown'
```

## 2. Acender Luzes Vermelhas para Alertas de Perigo

```yaml
automation:
  - alias: "INMET - Luzes de Emergência"
    description: "Acende luzes vermelhas durante alertas laranja/vermelho"
    trigger:
      - platform: state
        entity_id: sensor.alertas_meteorologicos_sp
    condition:
      condition: template
      value_template: >
        {% set alertas = state_attr('sensor.alertas_meteorologicos_sp', 'alertas') %}
        {% if alertas %}
          {{ alertas | selectattr('severidade', 'in', ['Laranja', 'Vermelho']) | list | length > 0 }}
        {% else %}
          false
        {% endif %}
    action:
      - service: light.turn_on
        target:
          entity_id: 
            - light.sala_principal
            - light.quarto_casal
        data:
          color_name: red
          brightness: 255
          flash: long
```

## 3. Anúncio por Voz com Google Home/Alexa

```yaml
automation:
  - alias: "INMET - Anúncio de Voz"
    description: "Anuncia alertas meteorológicos por voz"
    trigger:
      platform: event
      event_type: inmet_novo_alerta
    condition:
      condition: and
      conditions:
        - condition: time
          after: "07:00:00"
          before: "22:00:00"
        - condition: template
          value_template: "{{ trigger.event.data.severidade in ['Laranja', 'Vermelho'] }}"
    action:
      - service: tts.google_translate_say
        target:
          entity_id: media_player.google_home_sala
        data:
          message: >
            Atenção! Novo alerta meteorológico de nível {{ trigger.event.data.severidade }}.
            {{ trigger.event.data.titulo }} para o estado de {{ trigger.event.data.estado }}.
            Vigência de {{ trigger.event.data.inicio }} até {{ trigger.event.data.fim }}.
            Mantenha-se seguro!
          language: 'pt-br'
```

## 4. Envio de Email Detalhado

```yaml
automation:
  - alias: "INMET - Email Detalhado"
    description: "Envia email com informações detalhadas do alerta"
    trigger:
      platform: event
      event_type: inmet_novo_alerta
    condition:
      condition: template
      value_template: "{{ trigger.event.data.severidade != 'Amarelo' }}"
    action:
      - service: notify.smtp
        data:
          title: "🌦️ Alerta Meteorológico - {{ trigger.event.data.severidade }}"
          message: >
            <html>
            <body>
            <h2>🌦️ Novo Alerta Meteorológico INMET</h2>
            
            <table border="1" style="border-collapse: collapse; margin: 20px 0;">
              <tr><td><strong>Estado:</strong></td><td>{{ trigger.event.data.estado }}</td></tr>
              <tr><td><strong>Severidade:</strong></td><td>{{ trigger.event.data.severidade }}</td></tr>
              <tr><td><strong>Evento:</strong></td><td>{{ trigger.event.data.evento }}</td></tr>
              <tr><td><strong>Título:</strong></td><td>{{ trigger.event.data.titulo }}</td></tr>
              <tr><td><strong>Início:</strong></td><td>{{ trigger.event.data.inicio }}</td></tr>
              <tr><td><strong>Fim:</strong></td><td>{{ trigger.event.data.fim }}</td></tr>
            </table>
            
            <p><strong>Recomendações de Segurança:</strong></p>
            <ul>
              <li>Mantenha-se informado sobre as condições meteorológicas</li>
              <li>Evite áreas de risco durante o período do alerta</li>
              <li>Tenha um kit de emergência preparado</li>
            </ul>
            
            <hr>
            <small>Enviado automaticamente pelo Home Assistant</small>
            </body>
            </html>
          target: "usuario@email.com"
```

## 5. Fechamento Automático de Persianas/Toldos

```yaml
automation:
  - alias: "INMET - Fechar Persianas Vento"
    description: "Fecha persianas automaticamente durante alertas de vento"
    trigger:
      platform: event
      event_type: inmet_novo_alerta
    condition:
      condition: and
      conditions:
        - condition: template
          value_template: "{{ 'Vento' in trigger.event.data.evento }}"
        - condition: template
          value_template: "{{ trigger.event.data.severidade in ['Laranja', 'Vermelho'] }}"
    action:
      - service: cover.close_cover
        target:
          entity_id:
            - cover.persiana_sala
            - cover.persiana_quarto
            - cover.toldo_varanda
      - service: notify.mobile_app_meu_celular
        data:
          message: "Persianas fechadas automaticamente devido a alerta de vento forte"
```

## 6. Log Detalhado de Alertas

```yaml
automation:
  - alias: "INMET - Log de Alertas"
    description: "Registra todos os alertas em arquivo de log"
    trigger:
      platform: event
      event_type: inmet_novo_alerta
    action:
      - service: system_log.write
        data:
          message: >
            NOVO ALERTA INMET: {{ trigger.event.data.titulo }} 
            ({{ trigger.event.data.severidade }}) - 
            Estado: {{ trigger.event.data.estado }}, 
            Evento: {{ trigger.event.data.evento }}, 
            Período: {{ trigger.event.data.inicio }} até {{ trigger.event.data.fim }}
          level: warning
```

## 7. Controle de Irrigação Automática

```yaml
automation:
  - alias: "INMET - Pausar Irrigação Chuva"
    description: "Pausa irrigação durante alertas de chuva"
    trigger:
      - platform: state
        entity_id: sensor.alertas_meteorologicos_sp
    condition:
      condition: template
      value_template: >
        {% set alertas = state_attr('sensor.alertas_meteorologicos_sp', 'alertas') %}
        {% if alertas %}
          {{ alertas | selectattr('evento', 'search', 'Chuva') | list | length > 0 }}
        {% else %}
          false
        {% endif %}
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.irrigacao_jardim
      - service: input_boolean.turn_on
        target:
          entity_id: input_boolean.irrigacao_pausada_inmet

  - alias: "INMET - Retomar Irrigação"
    description: "Retoma irrigação quando não há mais alertas de chuva"
    trigger:
      - platform: state
        entity_id: sensor.quantidade_de_alertas_sp
        to: "0"
    condition:
      - condition: state
        entity_id: input_boolean.irrigacao_pausada_inmet
        state: "on"
    action:
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.irrigacao_pausada_inmet
      - service: notify.mobile_app_meu_celular
        data:
          message: "Irrigação pode ser retomada - alertas meteorológicos finalizados"
```

## 8. Dashboard Dinâmico com Alertas

```yaml
# Sensor template para status visual
template:
  - sensor:
      - name: "Status Meteorológico"
        state: >
          {% set count = states('sensor.quantidade_de_alertas_sp') | int %}
          {% if count == 0 %}
            Normal
          {% else %}
            {% set alertas = state_attr('sensor.alertas_meteorologicos_sp', 'alertas') %}
            {% set vermelho = alertas | selectattr('severidade', 'equalto', 'Vermelho') | list | length %}
            {% set laranja = alertas | selectattr('severidade', 'equalto', 'Laranja') | list | length %}
            {% if vermelho > 0 %}
              Perigo
            {% elif laranja > 0 %}
              Cuidado
            {% else %}
              Atenção
            {% endif %}
          {% endif %}
        icon: >
          {% set status = this.state %}
          {% if status == 'Normal' %}
            mdi:weather-sunny
          {% elif status == 'Atenção' %}
            mdi:weather-cloudy
          {% elif status == 'Cuidado' %}
            mdi:weather-lightning-rainy
          {% else %}
            mdi:weather-tornado
          {% endif %}
        attributes:
          cor: >
            {% set status = this.state %}
            {% if status == 'Normal' %}
              green
            {% elif status == 'Atenção' %}
              yellow
            {% elif status == 'Cuidado' %}
              orange
            {% else %}
              red
            {% endif %}
```

## 9. Automação com Node-RED (JSON)

```json
[
    {
        "id": "inmet_flow",
        "type": "tab",
        "label": "INMET Alertas",
        "disabled": false,
        "info": ""
    },
    {
        "id": "events_all",
        "type": "ha-events-all",
        "z": "inmet_flow",
        "name": "INMET Eventos",
        "server": "home_assistant",
        "version": 1,
        "event_type": "inmet_novo_alerta",
        "x": 120,
        "y": 100,
        "wires": [["process_alert"]]
    },
    {
        "id": "process_alert",
        "type": "function",
        "z": "inmet_flow",
        "name": "Processar Alerta",
        "func": "const data = msg.payload.data;\nconst severity = data.severidade;\n\nmsg.title = `Alerta ${severity}`;\nmsg.payload = {\n    message: `${data.titulo}\\nEstado: ${data.estado}\\nEvento: ${data.evento}\\nPeríodo: ${data.inicio} até ${data.fim}`,\n    data: {\n        priority: severity === 'Vermelho' ? 'high' : 'normal',\n        color: severity === 'Vermelho' ? 'red' : (severity === 'Laranja' ? 'orange' : 'yellow')\n    }\n};\n\nreturn msg;",
        "x": 300,
        "y": 100,
        "wires": [["send_notification"]]
    },
    {
        "id": "send_notification",
        "type": "ha-call-service",
        "z": "inmet_flow",
        "name": "Enviar Notificação",
        "server": "home_assistant",
        "version": 3,
        "service_domain": "notify",
        "service": "mobile_app_meu_celular",
        "entityId": "",
        "data": "{\"message\":\"{{payload.message}}\",\"title\":\"{{title}}\",\"data\":{{payload.data}}}",
        "x": 500,
        "y": 100,
        "wires": [[]]
    }
]
```

## 10. Script para Backup de Dados de Alertas

```yaml
script:
  backup_alertas_inmet:
    alias: "Backup Dados Alertas INMET"
    description: "Salva dados dos alertas em arquivo JSON"
    sequence:
      - service: shell_command.backup_inmet
        data:
          data: >
            {{ {
              'timestamp': now().isoformat(),
              'estado': state_attr('sensor.alertas_meteorologicos_sp', 'estado'),
              'total_alertas': states('sensor.quantidade_de_alertas_sp'),
              'alertas': state_attr('sensor.alertas_meteorologicos_sp', 'alertas')
            } | to_json }}

# Adicionar ao configuration.yaml:
shell_command:
  backup_inmet: 'echo "{{ data }}" >> /config/inmet_alertas_backup.json'
```

---

## Dicas de Uso

1. **Teste suas automações** com alertas amarelos antes de ativar para todos os níveis
2. **Use condições de horário** para evitar notificações durante a madrugada
3. **Combine múltiplos canais** de notificação para alertas críticos
4. **Monitore os logs** para identificar problemas nas automações
5. **Crie backups** das configurações antes de fazer alterações importantes

Personalize essas automações conforme suas necessidades específicas!