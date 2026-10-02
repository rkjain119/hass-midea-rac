"""Fan platform for Midea RAC Wi-Fi ACs: the AC's fan speed as a slider."""
from __future__ import annotations

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .api import ObloClient, ObloNode
from .const import DOMAIN, FAN_MODE_TO_OBLO, SVC_FAN, SVC_OUTLET

SPEEDS = ["low", "medium", "high"]
PRESET_AUTO = "Auto"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    client: ObloClient = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(MideaFan(client, node) for node in client.nodes.values())


class MideaFan(FanEntity):
    """Fan speed of the AC. On/off follows the AC's power."""

    _attr_has_entity_name = True
    _attr_name = "Fan"
    _attr_speed_count = len(SPEEDS)
    _attr_preset_modes = [PRESET_AUTO]
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    def __init__(self, client: ObloClient, node: ObloNode) -> None:
        self._client = client
        self._node_id = node.id
        self._attr_unique_id = f"{node.serial}_{node.id}_fan"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{node.serial}_{node.id}")},
        )

    @property
    def _node(self) -> ObloNode:
        return self._client.nodes.get(self._node_id)

    @property
    def available(self) -> bool:
        return self._client.connected and self._node is not None

    @property
    def is_on(self) -> bool | None:
        v = self._node.prop(SVC_OUTLET, "State")
        return None if v is None else bool(v)

    @property
    def _mode_name(self) -> str | None:
        idx = self._node.prop(SVC_FAN, "Mode")
        return next((n for n, v in FAN_MODE_TO_OBLO.items() if v == idx), None)

    @property
    def percentage(self) -> int | None:
        name = self._mode_name
        return ordered_list_item_to_percentage(SPEEDS, name) if name in SPEEDS else None

    @property
    def preset_mode(self) -> str | None:
        return PRESET_AUTO if self._mode_name == "auto" else None

    async def _set(self, service: str, prop: str, value) -> None:
        await self.hass.async_add_executor_job(
            self._client.set_property, self._node, service, prop, value
        )

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            await self.async_turn_off()
            return
        speed = percentage_to_ordered_list_item(SPEEDS, percentage)
        await self._set(SVC_FAN, "Mode", FAN_MODE_TO_OBLO[speed])

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self._set(SVC_FAN, "Mode", FAN_MODE_TO_OBLO["auto"])

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs) -> None:
        if not self.is_on:
            await self._set(SVC_OUTLET, "State", True)
        if preset_mode:
            await self.async_set_preset_mode(preset_mode)
        elif percentage:
            await self.async_set_percentage(percentage)

    async def async_turn_off(self, **kwargs) -> None:
        await self._set(SVC_OUTLET, "State", False)

    async def async_added_to_hass(self) -> None:
        @callback
        def _updated() -> None:
            self.async_write_ha_state()

        self._client.set_state_callback(
            lambda: self.hass.loop.call_soon_threadsafe(_updated)
        )
