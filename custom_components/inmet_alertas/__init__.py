from homeassistant.core import HomeAssistant

DOMAIN = "inmet_alertas"

async def async_setup(hass: HomeAssistant, config: dict):
    """Configuração inicial da integração."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry):
    """Configuração ao adicionar a integração pela interface."""
    hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, "sensor"))
    return True

async def async_unload_entry(hass: HomeAssistant, entry):
    """Remove a integração."""
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    return True
