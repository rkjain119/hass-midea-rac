DOMAIN = "midea_rac"
BROKER_HOST = "broker.smartliving.jio.com"
BROKER_PORT = 8883

CONF_PHONE = "phone"
CONF_TOKEN = "token"          # sessionid = "<userId>-<token>"
CONF_OWNER = "owner_id"       # owner user id used in topics

# OBLO service/property mapping
SVC_OUTLET = "OutletService"
SVC_THERMO = "ThermostatService"
SVC_THERMO_MODE = "ThermostatModeService"
SVC_FAN = "FanService"
SVC_TEMP_DEV = "temperatureDEV"         # indoor/outdoor readings
SVC_AC_CONFIG_DEV = "acConfigurationDEV"
SVC_OPSTATE = "ThermostatOperatingStateService"
SVC_POWER = "PowerConsumptionService"
SVC_DIAG = "WiseDiagnosticService"

# ThermostatMode enum index -> HA hvac mode (when powered on)
THERMO_MODE = ["off", "heat", "cool", "auto", "fan_only", "dry"]
# Fan mode enum
FAN_MODES = ["Low", "Medium", "High", "FullPower", "Auto"]
