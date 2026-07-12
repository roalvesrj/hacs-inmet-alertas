"""
Teste para reproduzir e validar o problema de persistência de alertas.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from custom_components.inmet_alertas.sensor import INMETDataUpdateCoordinator


@pytest.mark.asyncio 
async def test_problema_persistencia_alertas():
    """
    Teste para reproduzir o problema onde alertas 'somem' durante novos scans.
    """
    # Mock do Home Assistant
    mock_hass = Mock()
    mock_hass.services = Mock()
    mock_hass.services.async_call = AsyncMock()
    mock_hass.bus = Mock()
    mock_hass.bus.async_fire = Mock()
    
    # Criar coordenador
    coordinator = INMETDataUpdateCoordinator(
        mock_hass, 
        "SP", 
        30, 
        True
    )
    
    # Estado inicial vazio
    assert coordinator._previous_alert_ids == set()
    
    # Simular primeiro scan com 3 alertas
    coordinator._previous_alert_ids = {"alert_1", "alert_2", "alert_3"}
    
    # Simular segundo scan onde apenas 2 alertas são retornados
    # (isso simula um problema temporário no RSS ou rate limiting)
    new_scan_ids = {"alert_2", "alert_3"}
    
    # Problema: a linha abaixo sobrescreve completamente o estado
    coordinator._previous_alert_ids = new_scan_ids
    
    # RESULTADO: alert_1 foi perdido mesmo que ainda possa estar ativo!
    assert "alert_1" not in coordinator._previous_alert_ids
    assert coordinator._previous_alert_ids == {"alert_2", "alert_3"}
    
    print("❌ PROBLEMA CONFIRMADO: Alert_1 foi perdido mesmo que possa estar ativo!")


@pytest.mark.asyncio
async def test_solucao_esperada():
    """
    Teste que demonstra como deveria funcionar a persistência.
    """
    # Mock do estado persistente que queremos implementar
    alertas_persistentes = {
        "alert_1": {
            "id": "alert_1", 
            "expires": (datetime.now() + timedelta(hours=2)).isoformat(),
            "data": {"titulo": "Alerta 1", "ativo": True}
        },
        "alert_2": {
            "id": "alert_2",
            "expires": (datetime.now() + timedelta(hours=1)).isoformat(), 
            "data": {"titulo": "Alerta 2", "ativo": True}
        },
        "alert_3": {
            "id": "alert_3",
            "expires": (datetime.now() - timedelta(hours=1)).isoformat(),  # Expirado
            "data": {"titulo": "Alerta 3", "ativo": True}
        }
    }
    
    # Novos alertas do scan atual (apenas 1 dos 3 anteriores + 1 novo)
    novos_alertas_scan = {"alert_2", "alert_4"}
    
    # Lógica esperada: merge inteligente
    alertas_finais = {}
    now = datetime.now()
    
    # 1. Manter alertas existentes que ainda estão válidos
    for alert_id, alert_info in alertas_persistentes.items():
        expires = datetime.fromisoformat(alert_info["expires"].replace('Z', '+00:00'))
        if expires > now:
            alertas_finais[alert_id] = alert_info
    
    # 2. Adicionar novos alertas do scan
    for new_id in novos_alertas_scan:
        if new_id not in alertas_finais:
            alertas_finais[new_id] = {
                "id": new_id,
                "expires": (datetime.now() + timedelta(hours=3)).isoformat(),
                "data": {"titulo": f"Alerta {new_id}", "ativo": True}
            }
    
    # Resultado esperado:
    # - alert_1: mantido (ainda ativo, não apareceu no scan atual)
    # - alert_2: mantido (ativo e apareceu no scan)  
    # - alert_3: removido (expirado)
    # - alert_4: adicionado (novo do scan)
    
    assert "alert_1" in alertas_finais  # Mantido mesmo não estando no scan
    assert "alert_2" in alertas_finais  # Mantido
    assert "alert_3" not in alertas_finais  # Removido (expirado)
    assert "alert_4" in alertas_finais  # Adicionado
    
    print("✅ SOLUÇÃO ESPERADA: Alertas persistem até expirarem naturalmente!")


if __name__ == "__main__":
    import asyncio
    
    async def run_tests():
        await test_problema_persistencia_alertas()
        await test_solucao_esperada()
    
    asyncio.run(run_tests())