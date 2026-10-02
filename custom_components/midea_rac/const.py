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
SVC_AC_CONFIG_DEV = "acConfigurationDEV"   # eco/turbo/sleep/display/iClean/antiMildew
SVC_LOUVER_DEV = "louverDEV"
SVC_OPSTATE = "ThermostatOperatingStateService"
SVC_POWER = "PowerConsumptionService"
SVC_DIAG = "WiseDiagnosticService"

# FanService.Mode values. FullPower (3) is only set by the AC itself in turbo.
# HA standard fan mode names, so the frontend shows its built-in icons/labels.
FAN_MODE_TO_OBLO = {"low": 0, "medium": 1, "high": 2, "auto": 4}
FAN_MODES = list(FAN_MODE_TO_OBLO)

# louverDEV values verified on a MIMM310B58 unit. verticalMode 0 closes the louver
# fully, so it is never sent.
VERTICAL_SWING = 1
VERTICAL_FIXED_TOP = 2
HORIZONTAL_SWING = 1
HORIZONTAL_STOP = 0
