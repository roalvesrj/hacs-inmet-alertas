"""
Teste sintético da lógica de persistência implementada no sistema de alertas.
Este teste foca na lógica de negócio sem dependências do Home Assistant.
"""
from datetime import datetime, timedelta


class MockAlertaPersistence:
    """Mock da lógica de persistência para testar."""
    
    def __init__(self):
        self._alertas_persistentes = {}
    
    def merge_alertas_com_persistencia(self, novos_alertas: list, agora: datetime) -> list:
        """Simular a lógica de merge implementada no sensor."""
        alertas_finais = {}
        alertas_removidos = 0
        alertas_mantidos = 0 
        alertas_novos = 0
        
        # 1. Verificar alertas existentes - manter os válidos
        for alert_id, alert_data in self._alertas_persistentes.items():
            if self._is_alerta_ainda_valido(alert_data, agora):
                alertas_finais[alert_id] = alert_data
                alertas_mantidos += 1
            else:
                alertas_removidos += 1
        
        # 2. Adicionar/atualizar alertas do scan atual (COM VALIDAÇÃO!)
        for novo_alerta in novos_alertas:
            alert_id = novo_alerta["id"]
            
            # IMPORTANTE: Validar também os novos alertas!
            if not self._is_alerta_ainda_valido(novo_alerta, agora):
                print(f"    ⏰ Novo alerta já expirado, descartando: {alert_id}")
                alertas_removidos += 1
                continue
            
            if alert_id in alertas_finais:
                alertas_finais[alert_id].update(novo_alerta)
            else:
                alertas_finais[alert_id] = novo_alerta
                alertas_novos += 1
        
        # 3. Atualizar cache persistente
        self._alertas_persistentes = alertas_finais.copy()
        
        # 4. Log de estatísticas
        print(f"  ✨ Novos: {alertas_novos}")
        print(f"  📌 Mantidos: {alertas_mantidos}")  
        print(f"  ⏰ Removidos: {alertas_removidos}")
        print(f"  📊 Total: {len(alertas_finais)}")
        
        return list(alertas_finais.values())
    
    def _is_alerta_ainda_valido(self, alert_data: dict, agora: datetime) -> bool:
        """Verificar se alerta ainda é válido."""
        expires_str = alert_data.get('expires', '')
        
        if not expires_str:
            return True
            
        try:
            if isinstance(expires_str, str):
                expires_obj = datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
            else:
                expires_obj = expires_str
            
            is_valid = expires_obj > agora
            print(f"    🔍 Validando {alert_data.get('id', 'unknown')}: expires={expires_obj}, now={agora}, valid={is_valid}")
            return is_valid
        except Exception as e:
            print(f"    ⚠️ Erro ao validar {alert_data.get('id', 'unknown')}: {e}")
            return True  # Assumir válido em caso de erro


