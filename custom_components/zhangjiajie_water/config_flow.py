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
            update_interval = user_input.get("update_interval")
            if update_interval is None:
                return self.async_show_form(
                    step_id="init",
                    data_schema=vol.Schema({
                        vol.Optional("update_interval", default=6): vol.All(
                            vol.Coerce(int), vol.Range(min=1, max=24)
                        ),
                    }),
                    errors={"update_interval": "invalid_interval"},
                    description_placeholders={"update_interval": "数据刷新间隔（小时）"},
                )

            if not isinstance(update_interval, int) or update_interval < 1 or update_interval > 24:
                return self.async_show_form(
                    step_id="init",
                    data_schema=vol.Schema({
                        vol.Optional("update_interval", default=update_interval): vol.All(
                            vol.Coerce(int), vol.Range(min=1, max=24)
                        ),
                    }),
                    errors={"update_interval": "invalid_interval"},
                    description_placeholders={"update_interval": "数据刷新间隔（小时）"},
                )

            # ★★★ 关键修复 v2.2.5 ★★★
            # 1. async_update_entry 只更新内存，async_save() 才持久化到磁盘
            # 2. 持久化后再触发 reload，确保 Coordinator 用新 interval 启动
            new_options = dict(self._config_entry.options)
            new_options["update_interval"] = update_interval
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                options=new_options
            )
            # ★ 必须显式调用 async_save()，否则选项只存在内存，HA 重启后丢失
            await self.hass.config_entries.async_save()
            _LOGGER.warning(
                "[OptionsFlow] 保存成功: update_interval=%d, 新options=%s, 已持久化, 触发reload",
                update_interval, new_options
            )
            # 触发 reload，Coordinator 会用新的 update_interval 重建
            self.hass.config_entries.async_schedule_reload(self._config_entry.entry_id)
            # 完成 OptionsFlow（不传 data，因为 options 已通过 async_update_entry 更新）
            return self.async_create_entry(title="", data={})

        current = self._config_entry.options.get("update_interval", 6)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("update_interval", default=current): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=24)
                ),
            }),
            errors={},
            description_placeholders={"update_interval": f"数据刷新间隔（小时），当前: {current} 小时"},
        )
