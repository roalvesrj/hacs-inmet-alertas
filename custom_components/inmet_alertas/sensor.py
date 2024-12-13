import re
import logging
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from homeassistant.core import EventOrigin
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

URL_RSS = "https://apiprevmet3.inmet.gov.br/avisos/rss"
_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Configura o sensor sem ConfigFlow."""
    async_add_entities([INMETAlertasSensor(hass)], True)

class INMETAlertasSensor(Entity):
    """Sensor para monitorar alertas do INMET."""

    def __init__(self, hass):
        self._name = "INMET Alertas"
        self._state = None
        self._alerts = []
        self._previous_alert_ids = set()  # IDs dos alertas processados anteriormente
        self.hass = hass

    @property
    def name(self):
        """Retorna o nome do sensor."""
        return self._name

    @property
    def state(self):
        """Retorna o estado atual (quantidade de alertas válidos)."""
        return len(self._alerts)

    @property
    def extra_state_attributes(self):
        """Retorna os atributos adicionais do sensor."""
        return {
            "alertas": self._alerts
        }

    async def async_update(self):
        """Atualiza os dados do sensor."""
        session = async_get_clientsession(self.hass)
        async with session.get(URL_RSS) as response:
            if response.status != 200:
                self._alerts = []
                self._state = 0
                _LOGGER.warning(f"Erro ao acessar o feed RSS: {response.status}")
                return

            data = await response.text()

        if not data.strip():
            self._alerts = []
            self._state = 0
            _LOGGER.warning("Resposta vazia do feed RSS.")
            return

        try:
            # Processa o XML
            root = ET.fromstring(data)
        except ET.ParseError as e:
            self._alerts = []
            self._state = 0
            _LOGGER.error(f"Erro ao analisar o XML do feed RSS: {e}")
            return

        channel = root.find("channel")
        items = channel.findall("item") if channel is not None else []

        alerts = []
        new_alert_ids = set()  # IDs de alertas processados nesta execução
        now = datetime.now(timezone.utc)

        for item in items:
            try:
                # Extrair informações básicas
                alert_id = item.find("guid").text
                title = item.find("title").text
                description = item.find("description").text
                pub_date = item.find("pubDate").text

                # Converter pubDate para datetime com fuso horário
                pub_date_dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")

                # Extrair campos do description usando regex
                alerta_nome = re.sub(r"\. Severidade Grau:.*", "", title).strip()
                inicio = re.search(r"Início</th><td>(.*?)</td>", description)
                fim = re.search(r"Fim</th><td>(.*?)</td>", description)
                severidade = re.search(r"Severidade</th><td>(.*?)</td>", description)
                severidade_extra = re.search(r"Severidade Grau: (.*)", title)
                evento = re.search(r"Evento</th><td>(.*?)</td>", description)
                descricao = re.search(r"Descrição</th><td>(.*?)</td>", description)
                area = re.search(r"Área</th><td>Aviso para as Áreas: (.*?)</td>", description)

                # Garantir que 'severidade' tenha um valor válido
                if severidade_extra:
                    severidade = severidade_extra.group(1)
                elif severidade:
                    severidade = severidade.group(1)
                else:
                    severidade = "Desconhecida"

                # Converter datas de início e fim para timezone-aware
                inicio_dt = (
                    datetime.strptime(inicio.group(1), "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)
                    if inicio else None
                )
                fim_dt = (
                    datetime.strptime(fim.group(1), "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)
                    if fim else None
                )

                # Verificar validade do alerta
                if inicio_dt and (fim_dt is None or now <= fim_dt):
                    alert = {
                        "id": alert_id,
                        "status": alerta_nome,
                        "evento": evento.group(1) if evento else "Desconhecido",
                        "severidade": severidade,
                        "inicio": inicio_dt.strftime("%d/%m/%Y %H:%M"),
                        "fim": fim_dt.strftime("%d/%m/%Y %H:%M") if fim_dt else "Indefinido",
                        "descricao": descricao.group(1) if descricao else "Sem descrição",
                        "area": area.group(1) if area else "Indefinido",
                    }
                    alerts.append(alert)
                    new_alert_ids.add(alert_id)

                    # Disparar evento para novos alertas
                    if alert_id not in self._previous_alert_ids:
                        self.hass.bus.async_fire(
                            "inmet_alerta_novo",
                            {
                                "id": alert["id"],
                                "status": alert["status"],
                                "evento": alert["evento"],
                                "severidade": alert["severidade"],
                                "descricao": alert["descricao"],
                                "inicio": alert["inicio"],
                                "fim": alert["fim"],
                                "area": alert["area"],
                            },
                        )

            except Exception as e:
                _LOGGER.error(f"Erro ao processar um alerta: {e}")
                continue

        self._alerts = alerts
        self._state = len(alerts)
        self._previous_alert_ids = new_alert_ids
