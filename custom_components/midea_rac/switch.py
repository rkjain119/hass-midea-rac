"""Switch platform for Midea RAC Wi-Fi ACs (power, display, self-clean, anti-mildew)."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import ObloClient, ObloNode
from .const import DOMAIN, SVC_AC_CONFIG_DEV, SVC_OUTLET


@dataclass(frozen=True, kw_only=True)
class ObloSwitch:
    key: str
    name: str
    prop: str
    icon: str
    service: str = SVC_AC_CONFIG_DEV
    config: bool = False


SWITCHES: list[ObloSwitch] = [
    # The AC resumes its last mode when switched back on.
    ObloSwitch(key="power", name="Power", prop="State", icon="mdi:power", service=SVC_OUTLET),
    ObloSwitch(key="display", name="Display", prop="display", icon="mdi:led-on"),
    ObloSwitch(key="self_clean", name="Self-clean", prop="iClean", icon="mdi:spray-bottle"),
    # Dries the coil after the AC is switched off.
    ObloSwitch(
        key="anti_mildew", name="Anti-mildew", prop="antiMildew",
        icon="mdi:water-off", config=True,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    client: ObloClient = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for node in client.nodes.values():
        for desc in SWITCHES:
            if node.prop(desc.service, desc.prop) is not None:
                entities.append(MideaSwitch(client, node, desc))
    async_add_entities(entities)


class MideaSwitch(SwitchEntity):
    _attr_has_entity_name = True

    def __init__(self, client: ObloClient, node: ObloNode, desc: ObloSwitch) -> None:
        self._client = client
        self._node_id = node.id
        self._desc = desc
        self._attr_name = desc.name
        self._attr_icon = desc.icon
        self._attr_unique_id = f"{node.serial}_{node.id}_{desc.key}"
        if desc.config:
            self._attr_entity_category = EntityCategory.CONFIG
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
        v = self._node.prop(self._desc.service, self._desc.prop)
        return None if v is None else bool(v)

    async def async_turn_on(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(
            self._client.set_property, self._node, self._desc.service, self._desc.prop, True
        )

    async def async_turn_off(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(
            self._client.set_property, self._node, self._desc.service, self._desc.prop, False
        )

    async def async_added_to_hass(self) -> None:
        @callback
        def _updated() -> None:
            self.async_write_ha_state()

        self._client.set_state_callback(
            lambda: self.hass.loop.call_soon_threadsafe(_updated)
        )