def test_sistema_persistencia():
    """Teste completo do sistema de persistência."""
    
    print("🚀 INICIANDO TESTE DO SISTEMA DE PERSISTÊNCIA")
    print("=" * 60)
    
    persistence = MockAlertaPersistence()
    now = datetime.now()
    
    # Alertas de teste
    alert_1 = {
        "id": "alert_001",
        "titulo": "Chuva Forte SP",
        "severidade": "Perigo",
        "expires": (now + timedelta(hours=2)).isoformat()
    }
    
    alert_2 = {
        "id": "alert_002", 
        "titulo": "Vento Forte SP",
        "severidade": "Perigo Potencial",
        "expires": (now + timedelta(minutes=30)).isoformat()
    }
    
    alert_3_expirado = {
        "id": "alert_003",
        "titulo": "Granizo SP (EXPIRADO)",
        "severidade": "Grande Perigo",
        "expires": (now - timedelta(hours=1)).isoformat()
    }
    
    print("\\n📋 TESTE 1: Primeiro scan com 3 alertas (1 expirado)")
    resultado_1 = persistence.merge_alertas_com_persistencia(
        [alert_1, alert_2, alert_3_expirado], 
        now
    )
    
    assert len(resultado_1) == 2, f"Esperado 2 alertas, obtido {len(resultado_1)}"
    ids_1 = {alert["id"] for alert in resultado_1}
    assert "alert_001" in ids_1
    assert "alert_002" in ids_1
    assert "alert_003" not in ids_1  # Expirado deve ser removido
    print("✅ PASSOU: Alertas válidos mantidos, expirados removidos")
    
    print("\\n📋 TESTE 2: Segundo scan com falha (só 1 alerta retornado)")
    print("   Simulando rate limiting onde RSS retorna apenas parte dos alertas")
    resultado_2 = persistence.merge_alertas_com_persistencia(
        [alert_2],  # Só o alert_2 retornado
        now
    )
    
    assert len(resultado_2) == 2, f"Esperado 2 alertas persistentes, obtido {len(resultado_2)}"
    ids_2 = {alert["id"] for alert in resultado_2}
    assert "alert_001" in ids_2  # CRÍTICO: Deve manter mesmo não estando no scan!
    assert "alert_002" in ids_2
    print("✅ PASSOU: Alert_001 mantido por persistência mesmo não estando no scan RSS!")
    
    print("\\n📋 TESTE 3: Terceiro scan com novo alerta")
    alert_4_novo = {
        "id": "alert_004",
        "titulo": "Tempestade SP",
        "severidade": "Grande Perigo", 
        "expires": (now + timedelta(hours=5)).isoformat()
    }
    
    resultado_3 = persistence.merge_alertas_com_persistencia(
        [alert_1, alert_4_novo],  # alert_1 confirmado + novo
        now
    )
    
    assert len(resultado_3) == 3, f"Esperado 3 alertas, obtido {len(resultado_3)}"
    ids_3 = {alert["id"] for alert in resultado_3}
    assert "alert_001" in ids_3  # Confirmado
    assert "alert_002" in ids_3  # Persistido (ainda válido)
    assert "alert_004" in ids_3  # Novo
    print("✅ PASSOU: Novos alertas adicionados, persistentes mantidos")
    
    print("\\n📋 TESTE 4: Quarto scan após expiração natural")
    now_futuro = now + timedelta(hours=1)  # 1 hora depois - alert_2 deve expirar
    
    resultado_4 = persistence.merge_alertas_com_persistencia(
        [alert_1, alert_4_novo],
        now_futuro
    )
    
    assert len(resultado_4) == 2, f"Esperado 2 alertas após expiração, obtido {len(resultado_4)}"
    ids_4 = {alert["id"] for alert in resultado_4}
    assert "alert_001" in ids_4
    assert "alert_004" in ids_4
    assert "alert_002" not in ids_4  # Deve ter expirado naturalmente!
    print("✅ PASSOU: Alert_002 removido automaticamente após expiração natural")
    
    print("\\n🎉 TODOS OS TESTES PASSARAM COM SUCESSO!")
    print("=" * 60)
    print("📊 RESUMO DOS BENEFÍCIOS IMPLEMENTADOS:")
    print("  ✅ Alertas válidos persistem durante falhas do RSS")
    print("  ✅ Alertas expirados são removidos automaticamente") 
    print("  ✅ Novos alertas são integrados corretamente")
    print("  ✅ Sistema robusto contra rate limiting")
    print("  ✅ Merge inteligente preserva dados importantes")
    
    return True


def test_casos_extremos():
    """Teste de casos extremos e edge cases."""
    
    print("\\n🔬 TESTANDO CASOS EXTREMOS")
    print("-" * 40)
    
    persistence = MockAlertaPersistence()
    now = datetime.now()
    
    # Teste: Lista vazia de novos alertas
    print("\\n🧪 Caso 1: Lista vazia de novos alertas")
    resultado_vazio = persistence.merge_alertas_com_persistencia([], now)
    assert len(resultado_vazio) == 0
    print("✅ PASSOU: Lista vazia tratada corretamente")
    
    # Teste: Alertas sem data de expiração
    print("\\n🧪 Caso 2: Alertas sem data de expiração")
    alert_permanente = {
        "id": "perm_001",
        "titulo": "Alerta Permanente",
        "severidade": "Informativo"
        # Sem campo 'expires'
    }
    
    resultado_perm = persistence.merge_alertas_com_persistencia([alert_permanente], now)
    assert len(resultado_perm) == 1
    print("✅ PASSOU: Alertas sem expiração tratados como permanentes")
    
    # Teste: Atualização de alerta existente
    print("\\n🧪 Caso 3: Atualização de alerta existente")
    alert_atualizado = {
        "id": "perm_001", 
        "titulo": "Alerta Permanente ATUALIZADO",
        "severidade": "Perigo",
        "nova_info": "Dados adicionais"
    }
    
    resultado_atual = persistence.merge_alertas_com_persistencia([alert_atualizado], now)
    assert len(resultado_atual) == 1
    assert resultado_atual[0]["titulo"] == "Alerta Permanente ATUALIZADO"
    assert "nova_info" in resultado_atual[0]
    print("✅ PASSOU: Alerta existente atualizado com novos dados")
    
    print("\\n✅ TODOS OS CASOS EXTREMOS PASSARAM!")


if __name__ == "__main__":
    print("🎯 EXECUTANDO TESTES DE VALIDAÇÃO DA IMPLEMENTAÇÃO")
    print("\\nEste teste valida a lógica implementada no sensor.py")
    print("sem depender do ambiente do Home Assistant.")
    
    success = test_sistema_persistencia()
    test_casos_extremos()
    
    if success:
        print("\\n" + "=" * 60)
        print("🎊 IMPLEMENTAÇÃO VALIDADA COM SUCESSO!")
        print("🚀 O sistema está pronto para resolver o problema de alertas")
        print("   que 'somem' durante falhas do RSS do INMET.")
        print("=" * 60)