"""张家界供水 诊断支持（设置 → 集成 → 下载诊断）"""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import ZhangjiajieWaterCoordinator

# 凭据类字段全量脱敏（customer_code 的值就是户号）
TO_REDACT = {"openid", "wxid", "account_no", "custCode", "customer_code"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinator: ZhangjiajieWaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    return async_redact_data(
        {
            "entry": {
                "version": entry.version,
                "data": dict(entry.data),
                "options": dict(entry.options),
            },
            "coordinator": {
                "last_update_success": coordinator.last_update_success,
                "last_exception": (
                    str(coordinator.last_exception)
                    if coordinator.last_exception
                    else None
                ),
                "data": coordinator.data,
            },
        },
        TO_REDACT,
    )
