"""Sensor para alertas meteorológicos do INMET."""
import asyncio
import logging
import random
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.util import dt as dt_util

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
    format_datetime,
    is_alert_active,
    check_state_affected,
    filter_state_municipalities,
    calculate_summary,
)
from .const import (
    CORES_INMET_MAPA,
    SEVERIDADE_CAP_MAP,
    SEVERIDADE_CORES,
    SEVERIDADE_PRIORIDADES,
    MICRORREGIOES_ESTADOS,
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = "inmet_alertas"
URL_RSS = "https://apiprevmet3.inmet.gov.br/avisos/rss"
ATTRIBUTION = "Dados fornecidos pelo INMET"

SCAN_INTERVAL = timedelta(minutes=45)  # Reduzido de 30 para 45 min para evitar rate limiting

# Headers para evitar bloqueios HTTP 403 e rate limiting
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/rss+xml, application/xml, text/xml, */*',
    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configurar sensor dos alertas INMET."""
    estado = config_entry.data.get("estado")
    update_interval = config_entry.options.get("update_interval", config_entry.data.get("update_interval", 30))
    notificacoes_perigo = config_entry.options.get("notificacoes_perigo", config_entry.data.get("notificacoes_perigo", True))
    
    coordinator = INMETDataUpdateCoordinator(
        hass, estado, update_interval, notificacoes_perigo
    )
    
    # Registrar coordenador para acesso pelo serviço de atualização
    hass.data.setdefault(DOMAIN, {"coordinators": {}})
    hass.data[DOMAIN].setdefault("coordinators", {})
    hass.data[DOMAIN]["coordinators"][config_entry.entry_id] = coordinator

    # Primeira atualização em background para não bloquear startup
    async def _first_refresh():
        try:
            await coordinator.async_refresh()
        except Exception:
            _LOGGER.debug("Primeira atualização falhou, será tentada novamente no próximo ciclo")

    hass.async_create_task(_first_refresh())

    async_add_entities([
        INMETAlertasSensor(coordinator, config_entry),
        INMETAlertasCountSensor(coordinator, config_entry),
        INMETAlertasMapaSensor(coordinator, config_entry),
        INMETAlertasDiagnosticoSensor(coordinator, config_entry),
    ])


class INMETDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordenador para atualização de dados do INMET."""

    def __init__(self, hass: HomeAssistant, estado: str, update_interval: int, notificacoes_perigo: bool):
        """Inicializar coordenador."""
        self.estado = estado
        self.notificacoes_perigo = notificacoes_perigo
        self._alertas_persistentes = {}  # Dict[str, dict] - ID -> dados completos do alerta
        self._pending_caps = []  # Lista de CAPs para retry
        self._retry_count = {}
        self._notified_rate_limited = False  # Flag para sinalizar listeners durante rate limiting
        self._diagnostico = {
            "ultimo_http_status": None,
            "rate_limit_hits": 0,
            "pending_caps": 0,
            "ultimo_erro": None,
            "total_alertas_api": 0,
            "ciclo_atual": None,
        }
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Buscar dados do INMET."""
        self._diagnostico["ciclo_atual"] = dt_util.now().isoformat()
        
        try:
            session = async_get_clientsession(self.hass)
            
            # 1. Buscar RSS principal (todos os alertas)
            async with session.get(URL_RSS, headers=DEFAULT_HEADERS, timeout=30) as response:
                self._diagnostico["ultimo_http_status"] = response.status
                if response.status != 200:
                    raise UpdateFailed(f"Erro ao acessar o feed RSS: {response.status}")
                
                data = await response.text()
                
            if not data.strip():
                raise UpdateFailed("Resposta vazia do feed RSS")

            # Verificar se a resposta é XML válido
            if not data.strip():
                raise UpdateFailed("Resposta vazia do feed RSS")
            
            # Verificar rate limiting (não é erro, é comportamento esperado)
            if "limite de requisições" in data.lower() or "rate limit" in data.lower():
                self._diagnostico["rate_limit_hits"] += 1
                _LOGGER.info("⏳ INMET aplicou rate limiting no RSS principal. Processando apenas CAPs pendentes...")
                
                # Mesmo com rate limiting no RSS, processar CAPs pendentes existentes
                alerts = []
                new_alert_ids = set()
                now = dt_util.now()
                
                # Se há CAPs pendentes, processá-los mesmo com rate limiting no RSS principal
                if self._pending_caps:
                    session = async_get_clientsession(self.hass)
                    _LOGGER.info(f"Processando {len(self._pending_caps)} CAPs pendentes durante rate limiting...")
                    await self._process_pending_caps(session, alerts, new_alert_ids, now)
                
                # IMPORTANTE: Durante rate limiting, usar persistência para manter alertas existentes!
                alertas_finais = await self._merge_alertas_com_persistencia(alerts, now)
                
                # Sinalizar para que listeners atualizem mesmo sem dados novos
                self._notified_rate_limited = True
                self._diagnostico["pending_caps"] = len(self._pending_caps)
                
                # Retornar dados (com alertas persistentes mantidos mesmo durante rate limiting)
                return {
                    "alerts": alertas_finais,
                    "count": len(alertas_finais),
                    "estado": self.estado,
                    "last_update": now.isoformat(),
                    "rate_limited": True,  # Indicador para logs
                    "diagnostico": self._diagnostico.copy(),
                }
            
            if not data.strip().startswith('<?xml') and not data.strip().startswith('<rss'):
                _LOGGER.error(f"Resposta não é XML válido. Content-Type: {response.headers.get('content-type', 'N/A')}")
                _LOGGER.error(f"Primeiros 200 chars: {data[:200]}")
                raise UpdateFailed("INMET retornou conteúdo inválido (não é XML)")

            try:
                root = ET.fromstring(data)
            except ET.ParseError as e:
                _LOGGER.error(f"Erro ao analisar XML. Primeiros 200 chars da resposta: {data[:200]}")
                raise UpdateFailed(f"XML inválido recebido do INMET: {e}")

            # Buscar items do RSS (com diferentes caminhos)
            items = []
            item_paths = ['.//item', './/entry', './channel/item', './/*[local-name()="item"]']
            
            for path in item_paths:
                found_items = root.findall(path)
                if found_items:
                    items = found_items
                    break
            
            _LOGGER.debug(f"Processando {len(items)} alertas do RSS principal")
            self._diagnostico["total_alertas_api"] = len(items)

            # 2. Processar cada alerta individualmente (máximo 50 por ciclo)
            alerts = []
            new_alert_ids = set()
            now = dt_util.now()
            processed_count = 0
            max_caps_per_cycle = 50

            # Primeiro processar CAPs pendentes de tentativas anteriores
            if self._pending_caps:
                _LOGGER.info(f"Processando {len(self._pending_caps)} CAPs pendentes...")
                await self._process_pending_caps(session, alerts, new_alert_ids, now)
            
            # Depois processar novos itens (limitado)
            for item in items:
                if processed_count >= max_caps_per_cycle:
                    _LOGGER.info(f"Limite de {max_caps_per_cycle} CAPs por ciclo atingido. Restantes serão processados na próxima atualização.")
                    break
                    
                try:
                    alert_data = await self._process_alert_item(session, item, now)
                    if alert_data:
                        alerts.append(alert_data)
                        new_alert_ids.add(alert_data["id"])
                        processed_count += 1
                        
                        # Verificar se é um novo alerta
                        if alert_data["id"] not in self._alertas_persistentes:
                            await self._handle_new_alert(alert_data)
                    
                    # Delay com jitter para evitar padrões
                    await asyncio.sleep(0.5 + random.uniform(0.1, 0.3))
                            
                except Exception as e:
                    _LOGGER.error(f"Erro ao processar alerta: {e}")
                    continue

            # Capturar IDs anteriores para limpeza de notificações
            previous_ids = set(self._alertas_persistentes.keys())
            
            # Merge inteligente de alertas para preservar persistência
            alertas_finais = await self._merge_alertas_com_persistencia(alerts, now)
            
            # Limpar notificações de alertas realmente expirados
            await self._cleanup_expired_notifications(alertas_finais, previous_ids)
            
            _LOGGER.info(f"Processamento concluído: {len(alertas_finais)} alertas persistentes para {self.estado}")
            _LOGGER.info(f"  - Novos do scan atual: {len(alerts)}")
            _LOGGER.info(f"  - Mantidos de scans anteriores: {len(alertas_finais) - len(alerts)}")
            _LOGGER.info(f"CAPs pendentes para próxima tentativa: {len(self._pending_caps)}")
            self._diagnostico["pending_caps"] = len(self._pending_caps)
            
            return {
                "alerts": alertas_finais,
                "count": len(alertas_finais),
                "estado": self.estado,
                "last_update": now.isoformat(),
                "diagnostico": self._diagnostico.copy(),
            }
            
        except Exception as e:
            # Rate limiting não é erro - já foi tratado acima
            error_msg = str(e).lower()
            if "rate limiting" in error_msg or "limite de requisições" in error_msg:
                _LOGGER.debug(f"Rate limiting detectado, mantendo alertas persistentes: {e}")
                
                # Mesmo durante erro de rate limiting, manter alertas existentes válidos
                alertas_finais = await self._merge_alertas_com_persistencia([], dt_util.now())
                self._diagnostico["pending_caps"] = len(self._pending_caps)
                
                return {
                    "alerts": alertas_finais,
                    "count": len(alertas_finais),
                    "estado": self.estado,
                    "last_update": dt_util.now().isoformat(),
                    "rate_limited": True,
                    "diagnostico": self._diagnostico.copy(),
                }
            else:
                self._diagnostico["ultimo_erro"] = str(e)[:200]
                raise UpdateFailed(f"Erro ao atualizar dados: {e}")
            
    async def _process_pending_caps(self, session, alerts: list, new_alert_ids: set, now: datetime) -> None:
        """Processar CAPs que falharam em tentativas anteriores."""
        retry_caps = []
        
        for cap_info in self._pending_caps[:10]:  # Máximo 10 retries por ciclo
            try:
                # Delay extra para retries
                await asyncio.sleep(1.0 + random.uniform(0.2, 0.5))
                
                alert_data = await self._process_alert_item(session, cap_info['item'], now, retry=True)
                if alert_data:
                    alerts.append(alert_data)
                    new_alert_ids.add(alert_data["id"])
                    _LOGGER.debug(f"✅ CAP {cap_info['id']} processado com sucesso no retry")
                    # Resetar contagem ao obter sucesso
                    self._retry_count[cap_info['id']] = 0
                else:
                    # Ainda com problemas - manter na fila sem limite de tentativas
                    # Usar backoff exponencial: só tentar novamente após N ciclos
                    self._retry_count[cap_info['id']] = self._retry_count.get(cap_info['id'], 0) + 1
                    tentativa = self._retry_count[cap_info['id']]
                    
                    if tentativa <= 10:
                        retry_caps.append(cap_info)
                        _LOGGER.debug(f"🔄 CAP {cap_info['id']} ainda com rate limiting, tentativa {tentativa}")
                    else:
                        # Após 10 tentativas, dar um desconto: resetar a contagem para continuar tentando
                        # mas com prioridade menor (vai para o final da fila)
                        _LOGGER.info(f"🔄 CAP {cap_info['id']} ainda com rate limiting após {tentativa} tentativas, resetando contagem")
                        self._retry_count[cap_info['id']] = 0
                        retry_caps.append(cap_info)
                        
            except Exception as e:
                error_msg = str(e).lower()
                # Se for rate limiting, apenas debug
                if "rate limiting" in error_msg or "limite de requisições" in error_msg:
                    _LOGGER.debug(f"Rate limiting persistente para CAP {cap_info['id']}")
                else:
                    _LOGGER.warning(f"Erro no retry do CAP {cap_info['id']}: {e}")
                
                # Manter na fila sem limite de tentativas
                self._retry_count[cap_info['id']] = self._retry_count.get(cap_info['id'], 0) + 1
                if self._retry_count[cap_info['id']] <= 10:
                    retry_caps.append(cap_info)
                else:
                    self._retry_count[cap_info['id']] = 0
                    retry_caps.append(cap_info)
        
        # Atualizar lista de pendentes (remover os removidos + os que falharam ainda estão)
        self._pending_caps = retry_caps + self._pending_caps[10:]
    
    async def _merge_alertas_com_persistencia(self, novos_alertas: list, agora: datetime) -> list:
        """Fazer merge inteligente entre alertas existentes e novos, preservando persistência.
        
        Esta função resolve o problema principal onde alertas 'somem' durante scans RSS.
        
        Args:
            novos_alertas: Lista de alertas do scan atual
            agora: Timestamp atual para verificação de expiração
            
        Returns:
            Lista final de alertas (existentes válidos + novos)
        """
        try:
            alertas_finais = {}
            alertas_removidos = 0
            alertas_mantidos = 0
            alertas_novos = 0
            
            # 1. VERIFICAR ALERTAS EXISTENTES - manter os que ainda são válidos
            for alert_id, alert_data in self._alertas_persistentes.items():
                if self._is_alerta_ainda_valido(alert_data, agora):
                    alertas_finais[alert_id] = alert_data
                    alertas_mantidos += 1
                    _LOGGER.debug(f"📌 Mantendo alerta persistente: {alert_id}")
                else:
                    alertas_removidos += 1
                    _LOGGER.info(f"⏰ Removendo alerta expirado: {alert_id} - {alert_data.get('titulo', 'Sem título')}")
            
            # 2. ADICIONAR/ATUALIZAR ALERTAS DO SCAN ATUAL
            for novo_alerta in novos_alertas:
                alert_id = novo_alerta["id"]
                
                if alert_id in alertas_finais:
                    # Atualizar dados do alerta existente com informações mais recentes
                    alertas_finais[alert_id].update(novo_alerta)
                    _LOGGER.debug(f"🔄 Atualizando alerta existente: {alert_id}")
                else:
                    # Adicionar novo alerta
                    alertas_finais[alert_id] = novo_alerta
                    alertas_novos += 1
                    _LOGGER.debug(f"✨ Adicionando novo alerta: {alert_id}")
            
            # 3. ATUALIZAR CACHE PERSISTENTE
            self._alertas_persistentes = alertas_finais.copy()
            
            # 4. LOG DETALHADO DO PROCESSAMENTO
            if alertas_mantidos > 0 or alertas_removidos > 0:
                _LOGGER.info(f"🔄 Merge de alertas concluído:")
                _LOGGER.info(f"  ✨ Novos: {alertas_novos}")
                _LOGGER.info(f"  📌 Mantidos: {alertas_mantidos}")
                _LOGGER.info(f"  ⏰ Removidos (expirados): {alertas_removidos}")
                _LOGGER.info(f"  📊 Total final: {len(alertas_finais)}")
            
            return list(alertas_finais.values())
            
        except Exception as e:
            _LOGGER.error(f"Erro no merge de alertas: {e}")
            # Em caso de erro, retornar pelo menos os novos alertas
            return novos_alertas
    
    def _is_alerta_ainda_valido(self, alert_data: dict, agora: datetime) -> bool:
        """Verificar se um alerta ainda é válido (não expirou).
        
        Args:
            alert_data: Dados do alerta
            agora: Timestamp atual
            
        Returns:
            True se o alerta ainda está válido
        """
        try:
            # Usar a mesma lógica de validação existente
            fim_iso = alert_data.get('fim', '')  # Campo 'fim' formatado brasileiro
            
            if not fim_iso:
                # Se não há data de fim, assumir válido (alerta permanente)
                return True
            
            # Converter data brasileira de volta para ISO para comparação
            try:
                # Tentar diferentes formatos de data
                fim_obj = None
                
                # Formato ISO original (se ainda estiver no formato original)
                for campo in ['expires', 'fim']:
                    iso_date = alert_data.get(campo, '')
                    if iso_date and 'T' in iso_date:
                        try:
                            fim_obj = dt_util.parse_datetime(iso_date)
                            if fim_obj:
                                break
                        except:
                            continue
                
                # Se não conseguiu parsear, assumir válido por segurança
                if not fim_obj:
                    _LOGGER.debug(f"Não foi possível verificar expiração do alerta {alert_data.get('id', 'desconhecido')}, assumindo válido")
                    return True
                
                # Comparar com tempo atual
                return fim_obj > agora
                
            except Exception as e:
                _LOGGER.warning(f"Erro ao verificar validade do alerta {alert_data.get('id', 'desconhecido')}: {e}")
                return True  # Assumir válido em caso de erro
                
        except Exception as e:
            _LOGGER.error(f"Erro crítico na validação de alerta: {e}")
            return True  # Assumir válido para evitar perda de dados

    async def _cleanup_expired_notifications(self, current_alerts: list, previous_ids: set | None = None) -> None:
        """Limpar notificações de alertas que não estão mais ativos."""
        if not previous_ids:
            return

        try:
            current_alert_ids = {alert['id'] for alert in current_alerts}
            expired_alert_ids = previous_ids - current_alert_ids

            for expired_id in expired_alert_ids:
                notification_id = f"inmet_alert_{self.estado}_{expired_id}"
                try:
                    await self.hass.services.async_call(
                        "persistent_notification",
                        "dismiss",
                        {"notification_id": notification_id},
                    )
                except Exception:
                    pass

        except Exception as e:
            _LOGGER.error(f"Erro na limpeza de notificações: {e}")

    async def _process_alert_item(self, session, item, now: datetime, retry: bool = False) -> dict[str, Any] | None:
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

            if not retry:
                _LOGGER.debug(f"Processando alerta {alert_id}: {title}")

            # Verificar se o alerta afeta o estado configurado
            cap_data = await self._get_cap_data_with_retry(session, link, alert_id, item, retry)
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
                "onset": cap_data.get('onset', ''),  # Campo original ISO para validação
                "expires": cap_data.get('expires', ''),  # Campo original ISO para validação
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
                "color_risk": cap_data.get('color_risk', ''),  # Para compatibilidade
                "dados_geograficos": cap_data.get('dados_geograficos'),  # Dados geográficos processados
            }
            
        except Exception as e:
            _LOGGER.error(f"Erro ao processar item do alerta: {e}")
            return None

    async def _get_cap_data_with_retry(self, session, url: str, alert_id: str, item, is_retry: bool = False) -> dict[str, Any] | None:
        """Obter dados CAP com tratamento de rate limiting e retry automático."""
        try:
            cap_data = await self._get_cap_data(session, url)
            # Se conseguiu obter dados, garantir que não há pending duplicado
            if cap_data and not is_retry:
                self._remove_pending_cap(alert_id)
            return cap_data
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Detectar rate limiting ou problemas de conectividade
            if any(term in error_msg for term in ["rate limiting", "limite de requisições", "connection reset", "timeout"]):
                if not is_retry:
                    # Só adicionar à fila de pending se ainda não estiver
                    if not self._is_pending_cap(alert_id):
                        cap_info = {
                            'id': alert_id,
                            'url': url,
                            'item': item  # Guardar o item completo para retry
                        }
                        self._pending_caps.append(cap_info)
                        _LOGGER.debug(f"⏳ CAP {alert_id} adicionado à fila de retry (rate limiting temporário)")
                    else:
                        _LOGGER.debug(f"⏳ CAP {alert_id} já está na fila de retry, ignorando duplicata")
                    return None
                else:
                    # Em retry, apenas debug - não é erro
                    _LOGGER.debug(f"Retry ainda com rate limiting para CAP {alert_id} - tentará novamente")
                    return None
            else:
                # Erro diferente de rate limiting, logar e seguir
                _LOGGER.error(f"Erro ao obter CAP {url}: {e}")
                return None

    def _is_pending_cap(self, alert_id: str) -> bool:
        """Verificar se um alerta já está na fila de pending."""
        return any(cap['id'] == alert_id for cap in self._pending_caps)

    def _remove_pending_cap(self, alert_id: str) -> None:
        """Remover um alerta da fila de pending se presente."""
        self._pending_caps = [cap for cap in self._pending_caps if cap['id'] != alert_id]
        # Resetar contagem de retry quando o CAP é removido com sucesso
        self._retry_count[alert_id] = 0

    async def _get_cap_data(self, session, url: str) -> dict[str, Any] | None:
        """Obter dados CAP (Common Alerting Protocol) do alerta específico."""
        try:
            async with session.get(url, headers=DEFAULT_HEADERS, timeout=30) as response:
                if response.status != 200:
                    _LOGGER.warning(f"Erro ao acessar RSS específico: {response.status}")
                    return None
                    
                data = await response.text()
                
            if not data.strip():
                _LOGGER.warning(f"Resposta vazia do CAP: {url}")
                return None
                
            # Verificar rate limiting no CAP
            if "limite de requisições" in data.lower() or "rate limit" in data.lower():
                _LOGGER.info(f"⏳ Rate limiting detectado no CAP {url} - será tentado novamente")
                raise Exception("Rate limiting")
                
            # Verificar se é XML válido antes de tentar processar
            if not data.strip().startswith('<?xml') and not data.strip().startswith('<alert'):
                _LOGGER.warning(f"CAP não é XML válido. URL: {url}")
                _LOGGER.debug(f"Conteúdo recebido: {data[:100]}")
                return None

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
                
                # Área e dados geográficos
                areas = info.findall('cap:area', ns)
                if not areas:
                    areas = info.findall('.//area')
                    
                areas_desc = []
                poligonos = []
                
                for area in areas:
                    # Descrição da área
                    area_desc = area.find('cap:areaDesc', ns)
                    if area_desc is None:
                        area_desc = area.find('areaDesc')
                    if area_desc is not None and area_desc.text:
                        areas_desc.append(area_desc.text.strip())
                    
                    # Polígonos - usar múltiplas estratégias
                    polygon_elem = area.find('cap:polygon', ns)
                    if polygon_elem is None:
                        polygon_elem = area.find('polygon')
                    if polygon_elem is None:
                        # Busca recursiva
                        for child in area.iter():
                            if child.tag.endswith('polygon'):
                                polygon_elem = child
                                break
                    
                    if polygon_elem is not None and polygon_elem.text:
                        polygon_text = polygon_elem.text.strip()
                        if polygon_text:
                            poligonos.append(polygon_text)
                            _LOGGER.debug(f"Polígono extraído: {polygon_text[:100]}...")
                
                cap_data['area_desc'] = '; '.join(areas_desc)
                cap_data['polygons'] = poligonos
                
                # Processar dados geográficos se existirem polígonos
                if poligonos:
                    _LOGGER.info(f"Processando {len(poligonos)} polígonos encontrados")
                    try:
                        # Importar GeoProcessor
                        from .helpers.geo_processor import GeoProcessor
                        
                        dados_geo = []
                        area_total = 0.0
                        
                        for i, polygon_text in enumerate(poligonos):
                            resultado_geo = GeoProcessor.processar_poligono_completo(
                                polygon_text, 
                                f"alerta_{i}"
                            )
                            if resultado_geo:
                                dados_geo.append(resultado_geo)
                                area_total += resultado_geo.get('area_km2', 0)
                        
                        # Combinar dados geográficos
                        if dados_geo:
                            dados_combinados = GeoProcessor.combinar_poligonos_estado(dados_geo)
                            
                            cap_data['dados_geograficos'] = {
                                'poligonos_individuais': dados_geo,
                                'area_total_km2': dados_combinados['area_total_km2'],
                                'centro_geografico': dados_combinados['centro_estado'],
                                'bounding_box': dados_combinados['bounding_box_estado'],
                                'zoom_recomendado': dados_combinados['zoom_estado'],
                                'total_poligonos': len(dados_geo)
                            }
                            
                            _LOGGER.info(f"Dados geográficos processados: {len(dados_geo)} polígonos, "
                                       f"{dados_combinados['area_total_km2']} km²")
                    except Exception as e:
                        _LOGGER.error(f"Erro ao processar dados geográficos: {e}")
                        cap_data['dados_geograficos'] = None
            
            return cap_data
            
        except Exception as e:
            error_msg = str(e).lower()
            # Rate limiting não é erro - é comportamento normal da API
            if "rate limit" in error_msg or "limite de requisições" in error_msg:
                _LOGGER.debug(f"Rate limiting aplicado para {url} - normal")
                return None
            
            _LOGGER.error(f"Erro ao processar RSS específico {url}: {e}")
            # Se for erro de conexão, tentar novamente
            if "Connection reset by peer" in str(e) or "timeout" in str(e).lower():
                raise Exception("Erro de conectividade - retry necessário")
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
                "descricao": alert_data.get("descricao", ""),
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
                    "descricao": alert_data.get("descricao", ""),
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
            return {
                ATTR_ATTRIBUTION: ATTRIBUTION,
                "estado": self._estado,
                "total_alertas": 0,
                "ultima_atualizacao": None,
                "alertas": [],
                "alertas_por_severidade": {},
                "severidade_maxima": None,
                "municipios_unicos": 0,
                "municipios_afetados": [],
            }

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
            
            max_prioridade = 0

            for alert in data["alerts"]:
                sev = alert.get("severidade", "Desconhecida")
                severidades[sev] = severidades.get(sev, 0) + 1

                prioridade = SEVERIDADE_PRIORIDADES.get(sev, 0)
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
            return {
                ATTR_ATTRIBUTION: ATTRIBUTION,
                "estado": self._estado,
                "ultima_atualizacao": None,
            }

        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            "estado": self._estado,
            "ultima_atualizacao": self.coordinator.data.get("last_update"),
        }


class INMETAlertasMapaSensor(CoordinatorEntity, SensorEntity):
    """Sensor de mapa geográfico dos alertas INMET."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "polígonos"
    _attr_icon = "mdi:map-marker-multiple"

    def __init__(self, coordinator: INMETDataUpdateCoordinator, config_entry: ConfigEntry):
        """Inicializar sensor de mapa."""
        super().__init__(coordinator)
        self._estado = config_entry.data.get("estado")
        self._attr_unique_id = f"inmet_alertas_mapa_{self._estado}"
        self._attr_name = f"INMET Alertas Mapa {self._estado}"

    @property
    def native_value(self) -> int:
        """Valor do sensor (número de polígonos com dados geográficos)."""
        if not self.coordinator.data or "alerts" not in self.coordinator.data:
            return 0

        alertas = self.coordinator.data["alerts"]
        poligonos_com_dados = 0
        
        for alerta in alertas:
            dados_geo = alerta.get("dados_geograficos")
            if dados_geo and dados_geo.get("poligonos_individuais"):
                poligonos_com_dados += len(dados_geo["poligonos_individuais"])
        
        return poligonos_com_dados

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Atributos extras do sensor."""
        if not self.coordinator.data or "alerts" not in self.coordinator.data:
            return {
                ATTR_ATTRIBUTION: ATTRIBUTION,
                "estado": self._estado,
                "poligonos": [],
                "area_total_afetada_km2": 0.0,
                "centro_geografico": None,
                "bounding_box": None,
                "zoom_recomendado": 8,
                "camadas_por_severidade": {},
                "total_alertas_com_geo": 0,
            }

        alertas = self.coordinator.data["alerts"]
        
        # Processar todos os polígonos por severidade
        poligonos_por_severidade = {
            "Grande Perigo": [],
            "Perigo": [],
            "Perigo Potencial": []
        }
        
        area_total = 0.0
        todos_centros = []
        todos_bboxes = []
        total_alertas_com_geo = 0
        
        for alerta in alertas:
            dados_geo = alerta.get("dados_geograficos")
            if not dados_geo:
                continue
                
            total_alertas_com_geo += 1
            severidade = alerta.get("severidade", "Perigo Potencial")
            cor_oficial = alerta.get("color_risk", "#808080")
            
            # Adicionar área total
            area_alerta = dados_geo.get("area_total_km2", 0)
            area_total += area_alerta
            
            # Coletar centro e bbox
            centro = dados_geo.get("centro_geografico")
            bbox = dados_geo.get("bounding_box")
            
            if centro:
                todos_centros.append(centro)
            if bbox:
                todos_bboxes.append(bbox)
            
            # Processar polígonos individuais
            poligonos_individuais = dados_geo.get("poligonos_individuais", [])
            
            for i, poli in enumerate(poligonos_individuais):
                poligono_info = {
                    "id": f"{alerta.get('id', 'desconhecido')}_{i}",
                    "alerta_id": alerta.get("id"),
                    "evento": alerta.get("event", ""),
                    "severidade": severidade,
                    "cor": cor_oficial,
                    "coordenadas": poli.get("coordenadas", []),
                    "area_km2": poli.get("area_km2", 0),
                    "centro": poli.get("centro"),
                    "bounding_box": poli.get("bounding_box"),
                    "inicio": alerta.get("onset", ""),
                    "fim": alerta.get("expires", ""),
                    "descricao": alerta.get("description", "")[:100],  # Limitar descrição
                    "municipios": alerta.get("municipios_estado", [])[:5]  # Limitar municípios exibidos
                }
                
                # Adicionar à severidade correspondente
                if severidade in poligonos_por_severidade:
                    poligonos_por_severidade[severidade].append(poligono_info)
        
        # Calcular centro geográfico combinado
        centro_combinado = None
        if todos_centros:
            lat_media = sum(c[0] for c in todos_centros) / len(todos_centros)
            lon_media = sum(c[1] for c in todos_centros) / len(todos_centros)
            centro_combinado = [lat_media, lon_media]
        
        # Calcular bounding box combinado
        bbox_combinado = None
        zoom_recomendado = 8
        if todos_bboxes:
            bbox_combinado = {
                "min_lat": min(b["min_lat"] for b in todos_bboxes),
                "max_lat": max(b["max_lat"] for b in todos_bboxes),
                "min_lon": min(b["min_lon"] for b in todos_bboxes),
                "max_lon": max(b["max_lon"] for b in todos_bboxes)
            }
            
            # Calcular zoom baseado na extensão
            extensao_lat = bbox_combinado["max_lat"] - bbox_combinado["min_lat"]
            extensao_lon = bbox_combinado["max_lon"] - bbox_combinado["min_lon"]
            extensao_max = max(extensao_lat, extensao_lon)
            
            if extensao_max > 5:
                zoom_recomendado = 6
            elif extensao_max > 2:
                zoom_recomendado = 7
            elif extensao_max > 1:
                zoom_recomendado = 8
            elif extensao_max > 0.5:
                zoom_recomendado = 9
            else:
                zoom_recomendado = 10
        
        # Preparar lista completa de polígonos ordenada por prioridade
        todos_poligonos = []
        # Ordem: Grande Perigo (mais alta), Perigo, Perigo Potencial (mais baixa)
        for severidade in ["Grande Perigo", "Perigo", "Perigo Potencial"]:
            todos_poligonos.extend(poligonos_por_severidade[severidade])
        
        # Preparar dados de camadas para sobreposição
        camadas_sobrepostas = {}
        for severidade, poligonos in poligonos_por_severidade.items():
            if poligonos:
                camadas_sobrepostas[severidade] = {
                    "cor": CORES_INMET_MAPA.get(severidade, "#808080"),
                    "total_poligonos": len(poligonos),
                    "area_total_km2": sum(p["area_km2"] for p in poligonos),
                    "poligonos": poligonos
                }

        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            "estado": self._estado,
            "poligonos": todos_poligonos,
            "area_total_afetada_km2": round(area_total, 2),
            "centro_geografico": centro_combinado,
            "bounding_box": bbox_combinado,
            "zoom_recomendado": zoom_recomendado,
            "camadas_por_severidade": camadas_sobrepostas,
            "total_alertas_com_geo": total_alertas_com_geo,
            "ultima_atualizacao": self.coordinator.data.get("last_update"),
        }


class INMETAlertasDiagnosticoSensor(CoordinatorEntity, SensorEntity):
    """Sensor de diagnóstico dos alertas INMET."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:information-outline"

    def __init__(self, coordinator: INMETDataUpdateCoordinator, config_entry: ConfigEntry):
        super().__init__(coordinator)
        self._estado = coordinator.estado
        self._attr_unique_id = f"{DOMAIN}_{self._estado}_diagnostico"
        self._attr_name = f"Diagnóstico INMET {self._estado}"

    @property
    def native_value(self) -> str:
        if not self.coordinator.data:
            return "inativo"
        diagnostico = self.coordinator.data.get("diagnostico", {})
        ultimo_status = diagnostico.get("ultimo_http_status")
        if diagnostico.get("ultimo_erro"):
            return "erro"
        if diagnostico.get("rate_limit_hits", 0) > 0:
            return "rate_limit"
        if ultimo_status == 200:
            return "ok"
        return "desconhecido"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            "estado": self._estado,
        }
        if self.coordinator.data:
            diagnostico = self.coordinator.data.get("diagnostico", {})
            attrs.update({
                "ultimo_http_status": diagnostico.get("ultimo_http_status"),
                "rate_limit_hits": diagnostico.get("rate_limit_hits", 0),
                "pending_caps": diagnostico.get("pending_caps", 0),
                "ultimo_erro": diagnostico.get("ultimo_erro"),
                "total_alertas_api": diagnostico.get("total_alertas_api", 0),
                "ciclo_atual": diagnostico.get("ciclo_atual"),
            })
        return attrs
