import logging
from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from .const import DOMAIN, CONF_DOORS
from .device import controller_device_info

async def async_setup_entry(hass, entry, async_add_entities):
    client = hass.data[DOMAIN][entry.entry_id]
    data = entry.options.get(CONF_DOORS, {})
    entities = [ICTDoor(client, int(k), v) for k, v in data.items()]
    async_add_entities(entities)

class ICTDoor(LockEntity):
    def __init__(self, client, door_id, name):
        self._client = client
        self._door_id = door_id
        self._attr_name = name
        self._attr_unique_id = f"ict_door_{door_id}"
        self._attr_device_info = controller_device_info()
        self._is_locked = True
        self._is_open = False
        self._attr_extra_state_attributes = {}
        self._update_door_state()

    async def async_added_to_hass(self):
        self._client.register_callback(self._handle_update)

    @callback
    def _handle_update(self, update):
        if update["type"] == "door" and update["id"] == self._door_id:
            self._is_locked = update["locked"]
            self._is_open = update["open"]
            self._update_door_state()
            self.async_write_ha_state()

    def _update_door_state(self):
        if self._is_open:
            door_state = "Open"
            self._attr_icon = "mdi:door-open"
        elif self._is_locked:
            door_state = "Locked"
            self._attr_icon = "mdi:door-closed-lock"
        else:
            door_state = "Closed"
            self._attr_icon = "mdi:door-closed"

        self._attr_extra_state_attributes["door_state"] = door_state

    @property
    def is_locked(self):
        return self._is_locked

    @property
    def is_open(self):
        return self._is_open

    async def async_lock(self, **kwargs):
        await self._client.send_command(0x01, 0x00, self._door_id)

    async def async_unlock(self, **kwargs):
        await self._client.send_command(0x01, 0x01, self._door_id)
