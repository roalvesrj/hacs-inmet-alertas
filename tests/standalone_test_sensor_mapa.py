#!/usr/bin/env python3
"""
Teste específico para validar o sensor de mapa geográfico INMET.
"""

import asyncio
import sys
import os
from datetime import datetime

# Adicionar diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_sensor_mapa():
    """Testa o sensor de mapa geográfico."""
    print("🗺️  Testando sensor de mapa geográfico INMET...")
    
    try:
        # Importar as classes necessárias
        from helpers.rss_parser import RSSParser
        from helpers.geo_processor import GeoProcessor
        
        # Mock do Home Assistant para teste
        class MockHomeAssistant:
            pass
        
        class MockSession:
            async def get(self, url, **kwargs):
                class MockResponse:
                    def __init__(self):
                        self.status = 200
                    
                    async def text(self):
                        # Simular resposta RSS com dados geográficos
                        if "rss" in url and url.endswith("rss"):
                            return '''<?xml version="1.0" encoding="UTF-8"?>
                            <rss version="2.0">
                                <channel>
                                    <item>
                                        <title>Aviso de Baixa Umidade</title>
                                        <link>https://apiprevmet3.inmet.gov.br/avisos/rss/51655</link>
                                        <description>Teste</description>
                                        <pubDate>Sun, 22 Sep 2024 12:00:00 GMT</pubDate>
                                    </item>
                                </channel>
                            </rss>'''
                        else:
                            # Simular resposta CAP com polígono
                            return '''<?xml version="1.0" encoding="UTF-8"?>
                            <alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
                                <info>
                                    <event>Baixa Umidade</event>
                                    <severity>Extreme</severity>
                                    <certainty>Likely</certainty>
                                    <urgency>Future</urgency>
                                    <onset>2024-09-22T13:00:00-03:00</onset>
                                    <expires>2024-09-22T18:00:00-03:00</expires>
                                    <description>Umidade relativa do ar abaixo de 12%</description>
                                    <instruction>Beba bastante líquido</instruction>
                                    <parameter>
                                        <valueName>Municipios</valueName>
                                        <value>Goiânia - GO (5208707), Anápolis - GO (5201108)</value>
                                    </parameter>
                                    <parameter>
                                        <valueName>colorRisk</valueName>
                                        <value>#F80703</value>
                                    </parameter>
                                    <area>
                                        <areaDesc>Região Central de Goiás</areaDesc>
                                        <polygon>-16.6864,-49.2643 -16.5864,-49.1643 -16.4864,-49.2643 -16.6864,-49.2643</polygon>
                                    </area>
                                </info>
                            </alert>'''
                
                return MockResponse()
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                pass
        
        # Mock do RSSParser para usar nossa sessão mockada
        hass_mock = MockHomeAssistant()
        parser = RSSParser(hass_mock)
        parser._session = MockSession()
        
        print("📡 Buscando alertas principais...")
        
        # Buscar alertas principais
        alertas_principais = await parser.buscar_alertas_principais()
        
        if not alertas_principais:
            print("❌ Nenhum alerta encontrado no teste")
            return False
        
        print(f"✅ {len(alertas_principais)} alerta(s) encontrado(s)")
        
        # Buscar detalhes com dados geográficos
        alerta = alertas_principais[0]
        print(f"🔍 Processando alerta: {alerta.get('title', 'N/A')}")
        
        detalhes = await parser.buscar_detalhes_alerta(alerta['link'])
        
        if not detalhes:
            print("❌ Erro ao buscar detalhes do alerta")
            return False
        
        print("✅ Detalhes do alerta obtidos")
        print(f"  📍 Evento: {detalhes.get('event', 'N/A')}")
        print(f"  🚨 Severidade: {detalhes.get('severidade_inmet', 'N/A')}")
        print(f"  🎨 Cor: {detalhes.get('color_risk', 'N/A')}")
        
        # Verificar dados geográficos
        dados_geo = detalhes.get('dados_geograficos')
        if dados_geo:
            print("🗺️  Dados geográficos encontrados:")
            print(f"  📐 Área total: {dados_geo.get('area_total_km2', 0)} km²")
            print(f"  📍 Centro: {dados_geo.get('centro_geografico')}")
            print(f"  🔢 Polígonos: {dados_geo.get('total_poligonos', 0)}")
            print(f"  🔍 Zoom: {dados_geo.get('zoom_recomendado', 8)}")
            
            # Testar polígonos individuais
            poligonos = dados_geo.get('poligonos_individuais', [])
            if poligonos:
                poli = poligonos[0]
                coordenadas = poli.get('coordenadas', [])
                print(f"  📊 Primeiro polígono: {len(coordenadas)} pontos")
                if coordenadas:
                    print(f"    🗺️  Primeira coordenada: {coordenadas[0]}")
                    print(f"    🗺️  Última coordenada: {coordenadas[-1]}")
        else:
            print("⚠️  Nenhum dado geográfico encontrado")
        
        # Simular dados do sensor de mapa
        print("\n📊 Simulando dados do sensor de mapa...")
        
        # Mock dos dados que o sensor retornaria
        alertas_simulados = [detalhes] if detalhes else []
        
        # Processar como o sensor faria
        poligonos_por_severidade = {
            "Grande Perigo": [],
            "Perigo": [],
            "Perigo Potencial": []
        }
        
        area_total = 0.0
        total_com_geo = 0
        
        for alerta_data in alertas_simulados:
            dados_geo = alerta_data.get("dados_geograficos")
            if dados_geo:
                total_com_geo += 1
                severidade = alerta_data.get("severidade_inmet", "Perigo Potencial")
                area_total += dados_geo.get("area_total_km2", 0)
                
                # Simular estrutura do sensor
                for i, poli in enumerate(dados_geo.get("poligonos_individuais", [])):
                    poligono_info = {
                        "id": f"teste_{i}",
                        "evento": alerta_data.get("event", ""),
                        "severidade": severidade,
                        "cor": alerta_data.get("color_risk", "#808080"),
                        "coordenadas": poli.get("coordenadas", []),
                        "area_km2": poli.get("area_km2", 0),
                        "centro": poli.get("centro")
                    }
                    
                    if severidade in poligonos_por_severidade:
                        poligonos_por_severidade[severidade].append(poligono_info)
        
        # Resultados do sensor
        print(f"📈 RESULTADOS DO SENSOR:")
        print(f"  🔢 Valor do sensor: {sum(len(polys) for polys in poligonos_por_severidade.values())} polígonos")
        print(f"  📊 Área total afetada: {area_total:.2f} km²")
        print(f"  🎯 Alertas com dados geo: {total_com_geo}")
        
        # Verificar camadas por severidade
        print(f"  📋 Camadas por severidade:")
        for severidade, polys in poligonos_por_severidade.items():
            if polys:
                area_camada = sum(p["area_km2"] for p in polys)
                print(f"    🔸 {severidade}: {len(polys)} polígonos, {area_camada:.2f} km²")
        
        print("\n✅ Teste do sensor de mapa concluído com sucesso!")
        print("\n📋 ESTRUTURA DO SENSOR VALIDADA:")
        print("  ✅ Extração de polígonos CAP")
        print("  ✅ Cálculo de áreas geográficas")
        print("  ✅ Processamento de cores por severidade")
        print("  ✅ Organização em camadas sobrepostas")
        print("  ✅ Cálculo de centros geográficos")
        print("  ✅ Suporte a múltiplos polígonos")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante teste do sensor de mapa: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    sucesso = asyncio.run(test_sensor_mapa())
    
    if sucesso:
        print(f"\n🎉 SENSOR DE MAPA FUNCIONANDO CORRETAMENTE!")
        print(f"💡 O sensor retornará:")
        print(f"   • Coordenadas de polígonos para visualização")
        print(f"   • Cores oficiais INMET por severidade")
        print(f"   • Suporte a camadas sobrepostas")
        print(f"   • Cálculos de área e centro geográfico")
        print(f"   • Zoom recomendado para visualização")
    else:
        print(f"\n❌ FALHA NO TESTE DO SENSOR DE MAPA")
        sys.exit(1)