#!/usr/bin/env python3
"""
Teste simples da lógica principal do INMET.
Testa apenas as funções que importamos do utils.py.
"""

import asyncio
import sys
import os

# Adicionar o diretório atual ao Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_utils():
    """Testa as funções utilitárias."""
    print("🧪 Testando funções utilitárias...")
    
    try:
        from utils import fetch_rss_data, parse_alert_item, is_alert_active
        
        # Testar fetch RSS
        print("📡 Buscando dados RSS...")
        rss_data = await fetch_rss_data()
        
        if rss_data and 'entries' in rss_data:
            print(f"✅ RSS obtido com sucesso! Total de entradas: {len(rss_data['entries'])}")
            
            # Filtrar alertas para GO
            alertas_go = []
            alertas_ativos = []
            
            for entry in rss_data['entries']:
                alert_data = await parse_alert_item(entry)
                if alert_data and alert_data.get('estados') and 'GO' in alert_data['estados']:
                    alertas_go.append(alert_data)
                    
                    # Verificar se está ativo
                    if await is_alert_active(alert_data):
                        alertas_ativos.append(alert_data)
            
            print(f"📊 Alertas total: {len(rss_data['entries'])}")
            print(f"🎯 Alertas para GO: {len(alertas_go)}")
            print(f"🔥 Alertas ativos para GO: {len(alertas_ativos)}")
            
            if alertas_ativos:
                print("\n📋 Alertas ativos:")
                for alerta in alertas_ativos:
                    print(f"  • {alerta.get('evento', 'N/A')} - {alerta.get('severidade', 'N/A')}")
                    print(f"    Estados: {', '.join(alerta.get('estados', []))}")
                    if alerta.get('areas'):
                        print(f"    Áreas: {', '.join(alerta['areas'][:3])}{'...' if len(alerta['areas']) > 3 else ''}")
            else:
                print("ℹ️  Nenhum alerta ativo encontrado para GO")
                
        else:
            print("❌ Falha ao obter dados RSS")
            
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_utils())