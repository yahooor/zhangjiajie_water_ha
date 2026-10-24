"""张家界供水集成入口"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import CONF_UPDATE_MODE, DOMAIN, UPDATE_MODE_INTERVAL
from .coordinator import ZhangjiajieWaterCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "button", "binary_sensor"]


async def _async_deploy_card_files(hass: HomeAssistant) -> None:
    """把内置 Lovelace 卡片与 logo 复制到 <配置目录>/www/zhangjiajie_water/。

    custom_components 目录不被 /local/ 静态服务，必须在设置时复制到用户 www 目录。
    内容一致时跳过写入，避免每次重启都改变文件时间、击穿浏览器缓存。
    """
    src_dir = Path(__file__).parent / "www"
    dst_dir = Path(hass.config.path("www", "zhangjiajie_water"))

    def _copy() -> None:
        dst_dir.mkdir(parents=True, exist_ok=True)
        for src in src_dir.iterdir():
            if not src.is_file():
                continue
            dst = dst_dir / src.name
            if not dst.exists() or dst.read_bytes() != src.read_bytes():
                shutil.copyfile(src, dst)
                _LOGGER.info("已更新内置卡片文件: %s", dst)

    await hass.async_add_executor_job(_copy)


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

    # 首次刷新：失败时打印警告但继续（不让初始化彻底失败）；
    # 唯独凭据失效必须上抛，让 HA 对该条目发起重新认证流程
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        raise
    except Exception as err:
        _LOGGER.warning("首次数据刷新失败，协程将在下次轮询时重试: %s", err)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    try:
        await _async_deploy_card_files(hass)
    except Exception as err:
        _LOGGER.warning("内置 Lovelace 卡片文件复制失败: %s", err)

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
