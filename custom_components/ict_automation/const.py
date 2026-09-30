DOMAIN = "ict_automation"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_PASSWORD = "password"

# Optional Protege WX web operator credentials. These are used only by the
# read-only WX DLL API to retrieve programmed record names during scans.
CONF_WX_USERNAME = "wx_username"
CONF_WX_PASSWORD = "wx_password"

CONF_DOORS = "doors"
CONF_AREAS = "areas"
CONF_INPUTS = "inputs"
CONF_OUTPUTS = "outputs"
# Troubles are now part of inputs, but we keep the key just in case of legacy usage
CONF_TROUBLES = "troubles"

# New Constants for Arming Modes
CONF_ENABLE_AWAY = "enable_arm_away"
CONF_ENABLE_STAY = "enable_arm_stay"
CONF_ENABLE_NIGHT = "enable_arm_night"
CONF_ENABLE_BYPASS = "enable_arm_bypass"
