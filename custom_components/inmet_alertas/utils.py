"""Utilitários para a integração INMET Alertas."""
from datetime import datetime
from typing import Dict, List, Any
import logging

_LOGGER = logging.getLogger(__name__)

# Mapeamento de severidades CAP para INMET
SEVERIDADE_CAP_MAP = {
    "Minor": "Perigo Potencial",
    "Moderate": "Perigo", 
    "Severe": "Perigo",
    "Extreme": "Grande Perigo"
}

# Cores/ícones por severidade
SEVERIDADE_CORES = {
    "Perigo Potencial": "🟡",
    "Perigo": "🟠",
    "Grande Perigo": "🔴",
    "Desconhecida": "ℹ️"
}


def format_datetime(iso_datetime: str) -> str:
    """Formatar datetime ISO para formato brasileiro."""
    if not iso_datetime:
        return ""
    
    try:
        # Parse ISO datetime
        dt = datetime.fromisoformat(iso_datetime.replace('Z', '+00:00'))
        # Formato brasileiro
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso_datetime


def is_alert_active(cap_data: Dict[str, Any], now: datetime) -> bool:
    """Verificar se o alerta está ativo no momento atual."""
    inicio_iso = cap_data.get('onset', '')
    fim_iso = cap_data.get('expires', '')
    
    if not inicio_iso or not fim_iso:
        return True  # Assume ativo se não há data
    
    try:
        inicio = datetime.fromisoformat(inicio_iso.replace('Z', '+00:00')).replace(tzinfo=None)
        fim = datetime.fromisoformat(fim_iso.replace('Z', '+00:00')).replace(tzinfo=None)
        now_naive = now.replace(tzinfo=None)
        
        return inicio <= now_naive <= fim
    except Exception as e:
        _LOGGER.warning(f"Erro ao verificar período do alerta: {e}")
        return True  # Assume ativo em caso de erro


def check_state_affected(cap_data: Dict[str, Any], estado: str) -> bool:
    """Verificar se o alerta afeta o estado especificado."""
    if not estado:
        return True
        
    municipios = cap_data.get('municipios', '')
    if not municipios:
        return False
    
    # Buscar padrão " - UF " nos municípios
    estado_tag = f" - {estado} "
    return estado_tag in municipios


def filter_state_municipalities(municipios_text: str, estado: str) -> List[str]:
    """Filtrar apenas os municípios do estado especificado."""
    if not municipios_text:
        return []
    
    municipios = municipios_text.split(", ")
    estado_tag = f" - {estado} "
    
    return [m.strip() for m in municipios if estado_tag in m]


def get_severidade_prioridade(severidade: str) -> int:
    """Obter prioridade numérica da severidade."""
    prioridades = {
        "Grande Perigo": 3, 
        "Perigo": 2, 
        "Perigo Potencial": 1,
        "Desconhecida": 0
    }
    return prioridades.get(severidade, 0)


def calculate_summary(alerts: List[Dict[str, Any]], estado: str) -> Dict[str, Any]:
    """Calcular resumo dos alertas ativos."""
    if not alerts:
        return {
            "total_alertas": 0,
            "alertas_ativos": 0,
            "severidade_maxima": None,
            "municipios_unicos": 0,
            "estado": estado,
        }
    
    # Todos os alertas passados são ativos
    severidade_maxima = None
    max_prioridade = 0
    municipios_set = set()
    
    for alert in alerts:
        # Verificar severidade máxima
        sev = alert.get('severidade', '')
        prioridade = get_severidade_prioridade(sev)
        if prioridade > max_prioridade:
            max_prioridade = prioridade
            severidade_maxima = sev
        
        # Coletar municípios únicos
        for municipio in alert.get('municipios_estado', []):
            municipios_set.add(municipio)
    
    return {
        "total_alertas": len(alerts),
        "alertas_ativos": len(alerts),
        "severidade_maxima": severidade_maxima,
        "municipios_unicos": len(municipios_set),
        "estado": estado,
    }