"""张家界供水集成入口"""
from __future__ import annotations
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_UPDATE_MODE, UPDATE_MODE_INTERVAL
from .coordinator import ZhangjiajieWaterCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "button"]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """迁移旧版本 ConfigEntry 到最新版本。"""
    _LOGGER.debug("迁移 ConfigEntry: v%s → v2", entry.version)
    if entry.version == 1:
        # v1 → v2: options 中新增 update_mode 字段，默认 interval（保持原行为）
        new_options = {**entry.options, CONF_UPDATE_MODE: UPDATE_MODE_INTERVAL}
        hass.config_entries.async_update_entry(entry, options=new_options, version=2)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = ZhangjiajieWaterCoordinator(hass, entry)

    # 首次刷新：失败时打印警告但继续（不让初始化彻底失败）
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.warning("首次数据刷新失败，协程将在下次轮询时重试: %s", err)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 保存 undo 回调，卸载时调用防止监听器泄漏
    unload_listener = entry.add_update_listener(_async_update_listener)
    entry.async_on_unload(unload_listener)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: ZhangjiajieWaterCoordinator | None = hass.data[DOMAIN].pop(
            entry.entry_id, None
        )
        if coordinator:
            await coordinator.async_shutdown()
    return unload_ok
