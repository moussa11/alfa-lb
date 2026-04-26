"""Sensors for Alfa Lebanon."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, MANUFACTURER
from .coordinator import AlfaCoordinator


@dataclass(frozen=True, kw_only=True)
class AlfaSensorEntityDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


SENSORS: tuple[AlfaSensorEntityDescription, ...] = (
    AlfaSensorEntityDescription(
        key="balance",
        translation_key="balance",
        icon="mdi:cash",
        native_unit_of_measurement="USD",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("balance_usd"),
        attrs_fn=lambda d: {"raw": d.get("balance_raw")},
    ),
    AlfaSensorEntityDescription(
        key="data_used",
        translation_key="data_used",
        icon="mdi:download-network",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.MEBIBYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("data_used_mb"),
    ),
    AlfaSensorEntityDescription(
        key="data_total",
        translation_key="data_total",
        icon="mdi:database",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.MEBIBYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("data_total_mb"),
    ),
    AlfaSensorEntityDescription(
        key="data_remaining",
        translation_key="data_remaining",
        icon="mdi:download-network-outline",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.MEBIBYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("data_remaining_mb"),
    ),
    AlfaSensorEntityDescription(
        key="plan",
        translation_key="plan",
        icon="mdi:sim",
        value_fn=lambda d: d.get("plan_name"),
    ),
    AlfaSensorEntityDescription(
        key="validity",
        translation_key="validity",
        icon="mdi:calendar-clock",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda d: d.get("validity"),
    ),
    AlfaSensorEntityDescription(
        key="days_until_expiry",
        translation_key="days_until_expiry",
        icon="mdi:calendar-end",
        native_unit_of_measurement="d",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("days_until_expiry"),
    ),
    AlfaSensorEntityDescription(
        key="last_recharge_amount",
        translation_key="last_recharge_amount",
        icon="mdi:cash-plus",
        native_unit_of_measurement="USD",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("last_recharge_amount"),
        attrs_fn=lambda d: {"history": d.get("recharge_history") or []},
    ),
    AlfaSensorEntityDescription(
        key="last_recharge_date",
        translation_key="last_recharge_date",
        icon="mdi:calendar-check",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda d: d.get("last_recharge_date"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AlfaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AlfaSensor(coordinator, entry, description) for description in SENSORS
    )


class AlfaSensor(CoordinatorEntity[AlfaCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    entity_description: AlfaSensorEntityDescription

    def __init__(
        self,
        coordinator: AlfaCoordinator,
        entry: ConfigEntry,
        description: AlfaSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=MANUFACTURER,
            name=entry.title,
            model=(coordinator.data or {}).get("plan_name"),
            configuration_url="https://www.alfa.com.lb",
        )

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if not self.coordinator.data or self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)
