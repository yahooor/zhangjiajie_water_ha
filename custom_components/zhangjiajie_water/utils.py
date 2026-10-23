"""张家界供水 集成纯函数工具

刻意不依赖 homeassistant，便于在 CI 中直接单元测试。
"""
from __future__ import annotations

import logging
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
