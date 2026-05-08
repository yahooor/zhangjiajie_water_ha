"""张家界供水 按钮平台 - 手动刷新数据"""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import ZhangjiajieWaterCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    coordinator: ZhangjiajieWaterCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([RefreshWaterDataButton(coordinator)])


class RefreshWaterDataButton(ButtonEntity):
    """手动刷新数据按钮"""

    _attr_has_entity_name = True
    _attr_name = "刷新数据"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: ZhangjiajieWaterCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_refresh_data"
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        """按钮按下：触发 coordinator 刷新"""
        _LOGGER.info("用户触发手动刷新数据")
        await self._coordinator.async_request_refresh()
