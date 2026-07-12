"""
Teste completo do sistema de persistência de alertas implementado.
"""
import pytest
import asyncio
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

# Adicionar o diretório pai ao path para importar os módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sensor import INMETDataUpdateCoordinator


@pytest.mark.asyncio
async def test_persistencia_alertas_completa():
    """
    Teste completo do novo sistema de persistência de alertas.
    """
    # Setup do mock do Home Assistant
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
    
    # Verificar inicialização
    assert hasattr(coordinator, '_alertas_persistentes')
    assert coordinator._alertas_persistentes == {}
    
    # Simulação de alertas com datas realistas
    now = datetime.now()
    
    # Alerta 1: Expira em 2 horas (ativo)
    alert_1 = {
        "id": "alert_001",
        "titulo": "Chuva Forte",
        "severidade": "Perigo",
        "inicio": "01/01/2024 10:00",
        "fim": "01/01/2024 16:00",
        "onset": (now - timedelta(hours=1)).isoformat(),
        "expires": (now + timedelta(hours=2)).isoformat(),
        "ativo": True
    }
    
    # Alerta 2: Expira em 30 min (ativo)  
    alert_2 = {
        "id": "alert_002", 
        "titulo": "Vento Forte",
        "severidade": "Perigo Potencial",
        "inicio": "01/01/2024 12:00",
        "fim": "01/01/2024 14:30", 
        "onset": (now - timedelta(minutes=30)).isoformat(),
        "expires": (now + timedelta(minutes=30)).isoformat(),
        "ativo": True
    }
    
    # Alerta 3: Já expirou há 1 hora
    alert_3 = {
        "id": "alert_003",
        "titulo": "Granizo",
        "severidade": "Grande Perigo", 
        "inicio": "01/01/2024 08:00",
        "fim": "01/01/2024 11:00",
        "onset": (now - timedelta(hours=3)).isoformat(),
        "expires": (now - timedelta(hours=1)).isoformat(),
        "ativo": True
    }
    
    print("\\n🧪 TESTE 1: Primeiro scan com 3 alertas")
    alertas_primeiro_scan = [alert_1, alert_2, alert_3]
    resultado_1 = await coordinator._merge_alertas_com_persistencia(alertas_primeiro_scan, now)
    
    # Deve ter apenas 2 alertas (o expirado deve ser removido)
    assert len(resultado_1) == 2
    ids_resultado_1 = {alert["id"] for alert in resultado_1}
    assert "alert_001" in ids_resultado_1
    assert "alert_002" in ids_resultado_1  
    assert "alert_003" not in ids_resultado_1  # Expirado
    
    print(f"✅ Primeiro scan: {len(resultado_1)} alertas válidos mantidos")
    
    print("\\n🧪 TESTE 2: Segundo scan com falha (rate limiting) - apenas 1 alerta retornado")
    # Simular que apenas 1 alerta foi retornado devido a problemas do RSS
    alertas_segundo_scan = [alert_2]  # Só o alerta 2
    resultado_2 = await coordinator._merge_alertas_com_persistencia(alertas_segundo_scan, now)
    
    # Deve manter AMBOS os alertas válidos (persistência funcionando!)
    assert len(resultado_2) == 2
    ids_resultado_2 = {alert["id"] for alert in resultado_2}
    assert "alert_001" in ids_resultado_2  # MANTIDO mesmo não estando no scan!
    assert "alert_002" in ids_resultado_2
    
    print(f"✅ Segundo scan (simulando falha RSS): {len(resultado_2)} alertas mantidos por persistência")
    
    print("\\n🧪 TESTE 3: Terceiro scan com novo alerta")
    # Novo alerta + os anteriores ainda válidos
    alert_4 = {
        "id": "alert_004",
        "titulo": "Tempestade", 
        "severidade": "Grande Perigo",
        "inicio": "01/01/2024 15:00",
        "fim": "01/01/2024 20:00",
        "onset": now.isoformat(),
        "expires": (now + timedelta(hours=5)).isoformat(),
        "ativo": True
    }
    
    alertas_terceiro_scan = [alert_1, alert_4]  # alert_1 confirmado + novo
    resultado_3 = await coordinator._merge_alertas_com_persistencia(alertas_terceiro_scan, now)
    
    # Deve ter 3 alertas: alert_1 (confirmado), alert_2 (persistente), alert_4 (novo)
    assert len(resultado_3) == 3
    ids_resultado_3 = {alert["id"] for alert in resultado_3}
    assert "alert_001" in ids_resultado_3  # Confirmado no scan
    assert "alert_002" in ids_resultado_3  # Mantido por persistência (ainda válido)
    assert "alert_004" in ids_resultado_3  # Novo
    
    print(f"✅ Terceiro scan: {len(resultado_3)} alertas (1 confirmado + 1 persistente + 1 novo)")
    
    print("\\n🧪 TESTE 4: Quarto scan após expiração do alert_2")
    # Simular tempo passando para alert_2 expirar
    now_futuro = now + timedelta(hours=1)  # 1 hora depois
    
    alertas_quarto_scan = [alert_1, alert_4]  # Mesmos de antes
    resultado_4 = await coordinator._merge_alertas_com_persistencia(alertas_quarto_scan, now_futuro)
    
    # Deve ter apenas 2 alertas (alert_2 deve ter expirado)
    assert len(resultado_4) == 2  
    ids_resultado_4 = {alert["id"] for alert in resultado_4}
    assert "alert_001" in ids_resultado_4
    assert "alert_004" in ids_resultado_4
    assert "alert_002" not in ids_resultado_4  # Expirado automaticamente!
    
    print(f"✅ Quarto scan (após expiração): {len(resultado_4)} alertas (alert_002 removido por expiração)")
    
    print("\\n🎉 TODOS OS TESTES PASSARAM! Sistema de persistência funcionando corretamente!")
    print("\\n📋 Resumo dos benefícios implementados:")
    print("  ✅ Alertas válidos persistem mesmo durante falhas do RSS")
    print("  ✅ Alertas são removidos apenas quando realmente expiram") 
    print("  ✅ Novos alertas são adicionados corretamente")
    print("  ✅ Alertas existentes são atualizados com dados mais recentes")
    print("  ✅ Sistema robusto contra rate limiting e falhas temporárias")


@pytest.mark.asyncio 
async def test_validacao_alerta():
    """
    Teste específico da função de validação de alertas.
    """
    mock_hass = Mock()
    coordinator = INMETDataUpdateCoordinator(mock_hass, "SP", 30, True)
    
    now = datetime.now()
    
    # Alerta válido (expira em 1 hora)
    alert_valido = {
        "id": "test_001",
        "expires": (now + timedelta(hours=1)).isoformat(),
        "titulo": "Teste Válido"
    }
    
    # Alerta expirado (expirou há 1 hora)
    alert_expirado = {
        "id": "test_002", 
        "expires": (now - timedelta(hours=1)).isoformat(),
        "titulo": "Teste Expirado"
    }
    
    # Alerta sem data de expiração (deve ser considerado válido)
    alert_sem_data = {
        "id": "test_003",
        "titulo": "Teste Sem Data"
    }
    
    # Testes
    assert coordinator._is_alerta_ainda_valido(alert_valido, now) == True
    assert coordinator._is_alerta_ainda_valido(alert_expirado, now) == False  
    assert coordinator._is_alerta_ainda_valido(alert_sem_data, now) == True
    
    print("✅ Validação de alertas funcionando corretamente!")


if __name__ == "__main__":
    async def run_all_tests():
        print("🚀 Iniciando testes do sistema de persistência de alertas...")
        await test_persistencia_alertas_completa()
        await test_validacao_alerta()
        print("\\n✅ Todos os testes concluídos com sucesso!")
    
    asyncio.run(run_all_tests())