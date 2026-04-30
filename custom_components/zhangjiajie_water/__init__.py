from __future__ import annotations
import json
import logging
from datetime import datetime, timedelta
import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN, BASE_URL, API_PATH
import asyncio

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]


class ZhangjiajieWaterAPI:
    """张家界水务 API 客户端"""
    def __init__(self, account_no: str, openid: str):
        self.account_no = account_no
        self.openid = openid
        self.base_url = BASE_URL
        self.api_path = API_PATH

    def _make_custcode(self, page: int) -> str:
        """构建分页参数: 户号,页码,每页数量,1=用水/2=缴费"""
        # 末尾 "1" 为接口固定参数，抓包确认所有请求均为 1
        return f"{self.account_no},{page},10,1"

    def _make_form(self, data_type: int, page: int = 1) -> dict:
        """构建 form data"""
        return {
            "type": str(data_type),
            "custCode": self._make_custcode(page),
            "wxid": self.openid
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
        timeout = aiohttp.ClientTimeout(total=20)
        last_error = None
        for attempt in range(retries):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url, data=form, headers=self.headers) as resp:
                        if resp.status != 200:
                            text = await resp.text()
                            raise Exception(f"API 错误 {resp.status}: {text}")
                        text = await resp.text()
                        result = json.loads(text)
                        if result.get("res") != 100:
                            msg = result.get("msg", "")
                            detail = f" - {msg}" if msg else ""
                            raise Exception(f"API 返回错误码 {result.get('res')}{detail}")
                        return result
            except Exception as e:
                last_error = e
                if attempt < retries - 1:
                    wait = 2 ** attempt
                    _LOGGER.warning("API 请求失败 (第 %d/%d 次)，%d 秒后重试: %s", attempt + 1, retries, wait, e)
                    await asyncio.sleep(wait)
        raise last_error


class ZhangjiajieWaterCoordinator(DataUpdateCoordinator):
    """数据协调器"""
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {entry.data['account_no']}",
            update_interval=timedelta(hours=6),
        )
        self.entry = entry
        self.api = ZhangjiajieWaterAPI(
            account_no=entry.data["account_no"],
            openid=entry.data["openid"],
        )
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data["account_no"])},
            manufacturer="张家界市自来水有限责任公司",
            name=entry.data.get("account_name", entry.data["account_no"]),
            model="智能水表",
            sw_version="1.0.0",
        )

    async def _async_update_data(self) -> dict:
        try:
            usage, payment = await asyncio.gather(
                self._fetch_usage(),
                self._fetch_payment()
            )
            return self._merge_data(usage, payment)
        except Exception as e:
            _LOGGER.error("数据更新失败: %s", e)
            raise

    async def _fetch_usage(self) -> dict:
        """获取用水月报，拉取全部页面直到跨出当年"""
        current_year = str(datetime.now().year)
        all_records = []
        page = 1
        while page <= 20:  # 安全上限，防止脏数据死循环
            records = await self.api.fetch_usage_records(page=page)
            if not records:
                break
            all_records.extend(records)
            last_ym = records[-1].get("ysny", "")
            if not last_ym or not last_ym.startswith(current_year):
                break
            page += 1
        if not all_records:
            return {}
        latest = all_records[0]
        raw_month = latest.get("ysny", "")
        # "202604" → "2026年4月"
        formatted_month = f"{raw_month[:4]}年{int(raw_month[4:])}月" if len(raw_month) == 6 and raw_month.isdigit() else raw_month
        raw_reading = latest.get("bybs")
        # 读数转数值（API返回字符串如 "659"）
        try:
            numeric_reading = float(raw_reading) if raw_reading is not None else None
        except (ValueError, TypeError):
            numeric_reading = raw_reading
        return {
            "latest_reading_month": formatted_month,
            "latest_reading": numeric_reading,
            "current_usage": float(latest.get("sl", 0)),
            "current_bill": float(latest.get("hjfy", 0)),
            "_usage_records": all_records,
        }

    async def _fetch_payment(self) -> dict:
        """获取最新缴费记录（type=2, page=1）"""
        records = await self.api.fetch_payment_records(page=1)
        if not records:
            return {}
        latest = records[0]
        bcye = float(latest.get("bcye", 0))
        return {
            "balance": bcye,
            "last_payment_date": latest.get("sfsj", "")[:10] if latest.get("sfsj") else None,
            "last_payment_amount": float(latest.get("jfje", 0)),
            "_payment_records": records,
        }

    def _merge_data(self, usage: dict, payment: dict) -> dict:
        current_year = str(datetime.now().year)
        annual = 0.0
        annual_bill = 0.0
        for rec in usage.get("_usage_records", []):
            ym = rec.get("ysny", "")
            if ym and ym.startswith(current_year):
                annual += float(rec.get("sl", 0))
                annual_bill += float(rec.get("hjfy", 0))
        merged = {
            "balance": payment.get("balance", 0.0),
            "last_payment_date": payment.get("last_payment_date"),
            "last_payment_amount": payment.get("last_payment_amount", 0.0),
            "current_usage": usage.get("current_usage", 0.0),
            "current_bill": usage.get("current_bill", 0.0),
            "latest_reading": usage.get("latest_reading"),
            "latest_reading_month": usage.get("latest_reading_month"),
            "annual_usage": round(annual, 2),
            "annual_bill": round(annual_bill, 2),
            "_year": current_year,  # 供 sensor 层读取当前年份
        }
        _LOGGER.debug("合并数据: %s", merged)
        return merged


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = ZhangjiajieWaterCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok