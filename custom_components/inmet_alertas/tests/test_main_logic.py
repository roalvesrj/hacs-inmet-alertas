#!/usr/bin/env python3
"""
Teste direto da lógica do INMET usando as funções do standalone.
"""

import asyncio
import aiohttp
import feedparser
from datetime import datetime
from typing import List, Dict, Any, Optional
import sys
import os

# Adicionar diretórios ao Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_standalone'))

async def test_main_logic():
    """Testa a lógica principal replicada do standalone."""
    print("🧪 Testando lógica principal do INMET...")
    
    try:
        # Importar as classes do standalone
        from test_standalone.utils.rss_parser import RSSParser
        
        # Configurar estado para teste
        estado = "GO"
        url_principal = "https://apiprevmet3.inmet.gov.br/avisos/rss"
        
        print(f"🎯 Buscando alertas para: {estado}")
        print(f"📡 URL principal: {url_principal}")
        
        # Criar parser
        parser = RSSParser(debug=True)
        
        # Buscar RSS principal
        alertas_all = parser.parse_main_rss(url_principal)
        
        if not alertas_all:
            print("❌ Nenhum alerta encontrado no RSS principal")
            return
            
        print(f"📊 Total de alertas no RSS: {len(alertas_all)}")
        
        # Processar cada alerta individualmente
        alertas_do_estado = []
        alertas_ativos = []
        
        for i, alerta in enumerate(alertas_all):
            print(f"  🔍 Processando alerta {i+1}/{len(alertas_all)}: {alerta.get('title', 'N/A')[:50]}...")
            
            # Buscar dados específicos do alerta para o estado
            cap_data = parser.parse_specific_rss(alerta['link'], estado)
            
            if cap_data:
                # Se chegou aqui, é porque o alerta afeta o estado
                alerta_completo = {**alerta, **cap_data}
                alertas_do_estado.append(alerta_completo)
                
                # Verificar se está ativo
                agora = datetime.now()
                onset = cap_data.get('onset')
                expires = cap_data.get('expires')
                
                if onset and expires:
                    try:
                        onset_dt = datetime.fromisoformat(onset.replace('Z', '+00:00')).replace(tzinfo=None)
                        expires_dt = datetime.fromisoformat(expires.replace('Z', '+00:00')).replace(tzinfo=None)
                        
                        if onset_dt <= agora <= expires_dt:
                            alertas_ativos.append(alerta_completo)
                            print(f"    ✅ Alerta ATIVO: {cap_data.get('event', 'N/A')}")
                        else:
                            print(f"    ⏰ Alerta inativo (fora do período)")
                    except:
                        print(f"    ⚠️  Erro ao processar datas do alerta")
                else:
                    print(f"    ⚠️  Alerta sem datas de início/fim")
            else:
                print(f"    ⏭️  Alerta não afeta {estado}")
        
        # Fechar parser
        parser.close()        # Resultados finais
        print(f"\n📈 RESULTADOS FINAIS:")
        print(f"  📊 Total de alertas: {len(alertas_all)}")
        print(f"  🎯 Alertas para {estado}: {len(alertas_do_estado)}")
        print(f"  🔥 Alertas ativos para {estado}: {len(alertas_ativos)}")
        
        if alertas_ativos:
            print(f"\n📋 ALERTAS ATIVOS EM {estado}:")
            for alerta in alertas_ativos:
                print(f"  • {alerta.get('event', 'N/A')} - {alerta.get('severity', 'N/A')}")
                print(f"    Início: {alerta.get('onset', 'N/A')}")
                print(f"    Fim: {alerta.get('expires', 'N/A')}")
                if alerta.get('areas'):
                    print(f"    Áreas: {', '.join(alerta['areas'][:3])}{'...' if len(alerta['areas']) > 3 else ''}")
                print()
        else:
            print(f"\nℹ️  Nenhum alerta ativo para {estado} no momento")
            
        print("✅ Teste concluído com sucesso!")
        
        # Retornar os mesmos dados que o sensor retornaria
        return {
            'alerts': alertas_ativos,
            'count': len(alertas_ativos),
            'estado': estado,
            'last_update': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test_main_logic())
    
    if result:
        print(f"\n🎉 SUCESSO! Dados que seriam retornados pelo sensor:")
        print(f"  Estado: {result['estado']}")
        print(f"  Alertas ativos: {result['count']}")
        print(f"  Última atualização: {result['last_update']}")
    else:
        print(f"\n❌ Falha no teste")