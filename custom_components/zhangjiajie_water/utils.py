"""张家界供水 集成纯函数工具

刻意不依赖 homeassistant，便于在 CI 中直接单元测试。
"""
from __future__ import annotations

import logging
import math
from datetime import datetime
from zoneinfo import ZoneInfo

_LOGGER = logging.getLogger(__name__)
TZ_SHANGHAI = ZoneInfo("Asia/Shanghai")


def safe_float(value, default: float | None = 0.0) -> float | None:
    """安全转换 float，非法值返回 default"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def format_reading_month(raw: str) -> str:
    """账单月份格式化："202604" → "2026年4月"，非法格式原样返回"""
    if len(raw) == 6 and raw.isdigit():
        return f"{raw[:4]}年{int(raw[4:])}月"
    return raw


def parse_payment_datetime(raw: str) -> datetime | None:
    """解析交费时间（Asia/Shanghai 时区）。

    兼容三种格式："2026-04-06 15:30" / 带秒或毫秒 / 纯日期。
    无法解析时返回 None 并记录告警。
    """
    stripped = (raw or "").strip()
    if not stripped:
        return None
    try:
        if len(stripped) > 16:
            # 带秒/毫秒: "2026-05-03 07:51:14" 或 "2026-05-03 07:51:14.0"
            return datetime.strptime(stripped[:19], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=TZ_SHANGHAI
            )
        if len(stripped) > 10:
            return datetime.strptime(stripped, "%Y-%m-%d %H:%M").replace(
                tzinfo=TZ_SHANGHAI
            )
        return datetime.strptime(stripped, "%Y-%m-%d").replace(tzinfo=TZ_SHANGHAI)
    except ValueError:
        _LOGGER.warning("交费时间格式无法解析: %s", raw)
        return None


def year_records(records: list, year: str) -> list:
    """过滤出指定年份（ysny 前缀匹配）的用水记录"""
    return [r for r in records if str(r.get("ysny", "")).startswith(year)]


def sum_annual(records: list, year: str) -> tuple[float, float]:
    """统计指定年份的（累计用水量, 累计费用）"""
    usage = 0.0
    bill = 0.0
    for rec in year_records(records, year):
        usage += safe_float(rec.get("sl", 0), 0.0) or 0.0
        bill += safe_float(rec.get("hjfy", 0), 0.0) or 0.0
    return round(usage, 2), round(bill, 2)


def derive_usage(first_page: list, year_filtered: list, current_year: str) -> dict:
    """从用水记录派生全部展示数据（纯函数，供 fixtures 测试）。

    - first_page: API 首页原始记录（最新在前，未过滤，供取"上一期"）
    - year_filtered: 本年过滤后的记录（供年累计与历史属性）
    - 跨年空窗：本年无记录时回退 first_page[0]
    """
    if not first_page:
        return {}
    latest = year_filtered[0] if year_filtered else first_page[0]
    raw_month = str(latest.get("ysny", ""))
    formatted_month = format_reading_month(raw_month)
    numeric_reading = _int_or_float(latest.get("bybs"))
    prev_reading = _int_or_float(latest.get("sybs"))
    current_usage = safe_float(latest.get("sl"), 0.0)
    # 抄表自检：本期读数 − 上期读数 应约等于本期用量
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
    # 上一期账单（首页第二条，取原始记录，跨年也正确）
    prev_rec: dict = first_page[1] if len(first_page) > 1 else {}
    prev_usage = safe_float(prev_rec.get("sl"), None)
    return {
        "latest_reading_month": formatted_month,
        "_latest_ym": raw_month,
        "latest_reading": numeric_reading,
        "current_month_reading": numeric_reading,
        "previous_month_reading": prev_reading,
        "current_usage": current_usage,
        "previous_usage": prev_usage,
        "previous_usage_month": format_reading_month(str(prev_rec.get("ysny", ""))),
        "previous_bill": safe_float(prev_rec.get("hjfy"), None),
        "current_bill": safe_float(latest.get("hjfy"), 0.0),
        "current_water_fee": safe_float(latest.get("sf"), 0.0),
        "other_fees": safe_float(latest.get("qtxm"), 0.0),
        "sewage_fee": safe_float(latest.get("wsclf"), 0.0),
        "garbage_fee": safe_float(latest.get("ljclf"), 0.0),
        "_usage_records": year_filtered,
    }


def _int_or_float(value) -> float | int | None:
    """解析读数：整数值返回 int；NaN/Inf 等毒值返回 None（不可进长期统计）"""
    num = safe_float(value, None)
    if num is None or not math.isfinite(num):
        return None
    if num.is_integer():
        return int(num)
    return num


def derive_payment(records: list) -> dict:
    """从缴费记录派生数据（纯函数）。首页第一条即最新结算。"""
    if not records:
        return {}
    latest = records[0]
    raw_sfsj = latest.get("sfsj", "")
    return {
        "balance": safe_float(latest.get("bcye"), 0.0),
        "previous_balance": safe_float(latest.get("scye"), 0.0),
        "invoice_code": latest.get("kphm", ""),
        "last_payment_date": raw_sfsj[:10] if raw_sfsj else None,
        "last_payment_time": parse_payment_datetime(raw_sfsj),
        "last_payment_amount": safe_float(latest.get("jfje"), 0.0),
        "_payment_records": records,
    }


def detect_revision(
    prev_latest: tuple[str, float | int | None] | None,
    derived: dict,
) -> dict | None:
    """账单修订检测（纯函数）：同一账单月份的抄表读数被上游改动时返回修订信息。

    上游修订已出账单的读数会导致长期统计出现"假重置"——调用方据此告警。
    """
    if prev_latest is None:
        return None
    prev_ym, prev_reading = prev_latest
    ym = derived.get("_latest_ym", "")
    reading = derived.get("latest_reading")
    if (
        prev_ym == ym
        and prev_reading is not None
        and reading is not None
        and abs(float(prev_reading) - float(reading)) > 1e-9
    ):
        return {
            "month": derived.get("latest_reading_month"),
            "old": prev_reading,
            "new": reading,
        }
    return None
