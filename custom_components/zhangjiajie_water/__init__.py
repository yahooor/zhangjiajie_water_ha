from __future__ import annotations
import json
import logging
from datetime import datetime, timedelta, date, timezone
from zoneinfo import ZoneInfo
import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN, BASE_URL, API_PATH, INTEGRATION_VERSION
import asyncio

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]


_TZ_SHANGHAI = ZoneInfo("Asia/Shanghai")


def _safe_float(value, default: float = 0.0) -> float:
    """安全转换 float，非法值返回 default"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class ZhangjiajieWaterAPI:
    """张家界水务 API 客户端"""
    def __init__(self, account_no: str, openid: str):
        self.account_no = account_no
        self.openid = openid
        self.base_url = BASE_URL
        self.api_path = API_PATH
        self._session: aiohttp.ClientSession | None = None
        self._closed = False

    async def async_close(self) -> None:
        """关闭 HTTP session"""
        self._closed = True
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建复用的 ClientSession"""
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
        if self._closed:
            raise Exception("API 客户端已关闭")
        last_error = None
        for attempt in range(retries):
            non_retryable = False
            try:
                session = await self._get_session()
                async with session.post(url, data=form, headers=self.headers) as resp:
                    text = await resp.text()
                    if resp.status != 200:
                        raise Exception(f"API HTTP {resp.status}: {text[:200]}")
                try:
                    result = json.loads(text)
                except (json.JSONDecodeError, ValueError):
                    # 非 JSON 响应（如 502 网关错误页面），重试无意义
                    non_retryable = True
                    raise Exception(f"API 返回非 JSON 响应: {text[:200]}")
                if result.get("res") != 100:
                    msg = result.get("msg", "")
                    detail = f" - {msg}" if msg else ""
                    raise Exception(f"API 返回错误码 {result.get('res')}{detail}")
                return result
            except Exception as e:
                last_error = e
                if non_retryable or attempt >= retries - 1:
                    raise
                wait = 2 ** attempt
                _LOGGER.warning("API 请求失败 (第 %d/%d 次)，%d 秒后重试: %s", attempt + 1, retries, wait, e)
                await asyncio.sleep(wait)
        raise last_error


