#!/usr/bin/env python3
"""
Teste simplificado para validar o processamento geográfico do INMET.
"""

import sys
import os

# Adicionar diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_geo_processor():
    """Testa o processador geográfico."""
    print("🗺️  Testando processador geográfico...")
    
    try:
        from helpers.geo_processor import GeoProcessor
        
        # Dados de teste simulando um polígono de Goiás
        polygon_test = "-16.6864,-49.2643 -16.5864,-49.1643 -16.4864,-49.2643 -16.6864,-49.2643"
        
        print(f"📊 Dados de entrada: {polygon_test}")
        
        # Teste 1: Parse de coordenadas
        print("\n1️⃣  Testando parse de coordenadas...")
        coordenadas = GeoProcessor.parse_coordenadas_cap(polygon_test)
        
        if coordenadas:
            print(f"✅ Coordenadas processadas: {len(coordenadas)} pontos")
            print(f"   🗺️  Primeira: {coordenadas[0]}")
            print(f"   🗺️  Última: {coordenadas[-1]}")
        else:
            print("❌ Falha ao processar coordenadas")
            return False
        
        # Teste 2: Cálculo de área
        print("\n2️⃣  Testando cálculo de área...")
        area = GeoProcessor.calcular_area_poligono(coordenadas)
        print(f"✅ Área calculada: {area:.2f} km²")
        
        # Teste 3: Centro geográfico
        print("\n3️⃣  Testando centro geográfico...")
        centro = GeoProcessor.calcular_centro_geografico(coordenadas)
        if centro:
            print(f"✅ Centro: [{centro[0]:.6f}, {centro[1]:.6f}]")
        else:
            print("❌ Falha ao calcular centro")
            return False
        
        # Teste 4: Bounding box
        print("\n4️⃣  Testando bounding box...")
        bbox = GeoProcessor.calcular_bounding_box(coordenadas)
        if bbox:
            print(f"✅ Bounding box:")
            print(f"   📍 Min: [{bbox['min_lat']:.6f}, {bbox['min_lon']:.6f}]")
            print(f"   📍 Max: [{bbox['max_lat']:.6f}, {bbox['max_lon']:.6f}]")
        else:
            print("❌ Falha ao calcular bounding box")
            return False
        
        # Teste 5: Zoom recomendado
        print("\n5️⃣  Testando zoom recomendado...")
        zoom = GeoProcessor.calcular_zoom_recomendado(bbox)
        print(f"✅ Zoom recomendado: {zoom}")
        
        # Teste 6: Processamento completo
        print("\n6️⃣  Testando processamento completo...")
        resultado = GeoProcessor.processar_poligono_completo(polygon_test, "teste_001")
        
        if resultado:
            print(f"✅ Processamento completo bem-sucedido:")
            print(f"   📐 Área: {resultado['area_km2']} km²")
            print(f"   📍 Centro: {resultado['centro']}")
            print(f"   🔢 Pontos: {resultado['total_pontos']}")
            print(f"   🔍 Zoom: {resultado['zoom_recomendado']}")
        else:
            print("❌ Falha no processamento completo")
            return False
        
        # Teste 7: Combinação de múltiplos polígonos
        print("\n7️⃣  Testando combinação de polígonos...")
        
        # Simular segundo polígono
        polygon_test2 = "-16.7864,-49.3643 -16.6864,-49.2643 -16.5864,-49.3643 -16.7864,-49.3643"
        resultado2 = GeoProcessor.processar_poligono_completo(polygon_test2, "teste_002")
        
        if resultado2:
            # Combinar os dois polígonos
            poligonos = [resultado, resultado2]
            dados_combinados = GeoProcessor.combinar_poligonos_estado(poligonos)
            
            print(f"✅ Combinação de polígonos:")
            print(f"   📐 Área total: {dados_combinados['area_total_km2']} km²")
            print(f"   📍 Centro estado: {dados_combinados['centro_estado']}")
            print(f"   🔢 Total polígonos: {dados_combinados['total_poligonos']}")
            print(f"   🔍 Zoom estado: {dados_combinados['zoom_estado']}")
        else:
            print("❌ Falha ao processar segundo polígono")
            return False
        
        print("\n✅ TODOS OS TESTES GEOGRÁFICOS PASSARAM!")
        return True
        
    except Exception as e:
        print(f"❌ Erro durante teste geográfico: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_constantes():
    """Testa as constantes adicionadas."""
    print("\n🔧 Testando constantes...")
    
    try:
        from const import (
            CORES_INMET_MAPA, COLORISK_TO_SEVERIDADE, MAPA_CONFIG,
            CENTROS_ESTADOS, ATTR_POLIGONOS, ATTR_AREA_TOTAL_AFETADA
        )
        
        # Teste das cores
        print(f"🎨 Cores INMET: {len(CORES_INMET_MAPA)} severidades")
        for sev, cor in CORES_INMET_MAPA.items():
            print(f"   {sev}: {cor}")
        
        # Teste dos centros dos estados
        print(f"📍 Centros dos estados: {len(CENTROS_ESTADOS)} estados")
        print(f"   GO: {CENTROS_ESTADOS.get('GO')}")
        print(f"   RJ: {CENTROS_ESTADOS.get('RJ')}")
        
        # Teste mapeamento de cores
        print(f"🗂️  Mapeamento ColorRisk: {len(COLORISK_TO_SEVERIDADE)} cores")
        
        print("✅ Constantes validadas!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar constantes: {e}")
        return False

def simular_sensor_mapa():
    """Simula o comportamento do sensor de mapa."""
    print("\n📊 Simulando comportamento do sensor de mapa...")
    
    try:
        from helpers.geo_processor import GeoProcessor
        from const import CORES_INMET_MAPA
        
        # Simular dados de alertas com coordenadas
        alertas_simulados = [
            {
                "id": "51655",
                "event": "Baixa Umidade",
                "severidade_inmet": "Grande Perigo",
                "color_risk": "#F80703",
                "polygon": "-16.6864,-49.2643 -16.5864,-49.1643 -16.4864,-49.2643 -16.6864,-49.2643"
            },
            {
                "id": "51656", 
                "event": "Tempestade",
                "severidade_inmet": "Perigo",
                "color_risk": "#FF8C00",
                "polygon": "-16.7864,-49.3643 -16.6864,-49.2643 -16.5864,-49.3643 -16.7864,-49.3643"
            }
        ]
        
        # Processar como o sensor faria
        poligonos_por_severidade = {
            "Grande Perigo": [],
            "Perigo": [],
            "Perigo Potencial": []
        }
        
        area_total = 0.0
        total_com_geo = 0
        
        for alerta in alertas_simulados:
            # Processar dados geográficos
            resultado_geo = GeoProcessor.processar_poligono_completo(
                alerta["polygon"], 
                alerta["id"]
            )
            
            if resultado_geo:
                total_com_geo += 1
                severidade = alerta["severidade_inmet"]
                area_total += resultado_geo["area_km2"]
                
                # Criar estrutura do polígono para o sensor
                poligono_info = {
                    "id": f"{alerta['id']}_0",
                    "alerta_id": alerta["id"],
                    "evento": alerta["event"],
                    "severidade": severidade,
                    "cor": alerta["color_risk"],
                    "coordenadas": resultado_geo["coordenadas"],
                    "area_km2": resultado_geo["area_km2"],
                    "centro": resultado_geo["centro"]
                }
                
                # Adicionar à severidade correspondente
                if severidade in poligonos_por_severidade:
                    poligonos_por_severidade[severidade].append(poligono_info)
        
        # Simular atributos do sensor
        valor_sensor = sum(len(polys) for polys in poligonos_por_severidade.values())
        
        # Preparar camadas sobrepostas
        camadas = {}
        for severidade, polys in poligonos_por_severidade.items():
            if polys:
                camadas[severidade] = {
                    "cor": CORES_INMET_MAPA.get(severidade, "#808080"),
                    "total_poligonos": len(polys),
                    "area_total_km2": sum(p["area_km2"] for p in polys),
                    "poligonos": polys
                }
        
        print(f"📈 RESULTADO DA SIMULAÇÃO:")
        print(f"   🔢 Valor do sensor: {valor_sensor} polígonos")
        print(f"   📊 Área total: {area_total:.2f} km²")
        print(f"   🎯 Alertas processados: {total_com_geo}")
        
        print(f"   📋 Camadas por severidade:")
        for sev, dados in camadas.items():
            print(f"     🔸 {sev}: {dados['total_poligonos']} polígonos, {dados['area_total_km2']:.2f} km²")
        
        # Verificar se temos dados para sobreposição
        if len(camadas) > 1:
            print(f"   ✅ Múltiplas camadas disponíveis para sobreposição!")
        
        print("✅ Simulação do sensor concluída!")
        return True
        
    except Exception as e:
        print(f"❌ Erro na simulação: {e}")
        return False

if __name__ == "__main__":
    print("🧪 TESTE COMPLETO DO SISTEMA GEOGRÁFICO INMET")
    print("=" * 60)
    
    sucesso_geo = test_geo_processor()
    sucesso_const = test_constantes()
    sucesso_sensor = simular_sensor_mapa()
    
    print("\n" + "=" * 60)
    
    if sucesso_geo and sucesso_const and sucesso_sensor:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("\n💡 SENSOR DE MAPA PRONTO PARA:")
        print("   🗺️  Processar polígonos CAP do INMET")
        print("   🎨 Aplicar cores oficiais por severidade")
        print("   📊 Calcular áreas e centros geográficos")
        print("   📐 Organizar em camadas sobrepostas")
        print("   🔍 Sugerir zoom adequado para visualização")
        print("   📍 Suportar múltiplos alertas simultâneos")
        
        print(f"\n📋 ESTRUTURA DOS DADOS GEOGRÁFICOS:")
        print(f"   • sensor.inmet_alertas_mapa_[estado]")
        print(f"   • Valor: Número de polígonos ativos")
        print(f"   • Atributos: poligonos, area_total_afetada_km2,")
        print(f"     centro_geografico, camadas_por_severidade")
        
    else:
        print("❌ ALGUNS TESTES FALHARAM!")
        if not sucesso_geo:
            print("   🗺️  Processamento geográfico com problemas")
        if not sucesso_const:
            print("   🔧 Constantes com problemas")
        if not sucesso_sensor:
            print("   📊 Simulação do sensor com problemas")
            
        sys.exit(1)