#!/usr/bin/env python3
"""
Script para testar a integração principal do INMET Alertas.
Simula uma execução do sensor para verificar se está funcionando.
"""

import asyncio
import sys
import os
from unittest.mock import MagicMock

# Adicionar o diretório atual ao Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock básico do Home Assistant
class MockHomeAssistant:
    def __init__(self):
        self.data = {}
        
class MockConfigEntry:
    def __init__(self):
        self.data = {
            "estado": "GO",
            "notificacoes_perigo": True,
            "update_interval": 30
        }
        self.options = {}
        
class MockLogger:
    def debug(self, msg, *args):
        print(f"DEBUG: {msg % args if args else msg}")
    
    def info(self, msg, *args):
        print(f"INFO: {msg % args if args else msg}")
    
    def warning(self, msg, *args):
        print(f"WARNING: {msg % args if args else msg}")
    
    def error(self, msg, *args):
        print(f"ERROR: {msg % args if args else msg}")

async def test_sensor():
    """Testa o sensor principal."""
    from sensor import INMETDataUpdateCoordinator, INMETAlertasSensor
    
    # Setup mock objects
    hass = MockHomeAssistant()
    config_entry = MockConfigEntry()
    
    # Criar coordinator
    coordinator = INMETDataUpdateCoordinator(
        hass, 
        "GO",  # estado
        30,    # update_interval
        True   # notificacoes_perigo
    )
    
    # Testar atualização dos dados
    print("🧪 Testando a atualização de dados...")
    
    try:
        await coordinator._async_update_data()
        print(f"✅ Dados atualizados com sucesso!")
        print(f"📊 Dados do coordinator: {coordinator.data}")
        
        # Criar sensor
        sensor = INMETAlertasSensor(coordinator, config_entry)
        
        # Testar propriedades do sensor
        print(f"🏷️  Nome do sensor: {sensor.name}")
        print(f"📈 Estado do sensor: {sensor.state}")
        print(f"🔧 Atributos do sensor: {sensor.extra_state_attributes}")
        
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sensor())