#!/usr/bin/env python3
"""
Teste com dados REAIS do INMET - reproduzir cenário de produção
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from helpers.rss_parser import RSSParser

def main():
    print("🔴 TESTE PRODUÇÃO REAL - SENSOR MAPA INMET")
    print("=" * 60)
    
    # Criar RSSParser igual ao sensor (sem hass para teste)
    parser = RSSParser(None)
    
    # Estados para testar (os que mais têm alertas)
    estados_teste = ['GO', 'MT', 'SP', 'MG', 'BA']
    
    for estado in estados_teste:
        print(f"\n🌎 TESTANDO ESTADO: {estado}")
        print("-" * 40)
        
        try:
            # Buscar alertas igual ao sensor
            alertas = parser.get_alertas(estado)
            print(f"📊 Total alertas: {len(alertas)}")
            
            if not alertas:
                print("⚠️  Sem alertas ativos")
                continue
            
            # Verificar se têm dados geográficos
            alertas_com_geo = 0
            total_poligonos = 0
            area_total = 0.0
            
            for i, alerta in enumerate(alertas):
                dados_geo = alerta.get('dados_geograficos')
                if dados_geo:
                    alertas_com_geo += 1
                    num_pol = dados_geo.get('total_poligonos', 0)
                    area = dados_geo.get('area_total_km2', 0)
                    total_poligonos += num_pol
                    area_total += area
                    
                    print(f"  🗺️  Alerta {i+1}: {num_pol} polígonos, {area:.1f} km²")
                    print(f"       📝 {alerta.get('event', 'N/A')}")
                else:
                    print(f"  ❌ Alerta {i+1}: SEM dados geográficos")
                    print(f"       📝 {alerta.get('event', 'N/A')}")
            
            print(f"\n📈 RESUMO {estado}:")
            print(f"   🗺️  Alertas com geo: {alertas_com_geo}/{len(alertas)}")
            print(f"   🔢 Total polígonos: {total_poligonos}")
            print(f"   📐 Área total: {area_total:.1f} km²")
            
            # Simular valor do sensor
            valor_sensor = total_poligonos
            print(f"   🎯 VALOR SENSOR: {valor_sensor}")
            
            if valor_sensor == 0:
                print("   🚨 PROBLEMA: Sensor retornaria 0!")
            else:
                print("   ✅ Sensor funcionando!")
                
        except Exception as e:
            print(f"❌ Erro ao processar {estado}: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 TESTE CONCLUÍDO")

if __name__ == "__main__":
    main()