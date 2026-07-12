#!/usr/bin/env python3
"""
Teste final - verificar se sensor retorna dados geográficos
"""

import sys
import os
import xml.etree.ElementTree as ET
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def test_cap_processing():
    """Simular processamento CAP igual ao sensor."""
    
    # XML de exemplo (igual ao que o INMET retorna)
    cap_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
        <info>
            <event>Baixa Umidade</event>
            <severity>Moderate</severity>
            <urgency>Future</urgency>
            <certainty>Possible</certainty>
            <description>Teste de alerta</description>
            <instruction>Siga as orientações</instruction>
            <onset>2025-01-01T12:00:00Z</onset>
            <expires>2025-01-02T12:00:00Z</expires>
            <parameter>
                <valueName>ColorRisk</valueName>
                <value>#FFFF00</value>
            </parameter>
            <parameter>
                <valueName>Municipios</valueName>
                <value>Goiânia|Aparecida de Goiânia</value>
            </parameter>
            <area>
                <areaDesc>Região Central de Goiás</areaDesc>
                <polygon>-16.6864,-49.2643 -16.5864,-49.1643 -16.4864,-49.2643 -16.6864,-49.2643</polygon>
            </area>
        </info>
    </alert>"""
    
    print("🧪 TESTE FINAL - PROCESSAMENTO CAP NO SENSOR")
    print("=" * 60)
    
    try:
        root = ET.fromstring(cap_xml)
        
        # Namespace CAP (igual ao sensor)
        ns = {'cap': 'urn:oasis:names:tc:emergency:cap:1.2'}
        cap_data = {}
        
        # Elementos diretos do alert
        for field in ['identifier', 'sender', 'sent', 'status', 'msgType']:
            elem = root.find(f'cap:{field}', ns)
            if elem is not None and elem.text:
                cap_data[field] = elem.text.strip()
        
        # Elementos do info
        info = root.find('cap:info', ns)
        if info is not None:
            for field in ['language', 'category', 'event', 'severity', 'urgency', 
                         'certainty', 'onset', 'expires', 'description', 'instruction', 
                         'web', 'contact']:
                elem = info.find(f'cap:{field}', ns)
                if elem is not None and elem.text:
                    cap_data[field] = elem.text.strip()
            
            # Parâmetros
            for param in info.findall('cap:parameter', ns):
                name_elem = param.find('cap:valueName', ns)
                value_elem = param.find('cap:value', ns)
                
                if (name_elem is not None and name_elem.text and 
                    value_elem is not None and value_elem.text):
                    param_name = name_elem.text.strip()
                    param_value = value_elem.text.strip()
                    
                    if param_name == 'ColorRisk':
                        cap_data['color_risk'] = param_value
                    elif param_name == 'Municipios':
                        cap_data['municipios'] = param_value
                    elif param_name == 'Estados':
                        cap_data['estados'] = param_value
            
            # NOVA IMPLEMENTAÇÃO - Área e dados geográficos
            areas = info.findall('cap:area', ns)
            if not areas:
                areas = info.findall('.//area')
                
            areas_desc = []
            poligonos = []
            
            for area in areas:
                # Descrição da área
                area_desc = area.find('cap:areaDesc', ns)
                if area_desc is None:
                    area_desc = area.find('areaDesc')
                if area_desc is not None and area_desc.text:
                    areas_desc.append(area_desc.text.strip())
                
                # Polígonos - usar múltiplas estratégias
                polygon_elem = area.find('cap:polygon', ns)
                if polygon_elem is None:
                    polygon_elem = area.find('polygon')
                if polygon_elem is None:
                    # Busca recursiva
                    for child in area.iter():
                        if child.tag.endswith('polygon'):
                            polygon_elem = child
                            break
                
                if polygon_elem is not None and polygon_elem.text:
                    polygon_text = polygon_elem.text.strip()
                    if polygon_text:
                        poligonos.append(polygon_text)
                        print(f"✅ Polígono extraído: {polygon_text}")
            
            cap_data['area_desc'] = '; '.join(areas_desc)
            cap_data['polygons'] = poligonos
            
            # Processar dados geográficos se existirem polígonos
            if poligonos:
                print(f"🗺️  Processando {len(poligonos)} polígonos encontrados...")
                try:
                    # Importar GeoProcessor
                    from helpers.geo_processor import GeoProcessor
                    
                    dados_geo = []
                    area_total = 0.0
                    
                    for i, polygon_text in enumerate(poligonos):
                        resultado_geo = GeoProcessor.processar_poligono_completo(
                            polygon_text, 
                            f"alerta_{i}"
                        )
                        if resultado_geo:
                            dados_geo.append(resultado_geo)
                            area_total += resultado_geo.get('area_km2', 0)
                            print(f"   📐 Polígono {i+1}: {resultado_geo.get('area_km2', 0)} km²")
                    
                    # Combinar dados geográficos
                    if dados_geo:
                        dados_combinados = GeoProcessor.combinar_poligonos_estado(dados_geo)
                        
                        cap_data['dados_geograficos'] = {
                            'poligonos_individuais': dados_geo,
                            'area_total_km2': dados_combinados['area_total_km2'],
                            'centro_geografico': dados_combinados['centro_estado'],
                            'bounding_box': dados_combinados['bounding_box_estado'],
                            'zoom_recomendado': dados_combinados['zoom_estado'],
                            'total_poligonos': len(dados_geo)
                        }
                        
                        print(f"✅ Dados geográficos processados: {len(dados_geo)} polígonos, "
                               f"{dados_combinados['area_total_km2']} km²")
                except Exception as e:
                    print(f"❌ Erro ao processar dados geográficos: {e}")
                    cap_data['dados_geograficos'] = None
        
        print(f"\n📊 RESULTADO CAP_DATA:")
        print(f"   🎯 Evento: {cap_data.get('event', 'N/A')}")
        print(f"   🎯 Severidade: {cap_data.get('severity', 'N/A')}")
        print(f"   🎯 Área: {cap_data.get('area_desc', 'N/A')}")
        print(f"   🎯 Polígonos: {len(cap_data.get('polygons', []))}")
        
        dados_geo = cap_data.get('dados_geograficos')
        if dados_geo:
            print(f"   ✅ Dados Geográficos:")
            print(f"      🔢 Total polígonos: {dados_geo.get('total_poligonos', 0)}")
            print(f"      📐 Área total: {dados_geo.get('area_total_km2', 0)} km²")
            print(f"      📍 Centro: {dados_geo.get('centro_geografico')}")
            
            # SIMULAR VALOR DO SENSOR
            valor_sensor = 0
            if dados_geo and dados_geo.get('poligonos_individuais'):
                valor_sensor = len(dados_geo['poligonos_individuais'])
            
            print(f"\n🎯 VALOR QUE O SENSOR RETORNARIA: {valor_sensor}")
            
            if valor_sensor > 0:
                print("🎉 SUCESSO! Sensor retornaria valor > 0")
            else:
                print("🚨 PROBLEMA! Sensor ainda retornaria 0")
        else:
            print(f"   ❌ SEM dados geográficos")
            print("🚨 PROBLEMA! Sensor retornaria 0")
        
        return cap_data
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return None

if __name__ == "__main__":
    test_cap_processing()