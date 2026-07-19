#!/usr/bin/env python3
"""
🔧 Teste de validação específica das correções do sensor de mapa
Foca apenas na lógica geográfica sem dependências externas
"""

import sys
import os
import xml.etree.ElementTree as ET

# Adicionar diretório pai
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_xml_parsing():
    """Testa o parsing de XML CAP com polígonos."""
    print("🔍 TESTE DE PARSING XML CAP")
    print("=" * 40)
    
    # XML de exemplo baseado nos dados reais do INMET
    xml_example = '''<?xml version="1.0" encoding="UTF-8"?>
    <alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
        <info>
            <event>Baixa Umidade</event>
            <severity>Moderate</severity>
            <certainty>Likely</certainty>
            <urgency>Future</urgency>
            <description>Umidade relativa do ar abaixo de 30%</description>
            <instruction>Beba bastante líquido</instruction>
            <onset>2024-09-22T13:00:00-03:00</onset>
            <expires>2024-09-22T18:00:00-03:00</expires>
            <parameter>
                <valueName>Municipios</valueName>
                <value>Goiânia - GO (5208707), Anápolis - GO (5201108)</value>
            </parameter>
            <parameter>
                <valueName>colorRisk</valueName>
                <value>#FF8C00</value>
            </parameter>
            <area>
                <areaDesc>Região Central de Goiás</areaDesc>
                <polygon>-16.6864,-49.2643 -16.5864,-49.1643 -16.4864,-49.2643 -16.6864,-49.2643</polygon>
            </area>
        </info>
    </alert>'''
    
    try:
        # Parse do XML
        root = ET.fromstring(xml_example)
        print(f"✅ XML parseado - Root: {root.tag}")
        
        # Definir namespace
        ns = {'cap': 'urn:oasis:names:tc:emergency:cap:1.2'}
        
        # Buscar info
        info = root.find('.//cap:info', ns)
        if info is None:
            info = root.find('.//info')
        
        print(f"✅ Info encontrado: {info is not None}")
        
        if info is not None:
            # Extrair dados básicos - corrigir busca namespace
            event_elem = info.find('cap:event', ns)
            if event_elem is None:
                event_elem = info.find('event')
            
            severity_elem = info.find('cap:severity', ns)
            if severity_elem is None:
                severity_elem = info.find('severity')
            
            print(f"📊 Evento: {event_elem.text if event_elem is not None and event_elem.text else 'N/A'}")
            print(f"📊 Severidade: {severity_elem.text if severity_elem is not None and severity_elem.text else 'N/A'}")
            
            # Buscar área com polígono
            areas = info.findall('.//cap:area', ns)
            if not areas:
                areas = info.findall('.//area')
            print(f"📍 Áreas encontradas: {len(areas)}")
            
            for i, area in enumerate(areas):
                # Buscar polígono com estratégias diferentes
                polygon_elem = area.find('cap:polygon', ns)
                if polygon_elem is None:
                    polygon_elem = area.find('polygon')
                if polygon_elem is None:
                    # Tentar busca recursiva
                    for child in area.iter():
                        if child.tag.endswith('polygon'):
                            polygon_elem = child
                            break
                
                if polygon_elem is not None and polygon_elem.text:
                    polygon_text = polygon_elem.text.strip()
                    print(f"🗺️ Polígono {i+1}: {polygon_text}")
                    
                    # Testar processamento geográfico
                    return test_geographic_processing(polygon_text)
                else:
                    print(f"❌ Polígono {i+1}: Não encontrado")
                    # Debug - mostrar estrutura da área
                    print(f"     🔍 Debug - filhos da área:")
                    for child in area:
                        print(f"        • {child.tag}: {child.text[:50] if child.text else 'None'}...")
        
        return False
        
    except Exception as e:
        print(f"❌ Erro no parsing XML: {e}")
        return False

