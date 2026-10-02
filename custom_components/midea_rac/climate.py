"""Climate platform for Midea RAC Wi-Fi ACs."""
from __future__ import annotations

import logging

from homeassistant.components.climate import (
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
    FAN_MODES,
    SVC_AC_CONFIG_DEV,
    SVC_FAN,
    SVC_OUTLET,
    SVC_TEMP_DEV,
    SVC_THERMO,
    SVC_THERMO_MODE,
    THERMO_MODE,
)

_LOGGER = logging.getLogger(__name__)

# HA hvac mode <-> OBLO ThermostatMode index (1=Heating,2=Cooling,3=Auto,4=Fan,5=Dry)
HA_TO_OBLO_MODE = {
    HVACMode.HEAT: 1,
    HVACMode.COOL: 2,
    HVACMode.AUTO: 3,
    HVACMode.FAN_ONLY: 4,
    HVACMode.DRY: 5,
}
OBLO_TO_HA_MODE = {
    1: HVACMode.HEAT,
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
        HVACMode.HEAT,
        HVACMode.AUTO,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
    ]
    _attr_fan_modes = FAN_MODES
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
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
        if isinstance(idx, int) and 0 <= idx < len(FAN_MODES):
            return FAN_MODES[idx]
        return None

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
        if fan_mode in FAN_MODES:
            await self.hass.async_add_executor_job(
                self._client.set_property,
                self._node,
                SVC_FAN,
                "Mode",
                FAN_MODES.index(fan_mode),
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
