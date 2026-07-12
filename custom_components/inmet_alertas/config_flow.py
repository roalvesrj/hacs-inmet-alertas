"""Config flow para INMET Alertas."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from typing import Any

_LOGGER = logging.getLogger(__name__)

DOMAIN = "inmet_alertas"

ESTADOS_BRASILEIROS = {
    "AC": "Acre",
    "AL": "Alagoas", 
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins"
}

class InmetAlertasConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for INMET Alertas."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            estado = user_input.get("estado", "").upper()
            
            # Verificar se já existe uma entrada configurada
            await self.async_set_unique_id(f"{DOMAIN}_{estado}")
            self._abort_if_unique_id_configured()
            
            if estado not in ESTADOS_BRASILEIROS:
                errors["estado"] = "invalid_state"
            else:
                return self.async_create_entry(
                    title=f"INMET Alertas - {ESTADOS_BRASILEIROS[estado]}",
                    data={
                        "estado": estado,
                        "notificacoes_perigo": user_input.get("notificacoes_perigo", True),
                        "update_interval": user_input.get("update_interval", 30)
                    }
                )

        # Criar lista de opções para o dropdown
        estado_options = {k: f"{k} - {v}" for k, v in ESTADOS_BRASILEIROS.items()}

        data_schema = vol.Schema({
            vol.Required("estado", default="SP"): vol.In(estado_options),
            vol.Optional("notificacoes_perigo", default=True): bool,
            vol.Optional("update_interval", default=30): vol.All(
                vol.Coerce(int), vol.Range(min=5, max=120)
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return InmetAlertasOptionsFlow()


class InmetAlertasOptionsFlow(config_entries.OptionsFlow):
    """Handle INMET Alertas options."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    "notificacoes_perigo",
                    default=self.config_entry.options.get("notificacoes_perigo", True)
                ): bool,
                vol.Optional(
                    "update_interval",
                    default=self.config_entry.options.get("update_interval", 30)
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=120)),
            })
        )