class ZhangjiajieWaterCoordinator(DataUpdateCoordinator):
    """数据协调器"""
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        update_interval = entry.options.get("update_interval", 6)
        _LOGGER.debug("[Coordinator] 初始化: 户号=%s, 轮询间隔=%d小时, options=%s, data=%s",
                     entry.data.get("account_no"), update_interval, dict(entry.options), dict(entry.data))
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {entry.data['account_no']}",
            update_interval=timedelta(hours=update_interval),
            config_entry=entry,
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
            sw_version=INTEGRATION_VERSION,
        )

    async def _async_update_data(self) -> dict:
        _LOGGER.debug("[Coordinator] _async_update_data 开始执行")
        try:
            usage, payment = await asyncio.gather(
                self._fetch_usage(),
                self._fetch_payment()
            )
            data = self._merge_data(usage, payment)
            _LOGGER.debug("[Coordinator] _async_update_data 成功，数据: %s", data)
            return data
        except Exception as e:
            _LOGGER.error("数据更新失败: %s", e)
            raise

    async def _fetch_usage(self) -> dict:
        """获取用水月报，逐条过滤本年记录"""
        current_year = str(datetime.now().year)
        all_records = []
        page = 1
        while page <= 20:  # 安全上限，防止脏数据死循环
            records = await self.api.fetch_usage_records(page=page)
            if not records:
                break
            # 逐条过滤，只保留本年记录（一页可能跨年）
            year_records = [r for r in records if r.get("ysny", "").startswith(current_year)]
            all_records.extend(year_records)
            # 本页最旧记录已跨年，后续页更旧，停止翻页
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
        numeric_reading = _safe_float(raw_reading, default=None)
        if numeric_reading is not None and numeric_reading == int(numeric_reading):
            numeric_reading = int(numeric_reading)
        raw_prev_reading = latest.get("sybs")
        prev_reading = _safe_float(raw_prev_reading, default=None)
        if prev_reading is not None and prev_reading == int(prev_reading):
            prev_reading = int(prev_reading)
        return {
            "latest_reading_month": formatted_month,
            "latest_reading": numeric_reading,
            "current_month_reading": numeric_reading,
            "previous_month_reading": prev_reading,
            "current_usage": _safe_float(latest.get("sl"), 0.0),
            "current_bill": _safe_float(latest.get("hjfy"), 0.0),
            "current_water_fee": _safe_float(latest.get("sf"), 0.0),
            "other_fees": _safe_float(latest.get("qtxm"), 0.0),
            "sewage_fee": _safe_float(latest.get("wsclf"), 0.0),
            "garbage_fee": _safe_float(latest.get("ljclf"), 0.0),
            "_usage_records": all_records,
        }

    async def _fetch_payment(self) -> dict:
        """获取最新缴费记录（type=2, page=1）"""
        records = await self.api.fetch_payment_records(page=1)
        if not records:
            return {}
        latest = records[0]
        bcye = _safe_float(latest.get("bcye"), 0.0)
        scye = _safe_float(latest.get("scye"), 0.0)
        # 解析交费时间（API返回格式 "2026-04-06 15:30" 或 "2026-04-06"）
        raw_sfsj = latest.get("sfsj", "")
        payment_date = None
        payment_datetime = None
        if raw_sfsj:
            payment_date = raw_sfsj[:10]
            try:
                stripped = raw_sfsj.strip()
                if len(stripped) > 16:
                    # 带秒/毫秒: "2026-05-03 07:51:14" 或 "2026-05-03 07:51:14.0"
                    payment_datetime = datetime.strptime(stripped[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=_TZ_SHANGHAI)
                elif len(stripped) > 10:
                    payment_datetime = datetime.strptime(stripped, "%Y-%m-%d %H:%M").replace(tzinfo=_TZ_SHANGHAI)
                else:
                    payment_datetime = datetime.strptime(stripped, "%Y-%m-%d").replace(tzinfo=_TZ_SHANGHAI)
            except ValueError:
                _LOGGER.warning("交费时间格式无法解析: %s", raw_sfsj)
        return {
            "balance": bcye,
            "previous_balance": scye,
            "invoice_code": latest.get("kphm", ""),
            "last_payment_date": payment_date,
            "last_payment_time": payment_datetime,
            "last_payment_amount": _safe_float(latest.get("jfje"), 0.0),
            "_payment_records": records,
        }

    def _merge_data(self, usage: dict, payment: dict) -> dict:
        current_year = str(datetime.now().year)
        annual = 0.0
        annual_bill = 0.0
        for rec in usage.get("_usage_records", []):
            ym = rec.get("ysny", "")
            if ym and ym.startswith(current_year):
                annual += _safe_float(rec.get("sl", 0))
                annual_bill += _safe_float(rec.get("hjfy", 0))
        merged = {
            "customer_code": self.entry.data.get("account_no", ""),
            "balance": payment.get("balance", 0.0),
            "previous_balance": payment.get("previous_balance", 0.0),
            "invoice_code": payment.get("invoice_code", ""),
            "last_payment_date": payment.get("last_payment_date"),
            "last_payment_time": payment.get("last_payment_time"),
            "last_payment_amount": payment.get("last_payment_amount", 0.0),
            "current_usage": usage.get("current_usage", 0.0),
            "current_bill": usage.get("current_bill", 0.0),
            "current_water_fee": usage.get("current_water_fee", 0.0),
            "other_fees": usage.get("other_fees", 0.0),
            "sewage_fee": usage.get("sewage_fee", 0.0),
            "garbage_fee": usage.get("garbage_fee", 0.0),
            "latest_reading": usage.get("latest_reading"),
            "latest_reading_month": usage.get("latest_reading_month"),
            "current_month_reading": usage.get("current_month_reading"),
            "previous_month_reading": usage.get("previous_month_reading"),
            "annual_usage": round(annual, 2),
            "annual_bill": round(annual_bill, 2),
            "_year": current_year,  # 供 sensor 层读取当前年份
        }
        _LOGGER.debug("合并数据: %s", merged)
        return merged


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = ZhangjiajieWaterCoordinator(hass, entry)

    # 首次刷新：如果失败，打印错误但继续（不让初始化彻底失败）
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.warning("首次数据刷新失败，协程将在下次轮询时重试: %s", err)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 正确清理：保存 undo 回调，卸载时调用它防止监听器泄漏
    unload_listener = entry.add_update_listener(_async_update_listener)
    entry.async_on_unload(unload_listener)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id, None)
        if coordinator and hasattr(coordinator, "api"):
            await coordinator.api.async_close()
    return unload_ok