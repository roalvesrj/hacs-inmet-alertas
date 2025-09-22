"""Constantes para a integração INMET Alertas."""
from typing import Final

# Informações da integração
DOMAIN: Final = "inmet_alertas"
NAME: Final = "INMET Alertas"
VERSION: Final = "1.7.0"
MANUFACTURER: Final = "Instituto Nacional de Meteorologia"
MODEL: Final = "Sistema de Alertas Meteorológicos"

# URLs e endpoints
URL_RSS: Final = "https://apiprevmet3.inmet.gov.br/avisos/rss"
URL_BASE_ALERTA: Final = "https://apiprevmet3.inmet.gov.br/avisos/rss/"

# Configurações de rede
HTTP_TIMEOUT: Final = 30
MAX_RETRIES: Final = 3
REQUEST_HEADERS: Final = {
    "User-Agent": "Home Assistant INMET Integration/1.6.0",
    "Accept": "application/rss+xml, application/xml, text/xml",
}

# Configurações de atualização
DEFAULT_UPDATE_INTERVAL: Final = 30  # minutos
MIN_UPDATE_INTERVAL: Final = 5       # minutos
MAX_UPDATE_INTERVAL: Final = 120     # minutos

# Mapeamento de severidades CAP para INMET
SEVERIDADE_CAP_MAP: Final = {
    "Minor": "Perigo Potencial",
    "Moderate": "Perigo", 
    "Severe": "Perigo",
    "Extreme": "Grande Perigo"
}

# Cores/ícones por severidade
SEVERIDADE_CORES: Final = {
    "Perigo Potencial": "🟡",
    "Perigo": "🟠",
    "Grande Perigo": "🔴",
}

# Ícones por tipo de evento
EVENTO_ICONES: Final = {
    "Chuva": "🌧️",
    "Vendaval": "💨", 
    "Tempestade": "⛈️",
    "Granizo": "🧊",
    "Neve": "❄️",
    "Geada": "🥶",
    "Onda de Calor": "🌡️",
    "Baixa Umidade": "🏜️",
    "default": "⚠️"
}

# Prioridades de severidade
SEVERIDADE_PRIORIDADES: Final = {
    "Grande Perigo": 3, 
    "Perigo": 2, 
    "Perigo Potencial": 1,
}

# Estados brasileiros
ESTADOS_BRASILEIROS: Final = {
    "AC": "Acre",
    "AL": "Alagoas", 
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins"
}

# Eventos personalizados
EVENT_NOVO_ALERTA: Final = "inmet_novo_alerta"
EVENT_ALERTA_PERIGOSO: Final = "inmet_alerta_perigoso"
EVENT_ALERTA_EXPIRADO: Final = "inmet_alerta_expirado"

# Serviços
SERVICE_ATUALIZAR_ALERTAS: Final = "atualizar_alertas"

# Atributos do sensor
ATTR_TOTAL_ALERTAS: Final = "total_alertas"
ATTR_ALERTAS: Final = "alertas"
ATTR_ALERTAS_POR_SEVERIDADE: Final = "alertas_por_severidade"
ATTR_SEVERIDADE_MAXIMA: Final = "severidade_maxima"
ATTR_MUNICIPIOS_UNICOS: Final = "municipios_unicos"
ATTR_MUNICIPIOS_AFETADOS: Final = "municipios_afetados"
ATTR_ESTADO: Final = "estado"
ATTR_ULTIMA_ATUALIZACAO: Final = "ultima_atualizacao"

# Configurações padrão
DEFAULT_NOTIFICACOES_PERIGO: Final = True
SEVERIDADES_NOTIFICACAO: Final = ["Perigo", "Grande Perigo"]

# Limites e validações
MAX_DESCRIPTION_LENGTH: Final = 200
MAX_MUNICIPIOS_EXIBIDOS: Final = 10