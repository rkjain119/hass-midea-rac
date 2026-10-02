"""Sensor platform for Midea RAC Wi-Fi ACs (energy, Wi-Fi, outdoor temp)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import ObloClient, ObloNode
from .const import DOMAIN

LINK_QUALITY = ["UNKNOWN", "LOW", "MEDIUM", "HIGH", "EXCELLENT"]


@dataclass(frozen=True, kw_only=True)
class ObloSensor:
    key: str
    name: str
    service: str
    prop: str
    unit: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    diagnostic: bool = False
    transform: Callable | None = None


SENSORS: list[ObloSensor] = [
    ObloSensor(
        key="energy", name="Energy", service="PowerConsumptionService",
        prop="PowerConsumption", unit=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ObloSensor(
        key="power", name="Power", service="PowerConsumptionService",
        prop="ActivePower", unit=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
    ),
    ObloSensor(
        key="rssi", name="Wi-Fi signal", service="WiseDiagnosticService",
        prop="RSSI", unit=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT, diagnostic=True,
    ),
    ObloSensor(
        key="link", name="Link quality", service="WiseDiagnosticService",
        prop="LinkQuality", diagnostic=True,
        transform=lambda v: LINK_QUALITY[v] if isinstance(v, int) and 0 <= v < len(LINK_QUALITY) else v,
    ),
    ObloSensor(
        key="indoor_temp", name="Indoor temperature", service="temperatureDEV",
        prop="indoorTemperature", unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT,
    ),
    ObloSensor(
        key="outdoor_temp", name="Outdoor temperature", service="temperatureDEV",
        prop="outdoorTemperature", unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    client: ObloClient = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for node in client.nodes.values():
        for desc in SENSORS:
            if node.prop(desc.service, desc.prop) is not None:
                entities.append(MideaSensor(client, node, desc))
    async_add_entities(entities)


class MideaSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, client: ObloClient, node: ObloNode, desc: ObloSensor) -> None:
        self._client = client
        self._node_id = node.id
        self._desc = desc
        self._attr_name = desc.name
        self._attr_unique_id = f"{node.serial}_{node.id}_{desc.key}"
        self._attr_native_unit_of_measurement = desc.unit
        self._attr_device_class = desc.device_class
        self._attr_state_class = desc.state_class
        if desc.diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
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
    def native_value(self):
        v = self._node.prop(self._desc.service, self._desc.prop)
        if v is None:
            return None
        if self._desc.transform:
            return self._desc.transform(v)
        return v

    async def async_added_to_hass(self) -> None:
        @callback
        def _updated() -> None:
            self.async_write_ha_state()

        self._client.set_state_callback(
            lambda: self.hass.loop.call_soon_threadsafe(_updated)
        )
