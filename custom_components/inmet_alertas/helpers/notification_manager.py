"""
Módulo para gerenciamento de notificações persistentes.
Centraliza toda a lógica de criação, atualização e remoção de notificações.
"""
import logging
from typing import Dict, List, Set, Any
from homeassistant.core import HomeAssistant

from ..const import (
    SEVERIDADES_NOTIFICACAO, MAX_DESCRIPTION_LENGTH,
    EVENT_NOVO_ALERTA, EVENT_ALERTA_PERIGOSO
)

_LOGGER = logging.getLogger(__name__)


class NotificationManager:
    """Gerenciador de notificações persistentes e eventos."""
    
    def __init__(self, hass: HomeAssistant, estado: str, notificacoes_ativas: bool = True):
        """Inicializar gerenciador."""
        self.hass = hass
        self.estado = estado.upper()
        self.notificacoes_ativas = notificacoes_ativas
        self._alertas_notificados: Set[str] = set()
    
    async def processar_novos_alertas(self, alertas_atuais: List[Dict[str, Any]], 
                                    alertas_anteriores: Set[str]) -> None:
        """
        Processar alertas novos e disparar notificações/eventos.
        
        Args:
            alertas_atuais: Lista de alertas atualmente ativos
            alertas_anteriores: Set de IDs de alertas anteriores
        """
        alertas_atuais_ids = {alerta['id'] for alerta in alertas_atuais}
        novos_alertas_ids = alertas_atuais_ids - alertas_anteriores
        
        if not novos_alertas_ids:
            return
        
        # Processar cada novo alerta
        for alerta in alertas_atuais:
            if alerta['id'] in novos_alertas_ids:
                await self._processar_novo_alerta(alerta)
    
    async def _processar_novo_alerta(self, alerta: Dict[str, Any]) -> None:
        """Processar um novo alerta detectado."""
        try:
            # Disparar evento geral
            await self._disparar_evento_novo_alerta(alerta)
            
            # Disparar evento específico para alertas perigosos
            if alerta["severidade"] in SEVERIDADES_NOTIFICACAO:
                await self._disparar_evento_perigoso(alerta)
                
                # Criar notificação persistente se configurado
                if self.notificacoes_ativas:
                    await self._criar_notificacao_persistente(alerta)
            
            # Registrar alerta como notificado
            self._alertas_notificados.add(alerta['id'])
            
            _LOGGER.info(f"Novo alerta processado: {alerta['titulo']} ({alerta['id']})")
            
        except Exception as e:
            _LOGGER.error(f"Erro ao processar novo alerta {alerta.get('id', 'desconhecido')}: {e}")
    
    async def _disparar_evento_novo_alerta(self, alerta: Dict[str, Any]) -> None:
        """Disparar evento geral de novo alerta."""
        self.hass.bus.async_fire(
            EVENT_NOVO_ALERTA,
            {
                "alert_id": alerta["id"],
                "titulo": alerta["titulo"],
                "severidade": alerta["severidade"],
                "evento": alerta["evento"],
                "estado": self.estado,
                "inicio": alerta["inicio"],
                "fim": alerta["fim"],
                "municipios": alerta.get("total_municipios_estado", 0),
                "area_desc": alerta.get("area_desc", ""),
                "ativo": alerta["ativo"],
            }
        )
    
    async def _disparar_evento_perigoso(self, alerta: Dict[str, Any]) -> None:
        """Disparar evento específico para alertas perigosos."""
        self.hass.bus.async_fire(
            EVENT_ALERTA_PERIGOSO,
            {
                "alert_id": alerta["id"],
                "titulo": alerta["titulo"],
                "severidade": alerta["severidade"],
                "evento": alerta["evento"],
                "estado": self.estado,
                "inicio": alerta["inicio"],
                "fim": alerta["fim"],
                "municipios": alerta.get("total_municipios_estado", 0),
                "area_desc": alerta.get("area_desc", ""),
            }
        )
    
    async def _criar_notificacao_persistente(self, alerta: Dict[str, Any]) -> None:
        """Criar notificação persistente para alerta perigoso."""
        try:
            notification_id = f"inmet_alert_{self.estado}_{alerta['id']}"
            
            # Formatar mensagem
            mensagem = self._formatar_mensagem_notificacao(alerta)
            
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": f"🚨 Alerta Meteorológico - {alerta['severidade']} ({self.estado})",
                    "message": mensagem,
                    "notification_id": notification_id,
                },
            )
            
            _LOGGER.debug(f"Notificação criada: {notification_id}")
            
        except Exception as e:
            _LOGGER.error(f"Erro ao criar notificação para alerta {alerta['id']}: {e}")
    
    def _formatar_mensagem_notificacao(self, alerta: Dict[str, Any]) -> str:
        """Formatar mensagem da notificação."""
        descricao = alerta.get('descricao', '')
        if len(descricao) > MAX_DESCRIPTION_LENGTH:
            descricao = descricao[:MAX_DESCRIPTION_LENGTH] + '...'
        
        mensagem = f"**{alerta['titulo']}**\n\n"
        mensagem += f"Evento: {alerta['evento']}\n"
        mensagem += f"Estado: {self.estado}\n"
        mensagem += f"Início: {alerta['inicio']}\n"
        mensagem += f"Fim: {alerta['fim']}\n"
        mensagem += f"Municípios afetados: {alerta.get('total_municipios_estado', 0)}\n\n"
        
        if descricao:
            mensagem += descricao
        
        return mensagem
    
    async def limpar_notificacoes_expiradas(self, alertas_atuais: List[Dict[str, Any]], 
                                          alertas_anteriores: Set[str]) -> None:
        """
        Limpar notificações de alertas que não estão mais ativos.
        
        Args:
            alertas_atuais: Lista de alertas atualmente ativos
            alertas_anteriores: Set de IDs de alertas anteriores
        """
        if not alertas_anteriores:
            return
        
        try:
            # IDs dos alertas atualmente ativos
            alertas_atuais_ids = {alerta['id'] for alerta in alertas_atuais}
            
            # IDs que eram ativos mas não estão mais
            alertas_expirados = alertas_anteriores - alertas_atuais_ids
            
            # Remover notificações dos alertas expirados
            for alert_id in alertas_expirados:
                await self._remover_notificacao(alert_id)
                
                # Remover da lista de notificados
                self._alertas_notificados.discard(alert_id)
                
        except Exception as e:
            _LOGGER.error(f"Erro na limpeza de notificações: {e}")
    
    async def _remover_notificacao(self, alert_id: str) -> None:
        """Remover notificação específica."""
        try:
            notification_id = f"inmet_alert_{self.estado}_{alert_id}"
            
            await self.hass.services.async_call(
                "persistent_notification",
                "dismiss",
                {"notification_id": notification_id},
            )
            
            _LOGGER.debug(f"Notificação removida: {notification_id}")
            
        except Exception as e:
            _LOGGER.warning(f"Erro ao remover notificação {alert_id}: {e}")
    
    def configurar_notificacoes(self, ativas: bool) -> None:
        """Configurar se as notificações estão ativas."""
        self.notificacoes_ativas = ativas
        _LOGGER.debug(f"Notificações configuradas: {'ativas' if ativas else 'inativas'}")
    
    def obter_alertas_notificados(self) -> Set[str]:
        """Obter conjunto de alertas já notificados."""
        return self._alertas_notificados.copy()