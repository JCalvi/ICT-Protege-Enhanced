import logging
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    CodeFormat,
)
from homeassistant.core import callback
from .const import (
    DOMAIN, CONF_AREAS,
    CONF_ENABLE_AWAY, CONF_ENABLE_STAY, CONF_ENABLE_NIGHT, CONF_ENABLE_BYPASS
)
from .device import controller_device_info

STATE_ALARM_DISARMED = "disarmed"
STATE_ALARM_ARMED_HOME = "armed_home"
STATE_ALARM_ARMED_AWAY = "armed_away"
STATE_ALARM_ARMED_NIGHT = "armed_night"
STATE_ALARM_TRIGGERED = "triggered"
STATE_ALARM_ARMING = "arming"

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    client = hass.data[DOMAIN][entry.entry_id]
    data = entry.options.get(CONF_AREAS, {})
    enable_away = entry.options.get(CONF_ENABLE_AWAY, True)
    enable_stay = entry.options.get(CONF_ENABLE_STAY, True)
    enable_night = entry.options.get(CONF_ENABLE_NIGHT, True)
    enable_bypass = entry.options.get(CONF_ENABLE_BYPASS, False)

    async_add_entities([
        ICTArea(client, int(k), v, enable_away, enable_stay, enable_night, enable_bypass)
        for k, v in data.items()
    ])

class ICTArea(AlarmControlPanelEntity):
    def __init__(self, client, area_id, name, enable_away, enable_stay, enable_night, enable_bypass):
        self._client = client
        self._area_id = area_id
        self._attr_name = name
        self._attr_unique_id = f"ict_area_{area_id}"
        self._attr_device_info = controller_device_info()
        self._attr_code_format = CodeFormat.NUMBER
        self._state = None

        features = AlarmControlPanelEntityFeature(0)
        if enable_away:
            features |= AlarmControlPanelEntityFeature.ARM_AWAY
        if enable_stay:
            features |= AlarmControlPanelEntityFeature.ARM_HOME
        if enable_night:
            features |= AlarmControlPanelEntityFeature.ARM_NIGHT
        if enable_bypass:
            features |= AlarmControlPanelEntityFeature.ARM_VACATION
        features |= AlarmControlPanelEntityFeature.TRIGGER
        self._attr_supported_features = features

    async def async_added_to_hass(self):
        self._client.register_callback(self._handle_update)

    @callback
    def _handle_update(self, update):
        if update["type"] == "area" and update["id"] == self._area_id:
            if update["alarm"]:
                self._state = STATE_ALARM_TRIGGERED
            elif update["armed"]:
                self._state = STATE_ALARM_ARMED_AWAY
            else:
                self._state = STATE_ALARM_DISARMED
            self.async_write_ha_state()

    @property
    def state(self):
        return self._state

    async def async_alarm_disarm(self, code=None) -> None:
        if not code:
            return
        await self._client.send_command_with_pin(0x02, 0x02, self._area_id, code)

    async def async_alarm_arm_away(self, code=None) -> None:
        if not code:
            return
        await self._client.send_command_with_pin(0x02, 0x01, self._area_id, code)

    async def async_alarm_arm_home(self, code=None) -> None:
        if not code:
            return
        await self._client.send_command_with_pin(0x02, 0x03, self._area_id, code)

    async def async_alarm_arm_night(self, code=None) -> None:
        if not code:
            return
        await self._client.send_command_with_pin(0x02, 0x04, self._area_id, code)

    async def async_alarm_arm_vacation(self, code=None) -> None:
        if not code:
            return
        await self._client.send_command_with_pin(0x02, 0x01, self._area_id, code)
