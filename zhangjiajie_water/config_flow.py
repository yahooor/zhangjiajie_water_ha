"""Config flow for Zhangjiajie Water integration."""
from __future__ import annotations
import logging
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import callback
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class ZhangjiajieWaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

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
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> OptionsFlow:
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
            # vol.Range 已在 schema 层验证 1~24，无需手动校验
            _LOGGER.info(
                "[OptionsFlow] 保存: update_interval=%d", user_input["update_interval"]
            )
            return self.async_create_entry(
                title="", data={"update_interval": user_input["update_interval"]}
            )

        current = self._config_entry.options.get("update_interval", 6)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("update_interval", default=current): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=24)
                ),
            }),
            description_placeholders={"update_interval": f"数据刷新间隔（小时），当前: {current} 小时"},
        )
