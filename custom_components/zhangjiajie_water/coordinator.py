"""张家界供水 DataUpdateCoordinator（混合刷新模式）"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.device_registry import DeviceInfo

from .api import ZhangjiajieWaterAPI
from .const import (
    DOMAIN,
    INTEGRATION_VERSION,
    CONF_UPDATE_MODE,
    CONF_DAILY_HOUR,
    CONF_DAILY_MINUTE,
    UPDATE_MODE_DAILY,
    UPDATE_MODE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)
_TZ_SHANGHAI = ZoneInfo("Asia/Shanghai")


def _safe_float(value, default: float | None = 0.0) -> float | None:
    """安全转换 float，非法值返回 default"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class ZhangjiajieWaterCoordinator(DataUpdateCoordinator):
    """数据协调器，支持每日定时与固定间隔两种刷新模式。"""

    _CONSECUTIVE_FAILURES_NOTIFY = 3  # 连续失败 N 次后发送通知

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        update_mode = entry.options.get(CONF_UPDATE_MODE, UPDATE_MODE_INTERVAL)
        update_interval = entry.options.get("update_interval", 6)

        # 每日定时模式下 update_interval 设为 None（禁用轮询，由事件驱动）
        poll_interval = None if update_mode == UPDATE_MODE_DAILY else timedelta(hours=update_interval)

        _LOGGER.debug(
            "[Coordinator] 初始化: 户号=%s, 模式=%s, 轮询间隔=%s, options=%s",
            entry.data.get("account_no"),
            update_mode,
            poll_interval,
            dict(entry.options),
        )
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {entry.data['account_no']}",
            update_interval=poll_interval,
            config_entry=entry,
        )
        self.entry = entry
        self.api = ZhangjiajieWaterAPI(
            account_no=entry.data["account_no"],
            openid=entry.data["openid"],
            hass=hass,
        )
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data["account_no"])},
            manufacturer="张家界市自来水有限责任公司",
            name=entry.data.get("account_name", entry.data["account_no"]),
            model="智能水表",
            sw_version=INTEGRATION_VERSION,
        )
        self._consecutive_failures = 0
        self._notification_sent = False
        self._daily_unsub = None  # async_track_time_change 的取消回调

    async def async_config_entry_first_refresh(self) -> None:
        """首次刷新 + 注册每日定时监听器。"""
        await super().async_config_entry_first_refresh()
        self._register_daily_listener()

    def _register_daily_listener(self) -> None:
        """根据 options 决定是否注册每日定时刷新。"""
        # 先清理旧监听器（选项变更时也会调用）
        if self._daily_unsub is not None:
            self._daily_unsub()
            self._daily_unsub = None

        update_mode = self.entry.options.get(CONF_UPDATE_MODE, UPDATE_MODE_INTERVAL)
        if update_mode != UPDATE_MODE_DAILY:
            return

        hour = int(self.entry.options.get(CONF_DAILY_HOUR, 7))
        minute = int(self.entry.options.get(CONF_DAILY_MINUTE, 30))

        @callback
        def _daily_refresh(now: datetime) -> None:  # noqa: ARG001
            """每日定时回调：触发协调器刷新。"""
            _LOGGER.debug("[Coordinator] 每日定时刷新触发 (%02d:%02d)", hour, minute)
            self.hass.async_create_task(self.async_request_refresh())

        self._daily_unsub = async_track_time_change(
            self.hass,
            _daily_refresh,
            hour=hour,
            minute=minute,
            second=0,
        )
        _LOGGER.info(
            "[Coordinator] 已注册每日定时刷新: %02d:%02d", hour, minute
        )

    async def async_shutdown(self) -> None:
        """卸载时清理监听器并关闭 API。"""
        if self._daily_unsub is not None:
            self._daily_unsub()
            self._daily_unsub = None
        await self.api.async_close()
        await super().async_shutdown()

    async def _async_update_data(self) -> dict:
        _LOGGER.debug("[Coordinator] _async_update_data 开始执行")
        try:
            usage, payment = await asyncio.gather(
                self._fetch_usage(),
                self._fetch_payment(),
            )
            data = self._merge_data(usage, payment)
            _LOGGER.debug("[Coordinator] _async_update_data 成功，数据: %s", data)
            # 成功时重置失败计数
            self._consecutive_failures = 0
            if self._notification_sent:
                self._notification_sent = False
                self.hass.async_create_task(
                    self.hass.services.async_call(
                        "persistent_notification",
                        "dismiss",
                        {"notification_id": f"{DOMAIN}_api_error_{self.entry.entry_id}"},
                    )
                )
            return data
        except UpdateFailed:
            raise
        except Exception as e:
            self._consecutive_failures += 1
            if (
                self._consecutive_failures >= self._CONSECUTIVE_FAILURES_NOTIFY
                and not self._notification_sent
            ):
                self._notification_sent = True
                self.hass.async_create_task(self._send_error_notification(str(e)))
            raise UpdateFailed(f"数据更新失败: {e}") from e

    async def _send_error_notification(self, error_msg: str) -> None:
        """发送 API 持续失败通知"""
        account = self.entry.data.get("account_name", self.entry.data["account_no"])
        try:
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": f"⚠️ 张家界供水数据更新失败（{account}）",
                    "message": (
                        f"连续 {self._consecutive_failures} 次数据刷新失败。\n\n"
                        f"**错误信息**: {error_msg}\n\n"
                        "可能原因：\n"
                        "- 网络连接问题\n"
                        "- 供水公司 API 服务异常\n"
                        "- OpenID 或户号变更\n\n"
                        "如果问题持续，请尝试重新配置集成。"
                    ),
                    "notification_id": f"{DOMAIN}_api_error_{self.entry.entry_id}",
                },
                blocking=True,
            )
        except Exception as e:
            _LOGGER.warning("发送失败通知时出错: %s", e)

    async def _fetch_usage(self) -> dict:
        """获取用水月报，逐条过滤本年记录"""
        current_year = str(datetime.now(_TZ_SHANGHAI).year)
        all_records: list = []
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
        formatted_month = (
            f"{raw_month[:4]}年{int(raw_month[4:])}月"
            if len(raw_month) == 6 and raw_month.isdigit()
            else raw_month
        )
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
        # 解析交费时间（API 返回格式 "2026-04-06 15:30" 或 "2026-04-06"）
        raw_sfsj = latest.get("sfsj", "")
        payment_date = None
        payment_datetime = None
        if raw_sfsj:
            payment_date = raw_sfsj[:10]
            try:
                stripped = raw_sfsj.strip()
                if len(stripped) > 16:
                    # 带秒/毫秒: "2026-05-03 07:51:14" 或 "2026-05-03 07:51:14.0"
                    payment_datetime = datetime.strptime(stripped[:19], "%Y-%m-%d %H:%M:%S").replace(
                        tzinfo=_TZ_SHANGHAI
                    )
                elif len(stripped) > 10:
                    payment_datetime = datetime.strptime(stripped, "%Y-%m-%d %H:%M").replace(
                        tzinfo=_TZ_SHANGHAI
                    )
                else:
                    payment_datetime = datetime.strptime(stripped, "%Y-%m-%d").replace(
                        tzinfo=_TZ_SHANGHAI
                    )
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
        current_year = str(datetime.now(_TZ_SHANGHAI).year)
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