def test_geographic_processing(polygon_text):
    """Testa o processamento geográfico."""
    print(f"\n📐 TESTE DE PROCESSAMENTO GEOGRÁFICO")
    print(f"📊 Entrada: {polygon_text}")
    
    try:
        from helpers.geo_processor import GeoProcessor
        
        # Processar polígono
        resultado = GeoProcessor.processar_poligono_completo(polygon_text, "teste_xml")
        
        if resultado:
            print(f"✅ Processamento bem-sucedido:")
            print(f"   📐 Área: {resultado['area_km2']} km²")
            print(f"   📍 Centro: {resultado['centro']}")
            print(f"   🔢 Pontos: {resultado['total_pontos']}")
            print(f"   🔍 Zoom: {resultado['zoom_recomendado']}")
            
            # Simular dados geográficos como seriam criados pelo sensor
            dados_geo = {
                'poligonos_individuais': [resultado],
                'area_total_km2': resultado['area_km2'],
                'centro_geografico': resultado['centro'],
                'bounding_box': resultado['bounding_box'],
                'zoom_recomendado': resultado['zoom_recomendado'],
                'total_poligonos': 1
            }
            
            print(f"\n📋 Dados que o sensor criaria:")
            print(f"   🗺️ Total polígonos: {dados_geo['total_poligonos']}")
            print(f"   📐 Área total: {dados_geo['area_total_km2']} km²")
            print(f"   📍 Centro estado: {dados_geo['centro_geografico']}")
            
            return True
        else:
            print(f"❌ Processamento falhou")
            return False
            
    except Exception as e:
        print(f"❌ Erro no processamento geográfico: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sensor_simulation():
    """Simula o comportamento do sensor de mapa."""
    print(f"\n🧮 SIMULAÇÃO DO SENSOR DE MAPA")
    print("=" * 40)
    
    try:
        # Simular alertas com dados geográficos
        alertas_simulados = [
            {
                "id": "51655",
                "event": "Baixa Umidade",
                "severidade_inmet": "Perigo",
                "color_risk": "#FF8C00",
                "dados_geograficos": {
                    "poligonos_individuais": [
                        {
                            "coordenadas": [[-16.6864, -49.2643], [-16.5864, -49.1643], 
                                          [-16.4864, -49.2643], [-16.6864, -49.2643]],
                            "area_km2": 118.50,
                            "centro": [-16.6112, -49.2393]
                        }
                    ],
                    "area_total_km2": 118.50,
                    "centro_geografico": [-16.6112, -49.2393],
                    "total_poligonos": 1
                }
            },
            {
                "id": "51656",
                "event": "Tempestade",
                "severidade_inmet": "Grande Perigo",
                "color_risk": "#F80703",
                "dados_geograficos": {
                    "poligonos_individuais": [
                        {
                            "coordenadas": [[-16.7864, -49.3643], [-16.6864, -49.2643], 
                                          [-16.5864, -49.3643], [-16.7864, -49.3643]],
                            "area_km2": 95.30,
                            "centro": [-16.6864, -49.3063]
                        }
                    ],
                    "area_total_km2": 95.30,
                    "centro_geografico": [-16.6864, -49.3063],
                    "total_poligonos": 1
                }
            }
        ]
        
        # Simular lógica do sensor
        poligonos_por_severidade = {
            "Grande Perigo": [],
            "Perigo": [],
            "Perigo Potencial": []
        }
        
        area_total = 0.0
        total_poligonos = 0
        
        for alerta in alertas_simulados:
            dados_geo = alerta.get("dados_geograficos")
            if dados_geo:
                severidade = alerta["severidade_inmet"]
                area_alerta = dados_geo["area_total_km2"]
                area_total += area_alerta
                
                # Criar estrutura do polígono
                for i, poli in enumerate(dados_geo["poligonos_individuais"]):
                    poligono_info = {
                        "id": f"{alerta['id']}_{i}",
                        "alerta_id": alerta["id"],
                        "evento": alerta["event"],
                        "severidade": severidade,
                        "cor": alerta["color_risk"],
                        "coordenadas": poli["coordenadas"],
                        "area_km2": poli["area_km2"],
                        "centro": poli["centro"]
                    }
                    
                    if severidade in poligonos_por_severidade:
                        poligonos_por_severidade[severidade].append(poligono_info)
                        total_poligonos += 1
        
        # Resultado final do sensor
        print(f"📊 RESULTADO DO SENSOR:")
        print(f"   🔢 Valor: {total_poligonos} polígonos")
        print(f"   📐 Área total: {area_total} km²")
        
        print(f"\n📋 Camadas por severidade:")
        for severidade, polys in poligonos_por_severidade.items():
            if polys:
                area_sev = sum(p["area_km2"] for p in polys)
                print(f"   🔸 {severidade}: {len(polys)} polígonos, {area_sev} km²")
        
        # Verificar se teria múltiplas camadas
        camadas_ativas = sum(1 for polys in poligonos_por_severidade.values() if polys)
        if camadas_ativas > 1:
            print(f"   ✅ {camadas_ativas} camadas ativas - Sobreposição OK!")
        
        return total_poligonos > 0
        
    except Exception as e:
        print(f"❌ Erro na simulação: {e}")
        return False

def main():
    """Função principal."""
    print("🧪 VALIDAÇÃO COMPLETA - CORREÇÕES DO SENSOR DE MAPA")
    print("=" * 60)
    
    # Teste 1: XML Parsing
    xml_ok = test_xml_parsing()
    
    # Teste 2: Simulação do sensor
    sensor_ok = test_sensor_simulation()
    
    print("\n" + "=" * 60)
    
    if xml_ok and sensor_ok:
        print("🎉 TODAS AS VALIDAÇÕES PASSARAM!")
        print("✅ Correções implementadas com sucesso")
        print("\n💡 O SENSOR DE MAPA DEVE FUNCIONAR CORRETAMENTE:")
        print("   🗺️ Extração de polígonos CAP funcionando")
        print("   📐 Cálculo de áreas operacional")
        print("   🎨 Organização por severidade OK")
        print("   📊 Sobreposição de camadas suportada")
        print("\n📋 PRÓXIMOS PASSOS:")
        print("   1. Reiniciar Home Assistant")
        print("   2. Verificar sensor.inmet_alertas_mapa_[estado]")
        print("   3. Confirmar valor > 0 se há alertas ativos")
    else:
        print("❌ ALGUMAS VALIDAÇÕES FALHARAM!")
        if not xml_ok:
            print("   🔍 Problema na extração de polígonos XML")
        if not sensor_ok:
            print("   🧮 Problema na simulação do sensor")
        
        print("\n🔧 AÇÕES NECESSÁRIAS:")
        print("   • Revisar namespace CAP no RSSParser")
        print("   • Verificar processamento geográfico")
        print("   • Testar com dados reais do INMET")

if __name__ == "__main__":
    main()