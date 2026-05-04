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
        _LOGGER.warning("[OptionsFlow] __init__ called, current options=%s", dict(config_entry.options))

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        _LOGGER.warning("[OptionsFlow] async_step_init called, user_input=%s", user_input)

        if user_input is not None:
            update_interval = user_input.get("update_interval")
            _LOGGER.warning("[OptionsFlow] user_input received: update_interval=%s (type=%s)", update_interval, type(update_interval))

            if update_interval is None:
                _LOGGER.error("[OptionsFlow] FATAL: update_interval is None in user_input!")
                errors = {"update_interval": "invalid_interval"}
            elif not isinstance(update_interval, int) or update_interval < 1 or update_interval > 24:
                _LOGGER.warning("[OptionsFlow] Validation failed: update_interval=%s", update_interval)
                errors = {"update_interval": "invalid_interval"}
            else:
                _LOGGER.warning("[OptionsFlow] Validation passed, calling async_create_entry with update_interval=%d", update_interval)
                result = self.async_create_entry(title="", data={"update_interval": update_interval})
                _LOGGER.warning("[OptionsFlow] async_create_entry returned, options now=%s", dict(self._config_entry.options))
                return result
        else:
            errors = {}
            _LOGGER.warning("[OptionsFlow] user_input is None, showing form (no submission)")

        current = self._config_entry.options.get("update_interval", 6)
        _LOGGER.warning("[OptionsFlow] Showing form with current update_interval=%d", current)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("update_interval", default=current): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=24)
                ),
            }),
            errors=errors,
            description_placeholders={"update_interval": "数据刷新间隔（小时）"},
        )
