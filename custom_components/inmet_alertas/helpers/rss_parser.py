"""
Módulo para parsing de RSS e dados CAP do INMET.
Centraliza toda a lógica de comunicação com os feeds RSS.
"""
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional, Any
import aiohttp
import feedparser
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import HomeAssistant

from ..const import (
    URL_RSS, URL_BASE_ALERTA, HTTP_TIMEOUT, REQUEST_HEADERS,
    SEVERIDADE_CAP_MAP, EVENTO_ICONES, CORES_INMET_MAPA, COLORISK_TO_SEVERIDADE
)
from .geo_processor import GeoProcessor

_LOGGER = logging.getLogger(__name__)


class RSSParser:
    """Parser para RSS principal e específico do INMET."""
    
    def __init__(self, hass: HomeAssistant):
        """Inicializar parser."""
        self.hass = hass
        self._session = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Obter sessão HTTP."""
        if self._session is None:
            self._session = async_get_clientsession(self.hass)
        return self._session
    
    async def buscar_alertas_principais(self) -> List[Dict[str, Any]]:
        """
        Buscar lista principal de alertas do RSS.
        
        Returns:
            Lista de alertas básicos do RSS principal.
        """
        try:
            session = await self.get_session()
            
            async with session.get(URL_RSS, timeout=HTTP_TIMEOUT, headers=REQUEST_HEADERS) as response:
                if response.status != 200:
                    raise Exception(f"Erro HTTP {response.status} ao acessar RSS principal")
                
                data = await response.text()
                
            if not data.strip():
                raise Exception("Resposta vazia do RSS principal")
            
            # Parse com feedparser (mais robusto para RSS)
            feed = feedparser.parse(data)
            
            if not feed.entries:
                _LOGGER.warning("Nenhuma entrada encontrada no RSS principal")
                return []
            
            alertas = []
            for entry in feed.entries:
                try:
                    alerta = self._extrair_dados_entrada(entry)
                    if alerta:
                        alertas.append(alerta)
                except Exception as e:
                    _LOGGER.warning(f"Erro ao processar entrada do RSS: {e}")
                    continue
            
            _LOGGER.info(f"Encontrados {len(alertas)} alertas no RSS principal")
            return alertas
            
        except Exception as e:
            _LOGGER.error(f"Erro ao buscar alertas principais: {e}")
            raise
    
    def _extrair_dados_entrada(self, entry) -> Optional[Dict[str, Any]]:
        """Extrair dados básicos de uma entrada do RSS."""
        try:
            # Extrair ID do link
            link = entry.get('link', '')
            alert_id = link.split('/')[-1] if link else None
            
            if not alert_id:
                return None
            
            return {
                'id': alert_id,
                'titulo': entry.get('title', 'Sem título'),
                'link': link,
                'publicado': entry.get('published', ''),
                'descricao_breve': entry.get('summary', ''),
            }
            
        except Exception as e:
            _LOGGER.error(f"Erro ao extrair dados da entrada: {e}")
            return None
    
    async def buscar_detalhes_alerta(self, link: str) -> Optional[Dict[str, Any]]:
        """
        Buscar detalhes específicos de um alerta via CAP.
        
        Args:
            link: URL do alerta específico
            
        Returns:
            Dados detalhados do alerta em formato CAP ou None se erro.
        """
        try:
            session = await self.get_session()
            
            async with session.get(link, timeout=HTTP_TIMEOUT, headers=REQUEST_HEADERS) as response:
                if response.status != 200:
                    _LOGGER.warning(f"Erro HTTP {response.status} ao acessar {link}")
                    return None
                
                data = await response.text()
            
            if not data.strip():
                _LOGGER.warning(f"Resposta vazia para {link}")
                return None
            
            # Parse do XML CAP
            try:
                root = ET.fromstring(data)
            except ET.ParseError as e:
                _LOGGER.error(f"Erro ao analisar XML de {link}: {e}")
                return None
            
            return self._extrair_dados_cap(root)
            
        except Exception as e:
            _LOGGER.error(f"Erro ao buscar detalhes do alerta {link}: {e}")
            return None
    
    def _extrair_dados_cap(self, root: ET.Element) -> Dict[str, Any]:
        """Extrair dados do formato CAP."""
        cap_data = {}
        
        # Namespace CAP
        ns = {'cap': 'urn:oasis:names:tc:emergency:cap:1.2'}
        
        try:
            # Buscar elemento info
            info = root.find('.//cap:info', ns)
            if info is None:
                # Tentar sem namespace
                info = root.find('.//info')
            
            if info is not None:
                # Dados básicos
                cap_data['event'] = self._get_text_safe(info, 'event', ns)
                cap_data['severity'] = self._get_text_safe(info, 'severity', ns)
                cap_data['certainty'] = self._get_text_safe(info, 'certainty', ns)
                cap_data['urgency'] = self._get_text_safe(info, 'urgency', ns)
                cap_data['description'] = self._get_text_safe(info, 'description', ns)
                cap_data['instruction'] = self._get_text_safe(info, 'instruction', ns)
                cap_data['onset'] = self._get_text_safe(info, 'onset', ns)
                cap_data['expires'] = self._get_text_safe(info, 'expires', ns)
                
                # Mapear severidade CAP para INMET
                severidade_cap = cap_data.get('severity', '')
                cap_data['severidade_inmet'] = SEVERIDADE_CAP_MAP.get(severidade_cap, severidade_cap)
                
                # Extrair parâmetros específicos
                parametros = info.findall('.//cap:parameter', ns) or info.findall('.//parameter')
                for param in parametros:
                    name_elem = param.find('cap:valueName', ns) or param.find('valueName')
                    value_elem = param.find('cap:value', ns) or param.find('value')
                    
                    if name_elem is not None and value_elem is not None:
                        param_name = name_elem.text
                        param_value = value_elem.text
                        
                        if param_name == 'Municipios':
                            cap_data['municipios'] = param_value
                        elif param_name == 'colorRisk':
                            cap_data['color_risk'] = param_value
                        elif param_name == 'web':
                            cap_data['web'] = param_value
                
                # Extrair áreas afetadas
                areas = info.findall('.//cap:area', ns) or info.findall('.//area')
                areas_desc = []
                poligonos = []
                
                for area in areas:
                    desc_elem = area.find('cap:areaDesc', ns) or area.find('areaDesc')
                    if desc_elem is not None and desc_elem.text:
                        areas_desc.append(desc_elem.text)
                    
                    # Buscar polígonos - tentar diferentes variações
                    polygon_elem = (area.find('cap:polygon', ns) or 
                                  area.find('polygon') or 
                                  area.find('.//polygon'))
                    
                    if polygon_elem is not None and polygon_elem.text:
                        polygon_text = polygon_elem.text.strip()
                        if polygon_text:
                            poligonos.append(polygon_text)
                            _LOGGER.debug(f"Polígono extraído: {polygon_text[:100]}...")
                
                cap_data['areas'] = areas_desc
                cap_data['area_desc'] = '; '.join(areas_desc)
                cap_data['polygons'] = poligonos
                
                # Processar dados geográficos se existirem polígonos
                if poligonos:
                    _LOGGER.info(f"Processando {len(poligonos)} polígonos encontrados")
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
                    else:
                        _LOGGER.warning(f"Nenhum polígono válido foi processado dos {len(poligonos)} encontrados")
                else:
                    _LOGGER.debug("Nenhum polígono encontrado no CAP")
                
                # Processar cor do risco se disponível
                cor_risco = cap_data.get('color_risk', '')
                if cor_risco:
                    # Mapear cor para severidade se possível
                    if cor_risco in COLORISK_TO_SEVERIDADE:
                        cap_data['severidade_por_cor'] = COLORISK_TO_SEVERIDADE[cor_risco]
                    
                    # Garantir que a cor está no formato correto
                    if not cor_risco.startswith('#'):
                        cor_risco = f"#{cor_risco}"
                    cap_data['color_risk'] = cor_risco
                
                # Se não temos cor específica, usar cor padrão da severidade
                if not cap_data.get('color_risk'):
                    severidade = cap_data.get('severidade_inmet', '')
                    cap_data['color_risk'] = CORES_INMET_MAPA.get(severidade, '#808080')
                
                # Adicionar ícone baseado no evento
                evento = cap_data.get('event', '')
                cap_data['icone'] = self._get_icone_evento(evento)
                
        except Exception as e:
            _LOGGER.error(f"Erro ao extrair dados CAP: {e}")
        
        return cap_data
    
    def _get_text_safe(self, parent: ET.Element, tag: str, ns: dict) -> str:
        """Extrair texto de um elemento de forma segura."""
        try:
            # Tentar com namespace
            elem = parent.find(f'cap:{tag}', ns)
            if elem is None:
                # Tentar sem namespace
                elem = parent.find(tag)
            
            return elem.text if elem is not None and elem.text else ''
        except:
            return ''
    
    def _get_icone_evento(self, evento: str) -> str:
        """Obter ícone para o tipo de evento."""
        evento_lower = evento.lower()
        
        for tipo, icone in EVENTO_ICONES.items():
            if tipo.lower() in evento_lower:
                return icone
        
        return EVENTO_ICONES['default']