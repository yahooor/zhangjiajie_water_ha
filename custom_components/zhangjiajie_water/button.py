"""张家界供水 按钮平台 - 手动刷新数据"""
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .coordinator import ZhangjiajieWaterCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    async_add_entities([RefreshWaterDataButton(hass, config_entry)])


class RefreshWaterDataButton(ButtonEntity):
    """手动刷新数据按钮"""

    _attr_has_entity_name = True
    _attr_name = "刷新数据"
    _attr_icon = "mdi:refresh"

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        self.hass = hass
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_refresh_data"

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN, self._config_entry.data["account_no"])},
            "name": self._config_entry.data.get("account_name", self._config_entry.data["account_no"]),
            "manufacturer": "张家界市自来水有限责任公司",
            "model": "智能水表",
        }

    async def async_press(self) -> None:
        """按钮按下：触发 coordinator 刷新"""
        coordinator: ZhangjiajieWaterCoordinator | None = self.hass.data.get(DOMAIN, {}).get(
            self._config_entry.entry_id
        )
        if coordinator is None:
            _LOGGER.error("Coordinator 未初始化，无法刷新")
            return
        _LOGGER.info("用户触发手动刷新数据")
        await coordinator.async_request_refresh()
