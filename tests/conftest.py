"""Fixtures compartilhadas para testes."""
import sys
import types
import pytest

# Mock módulos do Home Assistant antes de qualquer import da integração
_MOCK_HA_MODULES = {
    "homeassistant": types.ModuleType("homeassistant"),
    "homeassistant.helpers": types.ModuleType("homeassistant.helpers"),
    "homeassistant.helpers.config_validation": types.ModuleType("homeassistant.helpers.config_validation"),
    "homeassistant.core": types.ModuleType("homeassistant.core"),
    "homeassistant.const": types.ModuleType("homeassistant.const"),
    "homeassistant.config_entries": types.ModuleType("homeassistant.config_entries"),
    "homeassistant.util": types.ModuleType("homeassistant.util"),
    "homeassistant.util.dt": types.ModuleType("homeassistant.util.dt"),
    "voluptuous": types.ModuleType("voluptuous"),
}

# Atributos mínimos necessários
_MOCK_HA_MODULES["homeassistant.helpers.config_validation"].config_entry_only_config_schema = lambda d: d
_MOCK_HA_MODULES["homeassistant.core"].HomeAssistant = object
_MOCK_HA_MODULES["homeassistant.config_entries"].ConfigEntry = object
_MOCK_HA_MODULES["homeassistant.const"].Platform = type("Platform", (), {"SENSOR": "sensor"})
_MOCK_HA_MODULES["voluptuous"].Schema = lambda x: x
_MOCK_HA_MODULES["voluptuous"].Optional = lambda x, default=None: x

for mod_name, mod in _MOCK_HA_MODULES.items():
    sys.modules[mod_name] = mod

CAP_XML_SIMPLES = '''<?xml version="1.0" encoding="UTF-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>55025</identifier>
  <info>
    <event>Tempestade</event>
    <severity>Moderate</severity>
    <onset>2026-07-19T10:00:00-03:00</onset>
    <expires>2026-07-19T18:00:00-03:00</expires>
    <parameter>
      <valueName>Municipios</valueName>
      <value>Rio de Janeiro - RJ (3304557), Niterói - RJ (3303302)</value>
    </parameter>
  </info>
</alert>'''

CAP_XML_MICRORREGIAO = '''<?xml version="1.0" encoding="UTF-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>55026</identifier>
  <info>
    <event>Baixa Umidade</event>
    <severity>Minor</severity>
    <parameter>
      <valueName>Municipios</valueName>
      <value>Metropolitana do Rio de Janeiro</value>
    </parameter>
  </info>
</alert>'''

CAP_XML_SEM_MUNICIPIOS = '''<?xml version="1.0" encoding="UTF-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>55027</identifier>
  <info>
    <event>Onda de Calor</event>
    <severity>Severe</severity>
  </info>
</alert>'''


@pytest.fixture
def cap_simples():
    return CAP_XML_SIMPLES


@pytest.fixture
def cap_microrregiao():
    return CAP_XML_MICRORREGIAO


@pytest.fixture
def cap_sem_municipios():
    return CAP_XML_SEM_MUNICIPIOS
