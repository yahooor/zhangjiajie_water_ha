"""张家界供水 API 客户端"""
from __future__ import annotations
import asyncio
import json
import logging

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import BASE_URL, API_PATH

_LOGGER = logging.getLogger(__name__)


class ZhangjiajieWaterAPI:
    """张家界水务 API 客户端"""

    def __init__(self, account_no: str, openid: str, hass: HomeAssistant | None = None):
        self.account_no = account_no
        self.openid = openid
        self.base_url = BASE_URL
        self.api_path = API_PATH
        self._session: aiohttp.ClientSession | None = None
        self._hass = hass
        self._closed = False

    async def async_close(self) -> None:
        """关闭 HTTP session（仅在自建 session 时关闭）"""
        self._closed = True
        if self._session and not self._session.closed and self._hass is None:
            await self._session.close()
            self._session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取 HA 共享 session 或自建 session"""
        if self._hass is not None:
            return async_get_clientsession(self._hass)
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20))
        return self._session

    def _make_custcode(self, page: int) -> str:
        """构建分页参数: 户号,页码,每页数量,1"""
        # 末尾 "1" 为接口固定参数（抓包确认所有请求均为 1，非 data_type 标识）
        return f"{self.account_no},{page},10,1"

    def _make_form(self, data_type: int, page: int = 1) -> dict:
        """构建 form data"""
        return {
            "type": str(data_type),
            "custCode": self._make_custcode(page),
            "wxid": self.openid,
        }

    @property
    def headers(self) -> dict:
        return {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Origin": self.base_url,
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 26_4_2 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
                "MicroMessenger/8.0.72(0x18004820) NetType/WIFI Language/zh_CN"
            ),
        }

    async def fetch_usage_records(self, page: int = 1) -> list:
        """获取 type=1 用水记录（分页）"""
        url = f"{self.base_url}{self.api_path}"
        form = self._make_form(1, page)
        data = await self._post(url, form)
        return data.get("data", [])

    async def fetch_payment_records(self, page: int = 1) -> list:
        """获取 type=2 缴费记录（分页）"""
        url = f"{self.base_url}{self.api_path}"
        form = self._make_form(2, page)
        data = await self._post(url, form)
        return data.get("data", [])

    async def _post(self, url: str, form: dict, retries: int = 3) -> dict:
        """POST 请求，带重试"""
        if self._closed:
            raise UpdateFailed("API 客户端已关闭")
        last_error: Exception | None = None
        for attempt in range(retries):
            non_retryable = False
            try:
                session = await self._get_session()
                async with session.post(url, data=form, headers=self.headers) as resp:
                    text = await resp.text()
                    if resp.status != 200:
                        # HTTP 4xx 客户端错误不应重试（如 401/403/404）
                        if 400 <= resp.status < 500:
                            non_retryable = True
                        raise Exception(f"API HTTP {resp.status}: {text[:200]}")
                try:
                    result = json.loads(text)
                except (json.JSONDecodeError, ValueError):
                    # 非 JSON 响应（如 502 网关错误页面），重试无意义
                    non_retryable = True
                    raise Exception(f"API 返回非 JSON 响应: {text[:200]}")
                if result.get("res") != 100:
                    # API 业务错误（如户号错误），重试无意义
                    non_retryable = True
                    msg = result.get("msg", "")
                    detail = f" - {msg}" if msg else ""
                    raise Exception(f"API 返回错误码 {result.get('res')}{detail}")
                return result
            except Exception as e:
                last_error = e
                if non_retryable or attempt >= retries - 1:
                    raise
                wait = 2 ** attempt
                _LOGGER.warning(
                    "API 请求失败 (第 %d/%d 次)，%d 秒后重试: %s",
                    attempt + 1,
                    retries,
                    wait,
                    e,
                )
                await asyncio.sleep(wait)
        assert last_error is not None  # 循环至少执行一次
        raise last_error
