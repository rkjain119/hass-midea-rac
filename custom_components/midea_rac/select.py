"""Select platform for Midea RAC Wi-Fi ACs (FC gear / capacity level)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import ObloClient, ObloNode
from .const import DOMAIN, SVC_AC_CONFIG_DEV

GEAR_OFF = "Off"
# FC1..FC6; FC6 is turbo: the AC switches turbo on and resets capacity to 0, so FC6 is
# shown from the turbo flag. (capacityLevel's list length varies by unit and does not
# match the gears the AC actually offers, so it is not used.)
GEARS = 6
TURBO_GEAR = 6


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    client: ObloClient = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        MideaGearSelect(client, node)
        for node in client.nodes.values()
        if node.prop(SVC_AC_CONFIG_DEV, "capacity") is not None
    )


class MideaGearSelect(SelectEntity):
    """FC1..FCn compressor capacity limit. Only accepted by the AC in cool mode."""

    _attr_has_entity_name = True
    _attr_name = "Gear"
    _attr_icon = "mdi:speedometer"

    def __init__(self, client: ObloClient, node: ObloNode) -> None:
        self._client = client
        self._node_id = node.id
        self._attr_options = [GEAR_OFF] + [f"FC{i}" for i in range(1, GEARS + 1)]
        self._attr_unique_id = f"{node.serial}_{node.id}_gear"
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
    def current_option(self) -> str | None:
        level = self._node.prop(SVC_AC_CONFIG_DEV, "capacity")
        if not level and self._node.prop(SVC_AC_CONFIG_DEV, "turbo"):
            return f"FC{TURBO_GEAR}"
        option = f"FC{level}" if level else GEAR_OFF
        return option if option in self._attr_options else None

    async def async_select_option(self, option: str) -> None:
        level = 0 if option == GEAR_OFF else int(option[2:])
        if level == 0 and self._node.prop(SVC_AC_CONFIG_DEV, "turbo"):
            # Leaving FC6 means leaving turbo.
            await self.hass.async_add_executor_job(
                self._client.set_property, self._node, SVC_AC_CONFIG_DEV, "turbo", False
            )
        await self.hass.async_add_executor_job(
            self._client.set_property, self._node, SVC_AC_CONFIG_DEV, "capacity", level
        )

    async def async_added_to_hass(self) -> None:
        @callback
        def _updated() -> None:
            self.async_write_ha_state()

        self._client.set_state_callback(
            lambda: self.hass.loop.call_soon_threadsafe(_updated)
        )
