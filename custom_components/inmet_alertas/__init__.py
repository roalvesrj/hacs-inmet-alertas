"""Integração INMET Alertas para Home Assistant."""
import logging
import os
from homeassistant.helpers import config_validation as cv
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
_LOGGER = logging.getLogger(__name__)

DOMAIN = "inmet_alertas"
PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Configuração inicial da integração."""
    hass.data.setdefault(DOMAIN, {"coordinators": {}})

    # Registrar serviço de atualização (único, não por entry)
    async def handle_atualizar_alertas(call):
        estado_param = call.data.get("estado")
        for entry_id, coord in hass.data[DOMAIN].get("coordinators", {}).items():
            if estado_param is None or estado_param == coord.estado:
                await coord.async_request_refresh()

    hass.services.async_register(
        DOMAIN, "atualizar_alertas", handle_atualizar_alertas
    )

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configuração ao adicionar a integração pela interface."""
    
    hass.data.setdefault(DOMAIN, {"coordinators": {}})
    hass.data[DOMAIN].setdefault("coordinators", {})

    # Registrar arquivos estáticos para o plugin ha-map-card.
    # O HACS já registra automaticamente /hacsfiles/<domain> → www/ para
    # integrações instaladas via HACS. Tentamos registrar apenas uma vez
    # (flag em hass.data) para evitar o erro "Duplicate static resource"
    # que ocorre a cada reload da config entry.
    _static_key = f"{DOMAIN}_static_registered"
    if not hass.data[DOMAIN].get(_static_key):
        try:
            plugin_path = hass.config.path("custom_components", DOMAIN, "www")
            if os.path.exists(plugin_path):
                plugin_url = f"/hacsfiles/{DOMAIN}"
                hass.http.app.router.add_static(
                    plugin_url,
                    plugin_path,
                    name=f"{DOMAIN}_static"
                )
                hass.data[DOMAIN][_static_key] = True
                _LOGGER.info(f"✅ Plugin INMET disponível em: {plugin_url}/plugin_inmet_polygons.js")
            else:
                _LOGGER.warning(f"❌ Pasta do plugin não encontrada: {plugin_path}")
        except Exception as e:
            # Rota já registrada pelo HACS — não é erro, apenas log de debug.
            _LOGGER.debug(f"Recurso estático já registrado (provavelmente pelo HACS): {e}")
            hass.data[DOMAIN][_static_key] = True
    else:
        _LOGGER.debug("Recurso estático INMET já registrado anteriormente, ignorando.")
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Configurar listener para opções
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove a integração."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].get("coordinators", {}).pop(entry.entry_id, None)
    
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recarrega a entrada quando as opções são atualizadas."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
