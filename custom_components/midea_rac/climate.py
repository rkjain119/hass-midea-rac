"""Climate platform for Midea RAC Wi-Fi ACs."""
from __future__ import annotations

import logging

from homeassistant.components.climate import (
    PRESET_BOOST,
    PRESET_ECO,
    PRESET_NONE,
    PRESET_SLEEP,
    SWING_OFF,
    SWING_ON,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import ObloClient, ObloNode
from .const import (
    DOMAIN,
    FAN_MODE_TO_OBLO,
    FAN_MODES,
    HORIZONTAL_STOP,
    HORIZONTAL_SWING,
    SVC_AC_CONFIG_DEV,
    SVC_FAN,
    SVC_LOUVER_DEV,
    SVC_OUTLET,
    SVC_TEMP_DEV,
    SVC_THERMO,
    SVC_THERMO_MODE,
    VERTICAL_FIXED_TOP,
    VERTICAL_SWING,
)

_LOGGER = logging.getLogger(__name__)

PRESET_TO_PROP = {PRESET_ECO: "eco", PRESET_SLEEP: "sleep", PRESET_BOOST: "turbo"}

# HA hvac mode <-> OBLO ThermostatMode index (2=Cooling,3=Auto,4=Fan,5=Dry).
# 1=Heating exists in the protocol but these units are cooling-only.
HA_TO_OBLO_MODE = {
    HVACMode.COOL: 2,
    HVACMode.AUTO: 3,
    HVACMode.FAN_ONLY: 4,
    HVACMode.DRY: 5,
}
OBLO_TO_HA_MODE = {
    2: HVACMode.COOL,
    3: HVACMode.AUTO,
    4: HVACMode.FAN_ONLY,
    5: HVACMode.DRY,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up climate entities."""
    client: ObloClient = hass.data[DOMAIN][entry.entry_id]
    entities = [MideaClimate(client, node) for node in client.nodes.values()]
    async_add_entities(entities)


class MideaClimate(ClimateEntity):
    """A Midea air conditioner."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1.0
    _attr_min_temp = 17
    _attr_max_temp = 30
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.COOL,
        HVACMode.AUTO,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
    ]
    _attr_fan_modes = FAN_MODES
    _attr_preset_modes = [PRESET_NONE, PRESET_ECO, PRESET_SLEEP, PRESET_BOOST]
    _attr_swing_modes = [SWING_ON, SWING_OFF]
    _attr_swing_horizontal_modes = [SWING_ON, SWING_OFF]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.SWING_HORIZONTAL_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, client: ObloClient, node: ObloNode) -> None:
        self._client = client
        self._node_id = node.id
        self._attr_unique_id = f"{node.serial}_{node.id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=node.name,
            manufacturer="Midea",
            model="MIMM310B58",
        )

    @property
    def _node(self) -> ObloNode:
        return self._client.nodes.get(self._node_id)

    @property
    def available(self) -> bool:
        return self._client.connected and self._node is not None

    @property
    def current_temperature(self):
        # TemperatureService.Value only mirrors the setpoint; the room reading is here.
        v = self._node.prop(SVC_TEMP_DEV, "indoorTemperature")
        if v is None:
            v = self._node.prop(SVC_AC_CONFIG_DEV, "indoorTemperature")
        return float(v) if v is not None else None

    @property
    def target_temperature(self):
        v = self._node.prop(SVC_THERMO, "Value")
        return float(v) if v is not None else None

    @property
    def hvac_mode(self):
        if not self._node.prop(SVC_OUTLET, "State"):
            return HVACMode.OFF
        idx = self._node.prop(SVC_THERMO_MODE, "ThermostatMode")
        return OBLO_TO_HA_MODE.get(idx, HVACMode.AUTO)

    @property
    def fan_mode(self):
        idx = self._node.prop(SVC_FAN, "Mode")
        for name, value in FAN_MODE_TO_OBLO.items():
            if value == idx:
                return name
        return None

    @property
    def preset_mode(self):
        for preset, prop in PRESET_TO_PROP.items():
            if self._node.prop(SVC_AC_CONFIG_DEV, prop):
                return preset
        return PRESET_NONE

    @property
    def swing_mode(self):
        v = self._node.prop(SVC_LOUVER_DEV, "verticalMode")
        return SWING_ON if v == VERTICAL_SWING else SWING_OFF

    @property
    def swing_horizontal_mode(self):
        v = self._node.prop(SVC_LOUVER_DEV, "horizontalMode")
        return SWING_ON if v == HORIZONTAL_SWING else SWING_OFF

    # ---- commands ----
    async def async_set_temperature(self, **kwargs) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        await self.hass.async_add_executor_job(
            self._client.set_property, self._node, SVC_THERMO, "Value", str(int(temp))
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self.hass.async_add_executor_job(
                self._client.set_property, self._node, SVC_OUTLET, "State", False
            )
        else:
            # ensure powered on, then set mode
            if not self._node.prop(SVC_OUTLET, "State"):
                await self.hass.async_add_executor_job(
                    self._client.set_property, self._node, SVC_OUTLET, "State", True
                )
            oblo = HA_TO_OBLO_MODE.get(hvac_mode)
            if oblo is not None:
                await self.hass.async_add_executor_job(
                    self._client.set_property,
                    self._node,
                    SVC_THERMO_MODE,
                    "ThermostatMode",
                    oblo,
                )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        if fan_mode in FAN_MODE_TO_OBLO:
            await self._set(SVC_FAN, "Mode", FAN_MODE_TO_OBLO[fan_mode])

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        # eco / sleep / turbo are separate flags on the AC; only one is active at a time.
        for preset, prop in PRESET_TO_PROP.items():
            if preset != preset_mode and self._node.prop(SVC_AC_CONFIG_DEV, prop):
                await self._set(SVC_AC_CONFIG_DEV, prop, False)
        if preset_mode in PRESET_TO_PROP:
            await self._set(SVC_AC_CONFIG_DEV, PRESET_TO_PROP[preset_mode], True)

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        value = VERTICAL_SWING if swing_mode == SWING_ON else VERTICAL_FIXED_TOP
        await self._set(SVC_LOUVER_DEV, "verticalMode", value)

    async def async_set_swing_horizontal_mode(self, swing_horizontal_mode: str) -> None:
        value = HORIZONTAL_SWING if swing_horizontal_mode == SWING_ON else HORIZONTAL_STOP
        await self._set(SVC_LOUVER_DEV, "horizontalMode", value)

    async def _set(self, service: str, prop: str, value) -> None:
        await self.hass.async_add_executor_job(
            self._client.set_property, self._node, service, prop, value
        )

    async def async_turn_on(self) -> None:
        await self.hass.async_add_executor_job(
            self._client.set_property, self._node, SVC_OUTLET, "State", True
        )

    async def async_turn_off(self) -> None:
        await self.hass.async_add_executor_job(
            self._client.set_property, self._node, SVC_OUTLET, "State", False
        )

    async def async_added_to_hass(self) -> None:
        @callback
        def _updated() -> None:
            self.async_write_ha_state()

        self._client.set_state_callback(
            lambda: self.hass.loop.call_soon_threadsafe(_updated)
        )
