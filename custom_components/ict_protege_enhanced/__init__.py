import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.loader import async_get_integration

from .const import (
    CONF_AREAS,
    CONF_DOORS,
    CONF_HOST,
    CONF_INPUTS,
    CONF_OUTPUTS,
    CONF_PASSWORD,
    CONF_PORT,
    DOMAIN,
)
from .ict_library import ICTClient

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["lock", "binary_sensor", "switch", "alarm_control_panel", "select"]
FRONTEND_URL = f"/{DOMAIN}/protege-picker.js"
FRONTEND_FILE = Path(__file__).parent / "frontend" / "protege-picker.js"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up integration-level frontend resources."""
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                FRONTEND_URL,
                str(FRONTEND_FILE),
                cache_headers=False,
            )
        ]
    )

    integration = await async_get_integration(hass, DOMAIN)
    add_extra_js_url(hass, f"{FRONTEND_URL}?v={integration.version}")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    client = ICTClient(
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data.get(CONF_PASSWORD),
    )

    def get_ids(key):
        data = entry.options.get(key, {})
        if isinstance(data, dict):
            return [int(k) for k in data.keys()]
        return []

    door_ids = get_ids(CONF_DOORS)
    area_ids = get_ids(CONF_AREAS)
    input_ids = get_ids(CONF_INPUTS)
    output_ids = get_ids(CONF_OUTPUTS)

    client.set_configuration(
        doors=door_ids,
        areas=area_ids,
        inputs=input_ids,
        outputs=output_ids,
    )

    await client.start()
    hass.data[DOMAIN][entry.entry_id] = client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Remove orphaned entities no longer present in the integration config.
    ent_reg = er.async_get(hass)
    valid_unique_ids = set()

    for door_id in door_ids:
        valid_unique_ids.add(f"ict_door_{door_id}")
        valid_unique_ids.add(f"ict_door_contact_{door_id}")
    for area_id in area_ids:
        valid_unique_ids.add(f"ict_area_{area_id}")
    for input_id in input_ids:
        valid_unique_ids.add(f"ict_input_{input_id}")
        valid_unique_ids.add(f"ict_input_bypass_{input_id}")
        valid_unique_ids.add(f"ict_trouble_{input_id}")
    for output_id in output_ids:
        valid_unique_ids.add(f"ict_output_{output_id}")

    for entity in list(er.async_entries_for_config_entry(ent_reg, entry.entry_id)):
        if entity.unique_id not in valid_unique_ids:
            _LOGGER.warning("Removing orphaned entity: %s", entity.entity_id)
            ent_reg.async_remove(entity.entity_id)

    # All entities now belong to one physical Home Assistant device. Remove
    # legacy per-door/per-area/per-input/per-output device shells left by older
    # versions after the entities have migrated to ICT Protege Controller.
    dev_reg = dr.async_get(hass)
    controller_identifier = (DOMAIN, "ict_controller")

    for device in list(dr.async_entries_for_config_entry(dev_reg, entry.entry_id)):
        if controller_identifier not in device.identifiers:
            _LOGGER.info("Removing legacy Protege device shell: %s", device.name)
            dev_reg.async_remove_device(device.id)

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = hass.data[DOMAIN][entry.entry_id]
    await client.stop()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
