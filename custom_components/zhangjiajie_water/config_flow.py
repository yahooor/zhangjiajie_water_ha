"""Config flow for Zhangjiajie Water integration."""
from __future__ import annotations
import logging
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
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
            description_placeholders={
                "account_no": "户号（账单上 8 位数字）",
                "openid": "微信 OpenID（从抓包获取）",
            },
        )



