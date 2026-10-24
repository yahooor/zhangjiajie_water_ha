"""张家界供水 DataUpdateCoordinator（混合刷新模式）"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ZhangjiajieWaterAPI, ZhangjiajieWaterApiAuthError
from .const import (
    CONF_DAILY_HOUR,
    CONF_DAILY_MINUTE,
    CONF_UPDATE_MODE,
    DOMAIN,
    INTEGRATION_VERSION,
    UPDATE_MODE_DAILY,
    UPDATE_MODE_INTERVAL,
)
from .utils import (
    TZ_SHANGHAI as _TZ_SHANGHAI,
)
from .utils import (
    format_reading_month,
    parse_payment_datetime,
    sum_annual,
    year_records,
)
from .utils import (
    safe_float as _safe_float,
)

_LOGGER = logging.getLogger(__name__)


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
        """注册每日定时监听器 + 首次刷新。

        监听器必须先于首刷注册：首刷失败被上层捕获后继续运行，
        若放在首刷之后，"每日定时"模式会因启动时 API 故障而整天不刷新。
        """
        self._register_daily_listener()
        await super().async_config_entry_first_refresh()

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
        def _daily_refresh(now: datetime) -> None:
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
        except ZhangjiajieWaterApiAuthError as e:
            # 户号/OpenID 被服务端拒绝：抛出后 DataUpdateCoordinator 会自动
            # 对 config entry 发起重新认证（reauth）流程
            raise ConfigEntryAuthFailed(f"户号或 OpenID 未通过服务端验证: {e}") from e
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
        """获取用水月报：优先本年记录，本年无记录时回退最近一条（跨年空窗）"""
        current_year = str(datetime.now(_TZ_SHANGHAI).year)
        all_records: list = []
        first_page: list = []  # 首页原始记录（未过滤，最新在前），供"上月用量"取上一期
        latest_any: dict | None = None  # 全部记录中最 new 的一条（跨年回退用）
        page = 1
        while page <= 20:  # 安全上限，防止脏数据死循环
            records = await self.api.fetch_usage_records(page=page)
            if not records:
                break
            if page == 1:
                first_page = records
            if latest_any is None:
                latest_any = records[0]
            # 逐条过滤，只保留本年记录（一页可能跨年）
            all_records.extend(year_records(records, current_year))
            # 本页最旧记录已跨年，后续页更旧，停止翻页
            last_ym = records[-1].get("ysny", "")
            if not last_ym or not str(last_ym).startswith(current_year):
                break
            page += 1
        if latest_any is None:
            return {}
        # 本年尚无账单（如 1 月初）时回退最近一条跨年记录，避免读数/用量显示空窗；
        # 年累计统计仍只按本年记录计算（空列表 = 0）
        latest = all_records[0] if all_records else latest_any
        if not all_records:
            _LOGGER.info(
                "本年（%s）暂无用水记录，回退显示最近一条（%s）",
                current_year,
                latest.get("ysny", ""),
            )
        raw_month = str(latest.get("ysny", ""))
        formatted_month = format_reading_month(raw_month)
        raw_reading = latest.get("bybs")
        numeric_reading = _safe_float(raw_reading, default=None)
        # is_integer() 对 NaN/Inf 返回 False，避免 int(nan) 抛 ValueError 拖垮整次更新
        if numeric_reading is not None and numeric_reading.is_integer():
            numeric_reading = int(numeric_reading)
        raw_prev_reading = latest.get("sybs")
        prev_reading = _safe_float(raw_prev_reading, default=None)
        if prev_reading is not None and prev_reading.is_integer():
            prev_reading = int(prev_reading)
        current_usage = _safe_float(latest.get("sl"), 0.0)
        # 抄表自检：本期读数 − 上期读数 应约等于本期用量，不符则告警提示抄表异常
        if (
            numeric_reading is not None
            and prev_reading is not None
            and abs(float(numeric_reading) - float(prev_reading) - current_usage) > 0.05
        ):
            _LOGGER.warning(
                "抄表数据自检不一致（%s）: 本期读数 %s − 上期读数 %s ≠ 本期用量 %s，"
                "请核对供水公司账单",
                formatted_month,
                numeric_reading,
                prev_reading,
                current_usage,
            )
        # 上月用量 = 最新账单的上一期（首页第二条；取原始记录，跨年也正确）
        prev_rec: dict = first_page[1] if len(first_page) > 1 else {}
        prev_usage_month = format_reading_month(str(prev_rec.get("ysny", "")))
        prev_usage = _safe_float(prev_rec.get("sl"), None)
        prev_bill = _safe_float(prev_rec.get("hjfy"), None)
        return {
            "latest_reading_month": formatted_month,
            "latest_reading": numeric_reading,
            "current_month_reading": numeric_reading,
            "previous_month_reading": prev_reading,
            "current_usage": current_usage,
            "previous_usage": prev_usage,
            "previous_usage_month": prev_usage_month,
            "previous_bill": prev_bill,
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
        raw_sfsj = latest.get("sfsj", "")
        return {
            "balance": _safe_float(latest.get("bcye"), 0.0),
            "previous_balance": _safe_float(latest.get("scye"), 0.0),
            "invoice_code": latest.get("kphm", ""),
            "last_payment_date": raw_sfsj[:10] if raw_sfsj else None,
            "last_payment_time": parse_payment_datetime(raw_sfsj),
            "last_payment_amount": _safe_float(latest.get("jfje"), 0.0),
            "_payment_records": records,
        }

    def _merge_data(self, usage: dict, payment: dict) -> dict:
        current_year = str(datetime.now(_TZ_SHANGHAI).year)
        annual, annual_bill = sum_annual(usage.get("_usage_records", []), current_year)
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
            # 原始记录供 sensor 层 attributes_fn 使用（逐月历史/最近缴费）
            "_usage_records": usage.get("_usage_records", []),
            "_payment_records": payment.get("_payment_records", []),
        }
        _LOGGER.debug("合并数据: %s", merged)
        return merged
