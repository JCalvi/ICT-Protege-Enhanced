from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


def controller_device_info() -> DeviceInfo:
    """Return the single Home Assistant device shared by all Protege entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, "ict_controller")},
        name="ICT Protege Controller",
        manufacturer="Integrated Control Technology",
        model="Protege WX/GX Controller",
    )
