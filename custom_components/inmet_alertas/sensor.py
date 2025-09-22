"""Sensor para alertas meteorológicos do INMET."""
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.const import ATTR_ATTRIBUTION

from .utils import (
    SEVERIDADE_CAP_MAP,
    SEVERIDADE_CORES,
    format_datetime,
    is_alert_active,
    check_state_affected,
    filter_state_municipalities,
    calculate_summary,
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = "inmet_alertas"
URL_RSS = "https://apiprevmet3.inmet.gov.br/avisos/rss"
ATTRIBUTION = "Dados fornecidos pelo INMET"

SCAN_INTERVAL = timedelta(minutes=30)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configurar sensor dos alertas INMET."""
    estado = config_entry.data.get("estado")
    update_interval = config_entry.data.get("update_interval", 30)
    notificacoes_perigo = config_entry.data.get("notificacoes_perigo", True)
    
    coordinator = INMETDataUpdateCoordinator(
        hass, estado, update_interval, notificacoes_perigo
    )
    
    await coordinator.async_config_entry_first_refresh()
    
    # Registrar serviço de atualização
    async def handle_atualizar_alertas(call):
        """Handle atualizar_alertas service call."""
        estado_param = call.data.get("estado")
        if estado_param is None or estado_param == estado:
            await coordinator.async_request_refresh()
    
    hass.services.async_register(
        DOMAIN, "atualizar_alertas", handle_atualizar_alertas
    )
    
    async_add_entities([
        INMETAlertasSensor(coordinator, config_entry),
        INMETAlertasCountSensor(coordinator, config_entry),
    ])


class INMETDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordenador para atualização de dados do INMET."""

    def __init__(self, hass: HomeAssistant, estado: str, update_interval: int, notificacoes_perigo: bool):
        """Inicializar coordenador."""
        self.estado = estado
        self.notificacoes_perigo = notificacoes_perigo
        self._previous_alert_ids = set()
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Buscar dados do INMET."""
        try:
            session = async_get_clientsession(self.hass)
            
            # 1. Buscar RSS principal (todos os alertas)
            async with session.get(URL_RSS, timeout=30) as response:
                if response.status != 200:
                    raise UpdateFailed(f"Erro ao acessar o feed RSS: {response.status}")
                
                data = await response.text()
                
            if not data.strip():
                raise UpdateFailed("Resposta vazia do feed RSS")

            try:
                root = ET.fromstring(data)
            except ET.ParseError as e:
                raise UpdateFailed(f"Erro ao analisar XML: {e}")

            # Buscar items do RSS (com diferentes caminhos)
            items = []
            item_paths = ['.//item', './/entry', './channel/item', './/*[local-name()="item"]']
            
            for path in item_paths:
                found_items = root.findall(path)
                if found_items:
                    items = found_items
                    break
            
            _LOGGER.debug(f"Processando {len(items)} alertas do RSS principal")

            # 2. Processar cada alerta individualmente 
            alerts = []
            new_alert_ids = set()
            now = datetime.now(timezone.utc)

            for item in items:
                try:
                    alert_data = await self._process_alert_item(session, item, now)
                    if alert_data:
                        alerts.append(alert_data)
                        new_alert_ids.add(alert_data["id"])
                        
                        # Verificar se é um novo alerta
                        if alert_data["id"] not in self._previous_alert_ids:
                            await self._handle_new_alert(alert_data)
                            
                except Exception as e:
                    _LOGGER.error(f"Erro ao processar alerta: {e}")
                    continue

            self._previous_alert_ids = new_alert_ids
            
            # Limpar notificações de alertas expirados
            await self._cleanup_expired_notifications(alerts)
            
            _LOGGER.info(f"Processamento concluído: {len(alerts)} alertas ativos para {self.estado}")
            
            return {
                "alerts": alerts,
                "count": len(alerts),
                "estado": self.estado,
                "last_update": now.isoformat(),
            }
            
        except Exception as e:
            raise UpdateFailed(f"Erro ao atualizar dados: {e}")

    async def _cleanup_expired_notifications(self, current_alerts: list) -> None:
        """Limpar notificações de alertas que não estão mais ativos."""
        try:
            # IDs dos alertas atualmente ativos
            current_alert_ids = {alert['id'] for alert in current_alerts}
            
            # Verificar se há IDs anteriores para limpar
            if hasattr(self, '_previous_alert_ids') and self._previous_alert_ids:
                # IDs que eram ativos mas não estão mais
                expired_alert_ids = self._previous_alert_ids - current_alert_ids
                
                # Remover notificações dos alertas expirados
                for expired_id in expired_alert_ids:
                    notification_id = f"inmet_alert_{self.estado}_{expired_id}"
                    try:
                        await self.hass.services.async_call(
                            "persistent_notification",
                            "dismiss",
                            {"notification_id": notification_id},
                        )
                        _LOGGER.debug(f"Notificação removida: {notification_id}")
                    except Exception as e:
                        _LOGGER.warning(f"Erro ao remover notificação {notification_id}: {e}")
                        
        except Exception as e:
            _LOGGER.error(f"Erro na limpeza de notificações: {e}")

    async def _process_alert_item(self, session, item, now: datetime) -> dict[str, Any] | None:
        """Processar um item de alerta individual."""
        try:
            # Extrair dados básicos do item
            title_elem = item.find("title")
            link_elem = item.find("link")
            guid_elem = item.find("guid") 
            desc_elem = item.find("description")
            pubdate_elem = item.find("pubDate")
            
            if not all([title_elem is not None, link_elem is not None, guid_elem is not None]):
                return None
                
            title = title_elem.text.strip() if title_elem.text else ""
            link = link_elem.text.strip() if link_elem.text else ""
            alert_id = guid_elem.text.strip() if guid_elem.text else ""
            description = desc_elem.text if desc_elem is not None and desc_elem.text else ""
            pub_date = pubdate_elem.text if pubdate_elem is not None and pubdate_elem.text else ""

            _LOGGER.debug(f"Processando alerta {alert_id}: {title}")

            # Verificar se o alerta afeta o estado configurado
            cap_data = await self._get_cap_data(session, link)
            if not cap_data:
                return None
                
            if not check_state_affected(cap_data, self.estado):
                return None

            # Verificar se o alerta está ativo (dentro do período de validade)
            if not is_alert_active(cap_data, now):
                _LOGGER.debug(f"Alerta {alert_id} está fora do período de validade")
                return None

            # Extrair nome do alerta (sem severidade)
            alerta_nome = re.sub(r"\. Severidade Grau:.*", "", title).strip()
            
            # Mapear severidade CAP para INMET
            severidade_cap = cap_data.get('severity', '')
            severidade_inmet = SEVERIDADE_CAP_MAP.get(severidade_cap, 
                                                     cap_data.get('severidade_titulo', 'Desconhecida'))
            
            # Ícone baseado na severidade
            icone = SEVERIDADE_CORES.get(severidade_inmet or "Desconhecida", "ℹ️")
            
            # Formatar datas
            inicio_formatado = format_datetime(cap_data.get('onset', ''))
            fim_formatado = format_datetime(cap_data.get('expires', ''))
            
            # Filtrar municípios do estado
            municipios_estado = filter_state_municipalities(
                cap_data.get('municipios', ''), self.estado
            )

            return {
                "id": alert_id,
                "titulo": alerta_nome,
                "evento": cap_data.get('event', 'Desconhecido'),
                "severidade": severidade_inmet,
                "severidade_cap": severidade_cap,
                "icone": icone,
                "inicio": inicio_formatado,
                "fim": fim_formatado,
                "descricao": cap_data.get('description', ''),
                "instrucoes": cap_data.get('instruction', ''),
                "municipios_estado": municipios_estado,
                "total_municipios_estado": len(municipios_estado),
                "link": link,
                "ativo": True,  # Todos retornados são ativos
                "publicado": pub_date,
                "area_desc": cap_data.get('area_desc', ''),
                "cor_oficial": cap_data.get('color_risk', ''),
                "url_grafica": cap_data.get('web', ''),
            }
            
        except Exception as e:
            _LOGGER.error(f"Erro ao processar item do alerta: {e}")
            return None

    async def _get_cap_data(self, session, url: str) -> dict[str, Any] | None:
        """Obter dados CAP (Common Alerting Protocol) do alerta específico."""
        try:
            async with session.get(url, timeout=30) as response:
                if response.status != 200:
                    _LOGGER.warning(f"Erro ao acessar RSS específico: {response.status}")
                    return None
                    
                data = await response.text()

            root = ET.fromstring(data)
            
            # Namespace CAP
            ns = {'cap': 'urn:oasis:names:tc:emergency:cap:1.2'}
            cap_data = {}
            
            # Elementos diretos do alert
            for field in ['identifier', 'sender', 'sent', 'status', 'msgType']:
                elem = root.find(f'cap:{field}', ns)
                if elem is not None and elem.text:
                    cap_data[field] = elem.text.strip()
            
            # Elementos do info
            info = root.find('cap:info', ns)
            if info is not None:
                for field in ['language', 'category', 'event', 'severity', 'urgency', 
                             'certainty', 'onset', 'expires', 'description', 'instruction', 
                             'web', 'contact']:
                    elem = info.find(f'cap:{field}', ns)
                    if elem is not None and elem.text:
                        cap_data[field] = elem.text.strip()
                
                # Parâmetros
                for param in info.findall('cap:parameter', ns):
                    name_elem = param.find('cap:valueName', ns)
                    value_elem = param.find('cap:value', ns)
                    
                    if (name_elem is not None and name_elem.text and 
                        value_elem is not None and value_elem.text):
                        param_name = name_elem.text.strip()
                        param_value = value_elem.text.strip()
                        
                        if param_name == 'ColorRisk':
                            cap_data['color_risk'] = param_value
                        elif param_name == 'Municipios':
                            cap_data['municipios'] = param_value
                        elif param_name == 'Estados':
                            cap_data['estados'] = param_value
                
                # Área
                area = info.find('cap:area', ns)
                if area is not None:
                    area_desc = area.find('cap:areaDesc', ns)
                    if area_desc is not None and area_desc.text:
                        cap_data['area_desc'] = area_desc.text.strip()
                    
                    polygon = area.find('cap:polygon', ns)
                    if polygon is not None and polygon.text:
                        cap_data['polygon'] = polygon.text.strip()
            
            return cap_data
            
        except Exception as e:
            _LOGGER.error(f"Erro ao processar RSS específico {url}: {e}")
            return None

    async def _handle_new_alert(self, alert_data: dict[str, Any]) -> None:
        """Lidar com novo alerta detectado."""
        _LOGGER.info(f"Novo alerta detectado: {alert_data['titulo']}")
        
        # Disparar evento no Home Assistant
        self.hass.bus.async_fire(
            "inmet_novo_alerta",
            {
                "alert_id": alert_data["id"],
                "titulo": alert_data["titulo"],
                "severidade": alert_data["severidade"],
                "evento": alert_data["evento"],
                "estado": self.estado,
                "inicio": alert_data["inicio"],
                "fim": alert_data["fim"],
                "municipios": alert_data.get("total_municipios_estado", 0),
                "area_desc": alert_data.get("area_desc", ""),
                "ativo": alert_data["ativo"],
            }
        )
        
        # Disparar evento específico para alertas perigosos
        if alert_data["severidade"] in ["Perigo", "Grande Perigo"]:
            self.hass.bus.async_fire(
                "inmet_alerta_perigoso",
                {
                    "alert_id": alert_data["id"],
                    "titulo": alert_data["titulo"],
                    "severidade": alert_data["severidade"],
                    "evento": alert_data["evento"],
                    "estado": self.estado,
                    "inicio": alert_data["inicio"],
                    "fim": alert_data["fim"],
                    "municipios": alert_data.get("total_municipios_estado", 0),
                    "area_desc": alert_data.get("area_desc", ""),
                }
            )
        
        # Enviar notificação persistente se configurado
        if self.notificacoes_perigo and alert_data["severidade"] in ["Perigo", "Grande Perigo"]:
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": f"🚨 Alerta Meteorológico - {alert_data['severidade']} ({self.estado})",
                    "message": f"**{alert_data['titulo']}**\n\n"
                             f"Evento: {alert_data['evento']}\n"
                             f"Estado: {self.estado}\n"
                             f"Início: {alert_data['inicio']}\n"
                             f"Fim: {alert_data['fim']}\n"
                             f"Municípios afetados: {alert_data.get('total_municipios_estado', 0)}\n\n"
                             f"{alert_data.get('descricao', '')[:200]}...",
                    "notification_id": f"inmet_alert_{self.estado}_{alert_data['id']}",
                },
            )


class INMETAlertasSensor(CoordinatorEntity, SensorEntity):
    """Sensor principal dos alertas INMET."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:weather-cloudy-alert"

    def __init__(self, coordinator: INMETDataUpdateCoordinator, config_entry: ConfigEntry):
        """Inicializar sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._estado = coordinator.estado
        self._attr_unique_id = f"{DOMAIN}_{self._estado}_alertas"
        self._attr_name = f"Alertas Meteorológicos {self._estado}"

    @property
    def native_value(self) -> str | None:
        """Retornar o valor do sensor."""
        if not self.coordinator.data or not self.coordinator.data.get("alerts"):
            return "Nenhum alerta ativo"
        
        alerts = self.coordinator.data["alerts"]
        if len(alerts) == 1:
            return f"{alerts[0]['titulo']}"
        else:
            return f"{len(alerts)} alertas ativos"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Retornar atributos adicionais."""
        if not self.coordinator.data:
            return {ATTR_ATTRIBUTION: ATTRIBUTION}
            
        data = self.coordinator.data
        attributes = {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            "estado": self._estado,
            "total_alertas": data.get("count", 0),
            "ultima_atualizacao": data.get("last_update"),
            "alertas": data.get("alerts", []),
        }
        
        # Adicionar contadores por severidade
        if data.get("alerts"):
            severidades = {}
            municipios_unicos = set()
            area_total = 0
            severidade_maxima = None
            
            # Severidades por prioridade
            severidade_prioridade = {"Grande Perigo": 3, "Perigo": 2, "Perigo Potencial": 1}
            max_prioridade = 0
            
            for alert in data["alerts"]:
                # Contar severidades
                sev = alert.get("severidade", "Desconhecida")
                severidades[sev] = severidades.get(sev, 0) + 1
                
                # Verificar severidade máxima
                prioridade = severidade_prioridade.get(sev, 0)
                if prioridade > max_prioridade:
                    max_prioridade = prioridade
                    severidade_maxima = sev
                
                # Coletar municípios únicos
                for municipio in alert.get("municipios_estado", []):
                    municipios_unicos.add(municipio)
            
            attributes.update({
                "alertas_por_severidade": severidades,
                "severidade_maxima": severidade_maxima,
                "municipios_unicos": len(municipios_unicos),
                "municipios_afetados": list(municipios_unicos)[:10],  # Primeiros 10
            })
            
        return attributes


class INMETAlertasCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor de contagem de alertas INMET."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:counter"
    _attr_native_unit_of_measurement = "alertas"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: INMETDataUpdateCoordinator, config_entry: ConfigEntry):
        """Inicializar sensor de contagem."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._estado = coordinator.estado
        self._attr_unique_id = f"{DOMAIN}_{self._estado}_count"
        self._attr_name = f"Quantidade de Alertas {self._estado}"

    @property
    def native_value(self) -> int:
        """Retornar a contagem de alertas."""
        if not self.coordinator.data:
            return 0
        return self.coordinator.data.get("count", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Retornar atributos adicionais."""
        if not self.coordinator.data:
            return {ATTR_ATTRIBUTION: ATTRIBUTION}
            
        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            "estado": self._estado,
            "ultima_atualizacao": self.coordinator.data.get("last_update"),
        }
