/**
 * Plugin para ha-map-card que desenha polígonos dos alertas INMET
 * Mostra as áreas de alerta meteorológico usando coordenadas reais dos alertas
 * 
 * @param L Leaflet library
 * @param pluginBase Base plugin class
 * @param Logger Logger utility
 */
export default function(L, pluginBase, Logger) {
  return class INMETPolygonsPlugin extends pluginBase {
    constructor(map, name, options = {}) {
      super(map, name, options);
      
      console.log('🏗️ [INMET] Construindo plugin:', { name, hasMap: !!map, options });
      
      // Flags de controle
      this._isUpdating = false;
      this._hasLoggedNoHass = false;
      
      // Configurações padrão
      this.entityPrefix = options.entityPrefix || 'sensor.inmet_alertas_mapa_';
      this.updateInterval = options.updateInterval || 60000; // 1 minuto
      this.showLabels = options.showLabels !== false; // true por padrão
      this.autoFocus = options.autoFocus !== false; // true por padrão
      
      // Cores por severidade (cores oficiais INMET)
      this.severityColors = {
        'Grande Perigo': options.colors?.grandePerigo || '#F80703',  // Vermelho oficial
        'Perigo': options.colors?.perigo || '#FF8C00',               // Laranja oficial
        'Perigo Potencial': options.colors?.perigoPotencial || '#FFFF00' // Amarelo oficial
      };
      
      // Opacidades (50% para transparência ideal)
      this.fillOpacity = options.fillOpacity || 0.5;      // 50% transparência no preenchimento
      this.strokeOpacity = options.strokeOpacity || 0.8;  // 80% na borda (mais visível)
      this.strokeWeight = options.strokeWeight || 2;
      
      // Estados para monitorar (mapeamento nome completo -> sigla)
      this.stateMapping = {
        'acre': 'ac', 'alagoas': 'al', 'amapa': 'ap', 'amazonas': 'am',
        'bahia': 'ba', 'ceara': 'ce', 'distrito_federal': 'df', 'espirito_santo': 'es',
        'goias': 'go', 'maranhao': 'ma', 'mato_grosso': 'mt', 'mato_grosso_do_sul': 'ms',
        'minas_gerais': 'mg', 'para': 'pa', 'paraiba': 'pb', 'parana': 'pr',
        'pernambuco': 'pe', 'piaui': 'pi', 'rio_de_janeiro': 'rj', 'rio_grande_do_norte': 'rn',
        'rio_grande_do_sul': 'rs', 'rondonia': 'ro', 'roraima': 'rr', 'santa_catarina': 'sc',
        'sao_paulo': 'sp', 'sergipe': 'se', 'tocantins': 'to'
      };
      
      // Estados configurados pelo usuário - com fallback para RJ (que tem dados)
      this.states = options.states || ['rio_de_janeiro'];
      console.log('📍 [INMET] Estados configurados:', this.states);
      
      // Armazenar layers dos polígonos
      this.polygonLayerGroup = L.layerGroup().addTo(this.map);
      this.intervalId = null;
      
      Logger.debug(`[INMETPolygonsPlugin] Inicializado plugin: ${this.name} com ${this.states.length} estados`);
    }

    async init() {
      console.log('🚀 [INMET] Inicializando plugin...');
      
      // Aguardar Home Assistant estar disponível antes de configurar intervalo
      this.waitForHomeAssistant();
    }
    
    async waitForHomeAssistant() {
      console.log('⏳ [INMET] Aguardando Home Assistant...');
      
      let attempts = 0;
      const maxAttempts = 30; // 1 minuto tentando
      
      const checkHass = () => {
        attempts++;
        
        // Tentar múltiplas formas de acessar o Home Assistant
        let hass = null;
        
        // Método 1: Via plugin
        if (this.hass && this.hass.states) {
          hass = this.hass;
          console.log('✅ [INMET] HA encontrado via plugin.hass');
        }
        
        // Método 2: Via window
        else if (window.hass && window.hass.states) {
          hass = window.hass;
          console.log('✅ [INMET] HA encontrado via window.hass');
        }
        
        // Método 3: Via document (algumas versões)
        else if (typeof document !== 'undefined') {
          const homeAssistant = document.querySelector('home-assistant');
          if (homeAssistant && homeAssistant.hass && homeAssistant.hass.states) {
            hass = homeAssistant.hass;
            console.log('✅ [INMET] HA encontrado via home-assistant element');
          }
        }
        
        // Método 4: Via window.__HASS__ (backup)
        else if (window.__HASS__ && window.__HASS__.states) {
          hass = window.__HASS__;
          console.log('✅ [INMET] HA encontrado via window.__HASS__');
        }
        
        if (hass) {
          // Armazenar referência para uso futuro
          this._hassRef = hass;
          
          console.log('✅ [INMET] Home Assistant disponível! Testando sensores...');
          
          // Testar se temos o sensor RJ
          const rjSensor = hass.states['sensor.inmet_alertas_mapa_rj'];
          if (rjSensor) {
            console.log('📊 [INMET] Sensor RJ encontrado:', rjSensor.state, 'polígonos');
            if (rjSensor.attributes.camadas_por_severidade) {
              console.log('🗺️ [INMET] Dados geográficos disponíveis');
            }
          } else {
            console.warn('⚠️ [INMET] Sensor RJ não encontrado. Sensores disponíveis:', 
              Object.keys(hass.states).filter(id => id.startsWith('sensor.inmet')));
          }
          
          // Primeira atualização
          this.update();
          
          // Configurar intervalo de atualização
          if (!this.intervalId) {
            this.intervalId = setInterval(() => {
              this.update();
            }, this.updateInterval);
            console.log(`🔄 [INMET] Intervalo configurado: ${this.updateInterval}ms`);
          }
          
        } else if (attempts < maxAttempts) {
          // Tentar novamente em 2 segundos
          console.log(`⏳ [INMET] Tentativa ${attempts}/${maxAttempts} - Aguardando HA...`);
          setTimeout(checkHass, 2000);
        } else {
          console.error('❌ [INMET] Timeout: Home Assistant não foi encontrado após 1 minuto');
        }
      };
      
      checkHass();
    }

    async renderMap() {
      Logger.debug(`[INMETPolygonsPlugin] Renderizando mapa inicial para plugin: ${this.name}`);
      
      // Verificar se temos acesso ao hass
      if (!window.hass) {
        Logger.error('[INMETPolygonsPlugin] Home Assistant não disponível');
        return;
      }
      
      // Renderização inicial
      await this.updatePolygons();
    }

    async update() {
      // Evitar múltiplas chamadas simultâneas
      if (this._isUpdating) {
        return;
      }
      
      this._isUpdating = true;
      
      try {
        // Usar a referência armazenada ou tentar encontrar HA
        const hass = this._hassRef || this.hass || window.hass;
        if (!hass || !hass.states) {
          // Não fazer logs repetitivos - só avisar uma vez
          if (!this._hasLoggedNoHass) {
            console.warn('⚠️ [INMET] Aguardando Home Assistant...');
            console.log('🔍 [INMET] Referencias:', {
              hasHassRef: !!this._hassRef,
              hasThisHass: !!this.hass,
              hasWindowHass: !!window.hass
            });
            this._hasLoggedNoHass = true;
          }
          return;
        }
        
        // Reset do flag se conseguimos conectar
        this._hasLoggedNoHass = false;
        
        console.log('🔄 [INMET] Atualizando polígonos...');
        
        await this.updatePolygons();
        
      } catch (error) {
        console.error('❌ [INMET] Erro no update:', error);
      } finally {
        // Liberar após pequeno delay
        setTimeout(() => {
          this._isUpdating = false;
        }, 500);
      }
      
      // Usar window.hass se this.hass não estiver disponível
      const hass = this.hass || window.hass;
      
      // Debug: listar sensores INMET
      if (hass && hass.states) {
        const allInmetSensors = Object.keys(hass.states).filter(id => id.startsWith('sensor.inmet'));
        console.log('🔍 [INMET] Sensores encontrados:', {
          total: allInmetSensors.length,
          sensores: allInmetSensors
        });
        
        const mapSensors = allInmetSensors.filter(id => id.includes('_mapa_'));
        console.log('🗺️ [INMET] Sensores de mapa:', mapSensors);
        
        mapSensors.forEach(id => {
          const sensor = hass.states[id];
          console.log(`   📊 ${id}:`, {
            state: sensor.state,
            hasCamadas: !!sensor.attributes.camadas_por_severidade,
            camadas: sensor.attributes.camadas_por_severidade ? Object.keys(sensor.attributes.camadas_por_severidade) : []
          });
        });
      }
      
      await this.updatePolygons();
    }

    async updatePolygons() {
      try {
        console.log('🔄 [INMET] Iniciando updatePolygons...');
        
        // Limpar polígonos existentes
        this.clearPolygons();
        
        // Usar a referência armazenada ou tentar encontrar HA
        const hass = this._hassRef || this.hass || window.hass;
        
        if (!hass || !hass.states) {
          console.error('❌ [INMET] Home Assistant states não disponível');
          console.log('🔍 [INMET] Debug - Referencias disponíveis:', {
            hasHassRef: !!this._hassRef,
            hasThisHass: !!this.hass,
            hasWindowHass: !!window.hass
          });
          return;
        }
        
        console.log('✅ [INMET] Usando Home Assistant para buscar dados...');
        
        console.log(`🔄 [INMET] Processando ${this.states.length} estados configurados:`, this.states);
        
        // DEBUG: Verificar se temos sensores de MG e ES também
        const allInmetSensors = Object.keys(hass.states).filter(id => id.startsWith('sensor.inmet_alertas_mapa_'));
        console.log('🔍 [DEBUG] Todos os sensores de mapa disponíveis:', allInmetSensors);
        
        // Verificar especificamente MG e ES
        const mgSensor = hass.states['sensor.inmet_alertas_mapa_mg'];
        const esSensor = hass.states['sensor.inmet_alertas_mapa_es'];
        
        if (mgSensor) {
          console.log('📊 [DEBUG] Sensor MG:', mgSensor.state, 'polígonos', mgSensor.attributes.camadas_por_severidade ? 'COM dados geo' : 'SEM dados geo');
        }
        
        if (esSensor) {
          console.log('📊 [DEBUG] Sensor ES:', esSensor.state, 'polígonos', esSensor.attributes.camadas_por_severidade ? 'COM dados geo' : 'SEM dados geo');
        }
        
        let totalPolygons = 0;
        
        // Processar cada estado configurado
        for (const estadoNome of this.states) {
          const estadoSigla = this.stateMapping[estadoNome];
          if (!estadoSigla) {
            Logger.warn(`[INMETPolygonsPlugin] Estado não mapeado: ${estadoNome}`);
            continue;
          }
          
          const entityId = `${this.entityPrefix}${estadoSigla}`;
          const entity = hass.states[entityId];  // Usar a referência correta
          
          if (!entity) {
            console.log(`🔍 [INMET] Entidade não encontrada: ${entityId}`);
            continue;
          }
          
          console.log(`📊 [INMET] Processando: ${entityId} - ${entity.state} polígonos`);
          
          // DEBUG: Mostrar coordenadas do polígono para análise
          if (entity.attributes.camadas_por_severidade) {
            for (const [severidade, dados] of Object.entries(entity.attributes.camadas_por_severidade)) {
              console.log(`🔍 [DEBUG] ${estadoNome} - ${severidade}:`, dados.total_poligonos, 'polígonos');
              dados.poligonos.forEach((pol, idx) => {
                const coords = pol.coordenadas;
                if (coords && coords.length > 0) {
                  const minLat = Math.min(...coords.map(c => c[0]));
                  const maxLat = Math.max(...coords.map(c => c[0]));
                  const minLon = Math.min(...coords.map(c => c[1])); 
                  const maxLon = Math.max(...coords.map(c => c[1]));
                  console.log(`   📐 Polígono ${idx}: Lat ${minLat.toFixed(2)} a ${maxLat.toFixed(2)}, Lon ${minLon.toFixed(2)} a ${maxLon.toFixed(2)}`);
                  console.log(`   🎯 Centro: [${pol.centro}], Área: ${pol.area_km2} km²`);
                  console.log(`   🏛️ Municípios: ${pol.municipios ? pol.municipios.slice(0,3).join(', ') : 'N/A'}`);
                }
              });
            }
          }
          
          // Processar polígonos desta entidade
          const polygonsAdded = await this.processStateEntity(estadoNome, estadoSigla, entity);
          totalPolygons += polygonsAdded;
          
          console.log(`✅ [INMET] ${estadoNome}: ${polygonsAdded} polígonos adicionados`);
        }
        
        Logger.debug(`[INMETPolygonsPlugin] Atualização completa - ${totalPolygons} polígonos adicionados ao mapa`);
        
        // AutoFocus: centralizar mapa no estado se configurado
        if (this.autoFocus && totalPolygons > 0) {
          this._autoFocusMap();
        }
        
      } catch (error) {
        Logger.error(`[INMETPolygonsPlugin] Erro na atualização:`, error);
      }
    }

    _autoFocusMap() {
      try {
        const hass = this._hassRef || this.hass || window.hass;
        if (!hass || !hass.states) return;

        let bestEntity = null;
        let bestSigla = null;

        // Procurar o primeiro estado configurado com dados geográficos
        for (const estadoNome of this.states) {
          const estadoSigla = this.stateMapping[estadoNome];
          if (!estadoSigla) continue;

          const entityId = `${this.entityPrefix}${estadoSigla}`;
          const entity = hass.states[entityId];
          if (!entity || !entity.attributes) continue;

          const attrs = entity.attributes;

          // Usar centro_geografico e zoom_recomendado se disponíveis
          if (attrs.centro_geografico) {
            bestEntity = entity;
            bestSigla = estadoSigla.toUpperCase();
            break;
          }
        }

        if (!bestEntity) return;

        const attrs = bestEntity.attributes;
        let center = attrs.centro_geografico;
        let zoom = attrs.zoom_recomendado;

        // Fallback: calcular centro da bounding box
        if (!center && attrs.bounding_box) {
          const bb = attrs.bounding_box;
          center = [
            (bb.min_lat + bb.max_lat) / 2,
            (bb.min_lon + bb.max_lon) / 2
          ];
        }

        if (center && Array.isArray(center) && center.length >= 2) {
          console.log(`📍 [INMET] AutoFocus: centralizando em [${center[0].toFixed(4)}, ${center[1].toFixed(4)}] zoom ${zoom || 8}`);
          this.map.setView(center, zoom || 8);
        }
      } catch (error) {
        console.error('❌ [INMET] Erro no autoFocus:', error);
      }
    }

    async processStateEntity(estadoNome, estadoSigla, entity) {
      try {
        const attributes = entity.attributes || {};
        let polygonCount = 0;
        
        // Verificar se há dados geográficos (camadas por severidade)
        if (!attributes.camadas_por_severidade) {
          Logger.debug(`[INMETPolygonsPlugin] Sem dados geográficos para ${estadoNome} (${estadoSigla})`);
          return polygonCount;
        }
        
        const camadasData = attributes.camadas_por_severidade;
        const camadasDisponiveis = Object.keys(camadasData);
        
        Logger.debug(`[INMETPolygonsPlugin] Processando ${estadoNome} - Camadas disponíveis:`, camadasDisponiveis);
        
        // Processar cada nível de severidade em ordem de prioridade
        const severidadesOrdem = ['Grande Perigo', 'Perigo', 'Perigo Potencial'];
        
        for (const severity of severidadesOrdem) {
          const camadaInfo = camadasData[severity];
          
          if (camadaInfo && camadaInfo.poligonos && camadaInfo.poligonos.length > 0) {
            Logger.debug(`[INMETPolygonsPlugin] Criando camada ${severity} para ${estadoNome} com ${camadaInfo.poligonos.length} polígonos`);
            
            const polygonsAdded = this.createPolygonLayer(estadoNome, estadoSigla, severity, camadaInfo.poligonos);
            polygonCount += polygonsAdded;
          }
        }
        
        if (polygonCount > 0) {
          Logger.debug(`[INMETPolygonsPlugin] Estado ${estadoNome}: ${polygonCount} polígonos adicionados`);
        }
        
        return polygonCount;
        
      } catch (error) {
        Logger.error(`[INMETPolygonsPlugin] Erro processando ${estadoNome}:`, error);
        return 0;
      }
    }

    createPolygonLayer(estadoNome, estadoSigla, severity, polygons) {
      try {
        const color = this.severityColors[severity];
        if (!color) {
          Logger.warn(`[INMETPolygonsPlugin] Cor não definida para severidade: ${severity}`);
          return 0;
        }
        
        let polygonsAdded = 0;
        
        // Processar cada polígono individualmente
        polygons.forEach((polygon, index) => {
          if (!polygon.coordenadas || polygon.coordenadas.length === 0) {
            Logger.debug(`[INMETPolygonsPlugin] Polígono ${index} sem coordenadas válidas`);
            return;
          }
          
          try {
            // Validar formato das coordenadas
            if (!Array.isArray(polygon.coordenadas) || polygon.coordenadas.length < 3) {
              Logger.debug(`[INMETPolygonsPlugin] Coordenadas insuficientes para polígono ${index}`);
              return;
            }
            
            // Configurar opções de estilo (sempre aplicar transparência)
            const polygonOptions = {
              color: color,
              weight: this.strokeWeight,
              opacity: this.strokeOpacity,
              fillColor: color,
              fillOpacity: this.fillOpacity,  // Garantir 50% transparência
              interactive: true,
              bubblingMouseEvents: false
            };
            
            // Criar polígono Leaflet com opções explícitas
            const leafletPolygon = L.polygon(polygon.coordenadas, polygonOptions);
            
            // Forçar aplicação das opções de estilo (correção para transparência)
            leafletPolygon.setStyle({
              fillOpacity: this.fillOpacity,
              opacity: this.strokeOpacity
            });
            
            // Adicionar popup com informações
            const popupContent = this.createPopupContent(estadoNome, estadoSigla, severity, polygon, index);
            leafletPolygon.bindPopup(popupContent);
            
            // Adicionar tooltip se habilitado
            if (this.showLabels) {
              const tooltipContent = `${severity} - ${estadoNome}`;
              leafletPolygon.bindTooltip(tooltipContent, {
                permanent: false,
                direction: 'center',
                className: 'inmet-polygon-tooltip'
              });
            }
            
            // Adicionar ao grupo principal
            this.polygonLayerGroup.addLayer(leafletPolygon);
            polygonsAdded++;
            
            // Debug da transparência aplicada
            console.log(`🎨 [INMET] Polígono ${index} - Transparência: fillOpacity=${leafletPolygon.options.fillOpacity}, opacity=${leafletPolygon.options.opacity}`);
            
            Logger.debug(`[INMETPolygonsPlugin] Polígono ${index} adicionado: ${severity} em ${estadoNome} (${polygon.area_km2} km²)`);
            
          } catch (polygonError) {
            Logger.error(`[INMETPolygonsPlugin] Erro criando polígono ${index} para ${estadoNome}/${severity}:`, polygonError);
          }
        });
        
        if (polygonsAdded > 0) {
          Logger.debug(`[INMETPolygonsPlugin] Camada ${severity} em ${estadoNome}: ${polygonsAdded} polígonos criados`);
        }
        
        return polygonsAdded;
        
      } catch (error) {
        Logger.error(`[INMETPolygonsPlugin] Erro criando camada para ${estadoNome}/${severity}:`, error);
        return 0;
      }
    }

    createPopupContent(estadoNome, estadoSigla, severity, polygon, index) {
      const estadoFormatado = estadoNome.charAt(0).toUpperCase() + estadoNome.slice(1).replace(/_/g, ' ');
      
      // Ícone por severidade
      const icons = {
        'Grande Perigo': '🔴',
        'Perigo': '🟠', 
        'Perigo Potencial': '🟡'
      };
      
      const icon = icons[severity] || '⚠️';
      
      let content = `
        <div class="inmet-popup" style="min-width: 250px;">
          <h3 style="margin: 0 0 10px 0; color: ${this.severityColors[severity]};">
            ${icon} ${severity}
          </h3>
          <div style="font-size: 13px; line-height: 1.4;">
            <p style="margin: 5px 0;"><strong>Estado:</strong> ${estadoFormatado} (${estadoSigla.toUpperCase()})</p>
            <p style="margin: 5px 0;"><strong>Evento:</strong> ${polygon.evento || 'Alerta Meteorológico'}</p>
            <p style="margin: 5px 0;"><strong>Área:</strong> ${polygon.area_km2?.toFixed(1) || 'N/A'} km²</p>
      `;
      
      if (polygon.centro && Array.isArray(polygon.centro) && polygon.centro.length >= 2) {
        content += `<p style="margin: 5px 0;"><strong>Centro:</strong> ${polygon.centro[0].toFixed(4)}, ${polygon.centro[1].toFixed(4)}</p>`;
      }
      
      if (polygon.inicio && polygon.fim) {
        content += `
          <p style="margin: 5px 0;"><strong>Início:</strong> ${polygon.inicio}</p>
          <p style="margin: 5px 0;"><strong>Fim:</strong> ${polygon.fim}</p>
        `;
      }
      
      if (polygon.descricao) {
        const shortDesc = polygon.descricao.length > 120 ? 
          polygon.descricao.substring(0, 120) + '...' : 
          polygon.descricao;
        content += `<p style="margin: 5px 0;"><strong>Descrição:</strong> ${shortDesc}</p>`;
      }
      
      if (polygon.municipios && Array.isArray(polygon.municipios) && polygon.municipios.length > 0) {
        const municipiosText = polygon.municipios.length > 3 ? 
          polygon.municipios.slice(0, 3).join(', ') + ` e mais ${polygon.municipios.length - 3}` :
          polygon.municipios.join(', ');
        content += `<p style="margin: 5px 0;"><strong>Municípios:</strong> ${municipiosText}</p>`;
      }
      
      content += `
          </div>
          <div style="margin-top: 10px; padding-top: 8px; border-top: 1px solid #eee; font-size: 11px; color: #666;">
            INMET - Instituto Nacional de Meteorologia
          </div>
        </div>`;
      
      return content;
    }

    clearPolygons() {
      try {
        if (this.polygonLayerGroup) {
          // Fechar popups antes de limpar
          this.polygonLayerGroup.eachLayer((layer) => {
            if (layer.getPopup) {
              layer.closePopup();
            }
            if (layer.getTooltip) {
              layer.unbindTooltip();
            }
          });
          
          // Limpar todas as camadas
          this.polygonLayerGroup.clearLayers();
          console.log('🧹 [INMET] Polígonos limpos - mantendo transparência');
        }
      } catch (error) {
        console.error('❌ [INMET] Erro limpando polígonos:', error);
      }
    }
    
    destroy() {
      try {
        console.log('🗑️ [INMET] Destruindo plugin...');
        
        // Limpar intervalos
        if (this.intervalId) {
          clearInterval(this.intervalId);
          this.intervalId = null;
          console.log('⏰ [INMET] Intervalo de atualização removido');
        }
        
        // Limpar todos os polígonos
        this.clearPolygons();
        
        // Remover grupo de camadas do mapa
        if (this.polygonLayerGroup && this.map) {
          this.map.removeLayer(this.polygonLayerGroup);
          console.log('📍 [INMET] LayerGroup removido do mapa');
        }
        
        // Limpar referências
        this.polygonLayerGroup = null;
        this.map = null;
        this._hassRef = null;
        this.hass = null;
        
        console.log('✅ [INMET] Plugin destruído com sucesso');
      } catch (error) {
        console.error('❌ [INMET] Erro destruindo plugin:', error);
      }
    }
  };
}

// Registrar o plugin no sistema ha-map-card
if (typeof customElements !== 'undefined' && window.customCards) {
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: 'inmet-polygons-plugin',
    name: 'INMET Polygons Plugin',
    description: 'Plugin para exibir polígonos de alertas meteorológicos do INMET',
    version: '1.0.0'
  });
}

console.log('📦 INMET Polygons Plugin loaded successfully');