"""Config flow for Zhangjiajie Water integration."""
from __future__ import annotations
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_UPDATE_MODE,
    CONF_DAILY_HOUR,
    CONF_DAILY_MINUTE,
    UPDATE_MODE_DAILY,
    UPDATE_MODE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


async def async_migrate_entry(hass, config_entry: config_entries.ConfigEntry) -> bool:
    """迁移旧版本 ConfigEntry 到最新版本。"""
    _LOGGER.debug("迁移 ConfigEntry: v%s → v2", config_entry.version)
    if config_entry.version == 1:
        # v1 → v2: options 中新增 update_mode 字段，默认 interval（保持原行为）
        new_options = {**config_entry.options, CONF_UPDATE_MODE: UPDATE_MODE_INTERVAL}
        hass.config_entries.async_update_entry(config_entry, options=new_options, version=2)
    return True


class ZhangjiajieWaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors = {}
        if user_input is not None:
            account_no = user_input.get("account_no", "").strip()
            openid = user_input.get("openid", "").strip()
            if not account_no or len(account_no) < 4:
                errors["account_no"] = "invalid_account"
            elif not openid or len(openid) < 10:
                errors["openid"] = "invalid_openid"
            if not errors:
                await self.async_set_unique_id(f"zjw_{account_no}")
                self._abort_if_unique_id_configured()
                title = user_input.get("account_name") or account_no
                return self.async_create_entry(title=title, data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("account_no"): str,
                vol.Required("openid"): str,
                vol.Optional("account_name", default=""): str,
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "ZhangjiajieWaterOptionsFlow":
        """Get the options flow for this handler."""
        return ZhangjiajieWaterOptionsFlow(config_entry)


class ZhangjiajieWaterOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Zhangjiajie Water."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            _LOGGER.info("[OptionsFlow] 保存: %s", user_input)
            return self.async_create_entry(title="", data=user_input)

        current_mode = self._config_entry.options.get(CONF_UPDATE_MODE, UPDATE_MODE_INTERVAL)
        current_interval = self._config_entry.options.get("update_interval", 6)
        current_hour = self._config_entry.options.get(CONF_DAILY_HOUR, 7)
        current_minute = self._config_entry.options.get(CONF_DAILY_MINUTE, 30)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_UPDATE_MODE, default=current_mode): vol.In(
                    [UPDATE_MODE_INTERVAL, UPDATE_MODE_DAILY]
                ),
                vol.Optional("update_interval", default=current_interval): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=24)
                ),
                vol.Optional(CONF_DAILY_HOUR, default=current_hour): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=23)
                ),
                vol.Optional(CONF_DAILY_MINUTE, default=current_minute): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=59)
                ),
            }),
            description_placeholders={
                "update_interval": str(current_interval),
                "daily_hour": str(current_hour),
                "daily_minute": str(current_minute),
            },
        )
