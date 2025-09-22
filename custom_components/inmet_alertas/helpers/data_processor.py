"""
Módulo para processamento e validação de dados de alertas.
Centraliza toda a lógica de negócio para validação e formatação.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..const import (
    SEVERIDADE_PRIORIDADES, SEVERIDADE_CORES, MAX_DESCRIPTION_LENGTH,
    MAX_MUNICIPIOS_EXIBIDOS, ESTADOS_BRASILEIROS
)
from ..utils import is_alert_active, check_state_affected, filter_state_municipalities

_LOGGER = logging.getLogger(__name__)


class DataProcessor:
    """Processador de dados de alertas meteorológicos."""
    
    def __init__(self, estado: str):
        """Inicializar processador."""
        self.estado = estado.upper()
        
    def processar_alerta(self, alerta_basico: Dict[str, Any], cap_data: Dict[str, Any], 
                        agora: datetime) -> Optional[Dict[str, Any]]:
        """
        Processar e validar um alerta completo.
        
        Args:
            alerta_basico: Dados básicos do RSS
            cap_data: Dados detalhados do CAP
            agora: Timestamp atual
            
        Returns:
            Alerta processado e validado ou None se inválido.
        """
        try:
            # Verificar se o alerta afeta o estado
            if not self._afeta_estado(cap_data):
                return None
            
            # Verificar se está ativo
            if not is_alert_active(cap_data, agora):
                return None
            
            # Processar municípios do estado
            municipios_estado = self._processar_municipios(cap_data)
            
            # Extrair e formatar dados
            alerta_processado = {
                'id': alerta_basico['id'],
                'titulo': self._formatar_titulo(alerta_basico.get('titulo', '')),
                'evento': cap_data.get('event', 'Desconhecido'),
                'severidade': cap_data.get('severidade_inmet', 'Desconhecida'),
                'severidade_cap': cap_data.get('severity', ''),
                'icone': cap_data.get('icone', '⚠️'),
                'inicio': self._formatar_data(cap_data.get('onset', '')),
                'fim': self._formatar_data(cap_data.get('expires', '')),
                'descricao': self._formatar_descricao(cap_data.get('description', '')),
                'instrucoes': cap_data.get('instruction', ''),
                'municipios_estado': municipios_estado,
                'total_municipios_estado': len(municipios_estado),
                'link': alerta_basico['link'],
                'ativo': True,
                'publicado': alerta_basico.get('publicado', ''),
                'area_desc': cap_data.get('area_desc', ''),
                'cor_oficial': cap_data.get('color_risk', ''),
                'url_grafica': cap_data.get('web', ''),
            }
            
            return alerta_processado
            
        except Exception as e:
            _LOGGER.error(f"Erro ao processar alerta {alerta_basico.get('id', 'desconhecido')}: {e}")
            return None
    
    def _afeta_estado(self, cap_data: Dict[str, Any]) -> bool:
        """Verificar se o alerta afeta o estado configurado."""
        return check_state_affected(cap_data, self.estado)
    
    def _processar_municipios(self, cap_data: Dict[str, Any]) -> List[str]:
        """Processar lista de municípios afetados no estado."""
        municipios_text = cap_data.get('municipios', '')
        return filter_state_municipalities(municipios_text, self.estado)
    
    def _formatar_titulo(self, titulo: str) -> str:
        """Formatar título do alerta."""
        if not titulo or titulo == 'Sem título':
            return 'Alerta Meteorológico'
        
        # Limpar título
        titulo = titulo.strip()
        
        # Remover prefixos comuns
        prefixos_remover = ['Aviso Meteorológico:', 'Alerta:', 'INMET:']
        for prefixo in prefixos_remover:
            if titulo.startswith(prefixo):
                titulo = titulo[len(prefixo):].strip()
        
        return titulo or 'Alerta Meteorológico'
    
    def _formatar_data(self, data_iso: str) -> str:
        """Formatar data ISO para formato brasileiro."""
        if not data_iso:
            return ''
        
        try:
            # Parse da data ISO
            if 'Z' in data_iso:
                dt = datetime.fromisoformat(data_iso.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(data_iso)
            
            # Converter para horário local (simplificado)
            return dt.strftime('%d/%m/%Y %H:%M')
            
        except Exception as e:
            _LOGGER.warning(f"Erro ao formatar data {data_iso}: {e}")
            return data_iso
    
    def _formatar_descricao(self, descricao: str) -> str:
        """Formatar descrição do alerta."""
        if not descricao:
            return ''
        
        # Limitar tamanho
        if len(descricao) > MAX_DESCRIPTION_LENGTH:
            descricao = descricao[:MAX_DESCRIPTION_LENGTH] + '...'
        
        return descricao.strip()
    
    def calcular_resumo(self, alertas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calcular resumo estatístico dos alertas.
        
        Args:
            alertas: Lista de alertas processados
            
        Returns:
            Dicionário com estatísticas resumidas.
        """
        if not alertas:
            return {
                "count": 0,
                "severidade_maxima": None,
                "alertas_por_severidade": {},
                "municipios_unicos": 0,
                "municipios_afetados": [],
            }
        
        # Contadores
        severidades = {}
        municipios_unicos = set()
        severidade_maxima = None
        max_prioridade = 0
        
        for alerta in alertas:
            # Contar severidades
            sev = alerta.get("severidade", "Desconhecida")
            severidades[sev] = severidades.get(sev, 0) + 1
            
            # Verificar severidade máxima
            prioridade = SEVERIDADE_PRIORIDADES.get(sev, 0)
            if prioridade > max_prioridade:
                max_prioridade = prioridade
                severidade_maxima = sev
            
            # Coletar municípios únicos
            for municipio in alerta.get("municipios_estado", []):
                municipios_unicos.add(municipio)
        
        return {
            "count": len(alertas),
            "severidade_maxima": severidade_maxima,
            "alertas_por_severidade": severidades,
            "municipios_unicos": len(municipios_unicos),
            "municipios_afetados": list(municipios_unicos)[:MAX_MUNICIPIOS_EXIBIDOS],
        }
    
    def validar_configuracao(self) -> bool:
        """Validar se a configuração do estado é válida."""
        return self.estado in ESTADOS_BRASILEIROS
    
    def obter_nome_estado(self) -> str:
        """Obter nome completo do estado."""
        return ESTADOS_BRASILEIROS.get(self.estado, self.estado)