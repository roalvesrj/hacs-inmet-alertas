#!/usr/bin/env python3
"""
🧪 Teste simplificado para validar a correção do sensor de mapa
Simula o comportamento da integração sem dependências do Home Assistant
"""

import sys
import os
from datetime import datetime
from typing import Dict, List, Any

# Adicionar diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock das classes do Home Assistant para teste
class MockHomeAssistant:
    pass

class MockSession:
    def __init__(self):
        import requests
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Home Assistant INMET Integration/1.8.0",
            "Accept": "application/rss+xml, application/xml, text/xml",
        })
    
    async def get(self, url, timeout=30, headers=None):
        # Simular requisição async usando requests sync
        response = self.session.get(url, timeout=timeout)
        return MockResponse(response)

class MockResponse:
    def __init__(self, response):
        self.status = response.status_code
        self._response = response
    
    async def text(self):
        return self._response.text

def async_get_clientsession(hass):
    return MockSession()

# Patch para simular Home Assistant
import helpers.rss_parser
helpers.rss_parser.async_get_clientsession = async_get_clientsession

async def test_rss_parser_geografico():
    """Testa o RSSParser com dados geográficos."""
    print("🗺️ TESTE DO RSSPARSER GEOGRÁFICO")
    print("=" * 50)
    
    try:
        from helpers.rss_parser import RSSParser
        
        # Criar mock do Home Assistant
        mock_hass = MockHomeAssistant()
        
        # Criar parser
        parser = RSSParser(mock_hass)
        
        # Testar busca de alertas principais
        print("1️⃣ Buscando alertas principais...")
        alertas = await parser.buscar_alertas_principais()
        
        if not alertas:
            print("❌ Nenhum alerta encontrado")
            return False
        
        print(f"✅ {len(alertas)} alertas encontrados")
        
        # Testar alguns alertas específicos
        estado = "GO"
        alertas_com_geo = 0
        area_total = 0.0
        
        print(f"\n2️⃣ Testando alertas específicos para {estado}...")
        
        for i, alerta in enumerate(alertas[:5]):  # Testar apenas 5
            print(f"\n🔍 Alerta {i+1}: {alerta.get('titulo', 'N/A')[:50]}...")
            
            # Buscar detalhes
            link = alerta.get('link', '')
            if link:
                detalhes = await parser.buscar_detalhes_alerta(link)
                
                if detalhes:
                    # Verificar se tem dados geográficos
                    dados_geo = detalhes.get('dados_geograficos')
                    
                    if dados_geo:
                        alertas_com_geo += 1
                        area = dados_geo.get('area_total_km2', 0)
                        area_total += area
                        
                        print(f"  🗺️ DADOS GEOGRÁFICOS!")
                        print(f"     📐 Área: {area} km²")
                        print(f"     📍 Centro: {dados_geo.get('centro_geografico')}")
                        print(f"     🔢 Polígonos: {dados_geo.get('total_poligonos', 0)}")
                    else:
                        print(f"  ⏭️ Sem dados geográficos")
                        
                        # Debug: verificar se tem polígonos brutos
                        polygons = detalhes.get('polygons', [])
                        if polygons:
                            print(f"     🗂️ Polígonos brutos encontrados: {len(polygons)}")
                            print(f"     📊 Primeiro: {polygons[0][:100]}...")
                        else:
                            print(f"     ❌ Nenhum polígono encontrado")
                else:
                    print(f"  ❌ Falha ao buscar detalhes")
        
        print(f"\n3️⃣ RESULTADOS:")
        print(f"  📊 Total testado: 5 alertas")
        print(f"  🗺️ Com dados geográficos: {alertas_com_geo}")
        print(f"  📐 Área total: {area_total:.2f} km²")
        
        if alertas_com_geo > 0:
            print(f"\n🎉 SUCESSO! Parser extraiu dados geográficos corretamente")
            return True
        else:
            print(f"\n⚠️ Nenhum dado geográfico extraído")
            print(f"   Possíveis causas:")
            print(f"   • Namespace CAP não resolvido corretamente")
            print(f"   • Estrutura XML diferente do esperado")
            print(f"   • GeoProcessor com problema")
            return False
        
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_geo_processor():
    """Teste rápido do GeoProcessor."""
    print("\n🔧 TESTE RÁPIDO DO GEOPROCESSOR:")
    
    try:
        from helpers.geo_processor import GeoProcessor
        
        # Coordenadas de exemplo
        polygon_test = "-16.6864,-49.2643 -16.5864,-49.1643 -16.4864,-49.2643 -16.6864,-49.2643"
        
        resultado = GeoProcessor.processar_poligono_completo(polygon_test, "teste")
        
        if resultado:
            print(f"✅ GeoProcessor OK - Área: {resultado['area_km2']} km²")
            return True
        else:
            print(f"❌ GeoProcessor falhou")
            return False
            
    except Exception as e:
        print(f"❌ Erro no GeoProcessor: {e}")
        return False

async def main():
    """Função principal do teste."""
    print("🧪 TESTE DE VALIDAÇÃO - SENSOR DE MAPA GEOGRÁFICO")
    print("=" * 60)
    
    # Teste do GeoProcessor
    geo_ok = test_geo_processor()
    
    # Teste do RSSParser
    parser_ok = await test_rss_parser_geografico()
    
    print("\n" + "=" * 60)
    
    if geo_ok and parser_ok:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Correção implementada com sucesso")
        print("📋 O sensor de mapa deve funcionar corretamente agora")
    elif geo_ok and not parser_ok:
        print("⚠️ GeoProcessor OK, mas RSSParser com problemas")
        print("🔧 Necessário ajustar extração de polígonos do CAP")
    else:
        print("❌ FALHAS DETECTADAS!")
        print("🔧 Necessário revisar implementação")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())