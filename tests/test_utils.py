"""utils 纯函数单元测试（不依赖 homeassistant）

utils.py 位于集成包内，导入包会触发 __init__.py（依赖 homeassistant），
因此用 importlib 直接按文件路径加载，绕过包初始化。
"""
import importlib.util
import math
from datetime import datetime
from pathlib import Path

_UTILS_PATH = (
    Path(__file__).parent.parent
    / "custom_components"
    / "zhangjiajie_water"
    / "utils.py"
)
_spec = importlib.util.spec_from_file_location("zjw_utils", _UTILS_PATH)
utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(utils)

TZ_SHANGHAI = utils.TZ_SHANGHAI
format_reading_month = utils.format_reading_month
parse_payment_datetime = utils.parse_payment_datetime
safe_float = utils.safe_float
sum_annual = utils.sum_annual
year_records = utils.year_records

# ---- safe_float ----


def test_safe_float_normal():
    assert safe_float("1.5") == 1.5
    assert safe_float(3) == 3.0
    assert safe_float("0") == 0.0


def test_safe_float_invalid_returns_default():
    assert safe_float(None) == 0.0
    assert safe_float("") == 0.0
    assert safe_float("abc") == 0.0
    assert safe_float(None, default=None) is None
    assert safe_float("x", default=1.0) == 1.0


def test_safe_float_nan_passthrough():
    assert math.isnan(safe_float("nan"))


# ---- format_reading_month ----


def test_format_reading_month():
    assert format_reading_month("202604") == "2026年4月"
    assert format_reading_month("202611") == "2026年11月"


def test_format_reading_month_invalid_passthrough():
    assert format_reading_month("20261") == "20261"
    assert format_reading_month("") == ""
    assert format_reading_month("abcdef") == "abcdef"


# ---- parse_payment_datetime ----


def test_parse_payment_datetime_date_only():
    dt = parse_payment_datetime("2026-04-06")
    assert dt == datetime(2026, 4, 6, tzinfo=TZ_SHANGHAI)


def test_parse_payment_datetime_minute():
    dt = parse_payment_datetime("2026-04-06 15:30")
    assert dt == datetime(2026, 4, 6, 15, 30, tzinfo=TZ_SHANGHAI)


def test_parse_payment_datetime_seconds():
    assert parse_payment_datetime("2026-05-03 07:51:14") == datetime(
        2026, 5, 3, 7, 51, 14, tzinfo=TZ_SHANGHAI
    )
    # 毫秒后缀截断到秒
    assert parse_payment_datetime("2026-05-03 07:51:14.0") == datetime(
        2026, 5, 3, 7, 51, 14, tzinfo=TZ_SHANGHAI
    )


def test_parse_payment_datetime_invalid():
    assert parse_payment_datetime("") is None
    assert parse_payment_datetime(None) is None
    assert parse_payment_datetime("not a date") is None
    assert parse_payment_datetime("2026/04/06") is None


def test_parse_payment_datetime_strips_whitespace():
    assert parse_payment_datetime("  2026-04-06  ") == datetime(
        2026, 4, 6, tzinfo=TZ_SHANGHAI
    )


# ---- year_records / sum_annual ----

FIXTURE = [
    {"ysny": "202610", "sl": "4.2", "hjfy": "18.35"},
    {"ysny": "202609", "sl": "3.8", "hjfy": "16.90"},
    {"ysny": "202512", "sl": "5.0", "hjfy": "21.00"},  # 跨年记录
    {"ysny": "", "sl": "1.0", "hjfy": "2.0"},  # 脏数据
    {"sl": "9.9", "hjfy": "9.9"},  # 缺 ysny
]


def test_year_records_filters_by_prefix():
    got = year_records(FIXTURE, "2026")
    assert [r["ysny"] for r in got] == ["202610", "202609"]


def test_year_records_empty_year():
    assert year_records(FIXTURE, "2099") == []


def test_sum_annual():
    usage, bill = sum_annual(FIXTURE, "2026")
    assert usage == 8.0
    assert bill == 35.25


def test_sum_annual_no_records():
    assert sum_annual([], "2026") == (0.0, 0.0)
    assert sum_annual(FIXTURE, "2099") == (0.0, 0.0)


def test_sum_annual_tolerates_bad_numbers():
    records = [
        {"ysny": "202601", "sl": None, "hjfy": "x"},
        {"ysny": "202602", "sl": "1.1", "hjfy": "2.2"},
    ]
    usage, bill = sum_annual(records, "2026")
    assert usage == 1.1
    assert bill == 2.2
