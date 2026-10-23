"""张家界供水 二进制传感器平台 - 低余额提醒"""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_LOW_BALANCE_THRESHOLD, DOMAIN
from .coordinator import ZhangjiajieWaterCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ZhangjiajieWaterCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([LowBalanceBinarySensor(coordinator)])


class LowBalanceBinarySensor(
    CoordinatorEntity[ZhangjiajieWaterCoordinator], BinarySensorEntity
):
    """余额低于阈值时开启（阈值在集成选项中配置，0 = 关闭）。"""

    _attr_has_entity_name = True
    _attr_name = "余额不足"
    _attr_icon = "mdi:cash-remove"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: ZhangjiajieWaterCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_low_balance"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        try:
            threshold = float(
                self.coordinator.entry.options.get(CONF_LOW_BALANCE_THRESHOLD, 0) or 0
            )
        except (TypeError, ValueError):
            threshold = 0.0
        if threshold <= 0:
            return False
        if not self.coordinator.data:
            return None
        balance = self.coordinator.data.get("balance")
        if balance is None:
            return None
        return float(balance) < threshold
