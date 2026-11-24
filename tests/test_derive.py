"""derive_usage / derive_payment / detect_revision 的 fixtures 测试。

常规账单与缴费样本为独立构造的合成数据，仍使用 tests/fixtures/real/ 的
历史路径；独立构造的边缘样本在 tests/fixtures/synthetic/。加载方式与 test_utils 相同：
importlib 按路径加载，绕过集成包 __init__（依赖 homeassistant）。
"""
import importlib.util
import json
from datetime import datetime
from itertools import pairwise
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

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> list:
    for sub in ("real", "synthetic"):
        p = FIXTURES / sub / name
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError(name)


# ---- 合成常规账页：2042 年 1–10 月及上一年末 ----


def test_synthetic_usage_derivation_golden():
    records = load("usage_records_page1.json")
    d = utils.derive_usage(records, utils.year_records(records, "2042"), "2042")
    assert d["latest_reading"] == 4266
    assert d["previous_month_reading"] == 4243
    assert d["current_usage"] == 23.0
    assert d["current_bill"] == 39.10
    assert d["current_water_fee"] == 29.21
    assert d["other_fees"] == 9.89
    assert records[0]["wsclf"] == ""  # 上游缺值回退为 0.0
    assert d["sewage_fee"] == 0.0
    assert d["garbage_fee"] == 0.0
    assert d["latest_reading_month"] == "2042年10月"
    assert d["previous_usage"] == 21.0
    assert d["previous_bill"] == 35.70
    assert d["previous_usage_month"] == "2042年9月"
    # 年内历史保留且沿用 API 由新到旧的顺序；跨年记录不混入。
    assert [r["ysny"] for r in d["_usage_records"]] == [
        f"2042{month:02d}" for month in range(10, 0, -1)
    ]
    assert d["_latest_ym"] == "204210"


def test_synthetic_reading_delta_matches_billed_usage_every_month():
    """对账不变式：每个月 抄表差(bybs-sybs) == 账单用量(sl)"""
    records = load("usage_records_page1.json")
    for rec in records:
        delta = float(rec["bybs"]) - float(rec["sybs"])
        billed = float(rec["sl"])
        assert abs(delta - billed) <= 0.05, f"{rec['ysny']}: delta={delta} billed={billed}"


def test_synthetic_annual_sums():
    records = load("usage_records_page1.json")
    assert utils.sum_annual(records, "2042") == (138.0, 234.60)
    assert utils.sum_annual(records, "2041") == (8.0, 13.60)


def test_synthetic_payment_derivation_golden():
    records = load("payment_records_page1.json")
    d = utils.derive_payment(records)
    # 最新一笔是账单自动扣款（jfje=0，实际扣款 = 结余差）。
    assert d["last_payment_date"] == "2042-10-14"
    assert d["last_payment_amount"] == 0.0
    assert d["balance"] == 180.30
    assert d["previous_balance"] == 219.40
    assert d["invoice_code"] == "SYNTHETIC-AUTO-204210"
    # ".0" 后缀时间戳正确解析为带时区 datetime。
    assert d["last_payment_time"] == datetime(
        2042, 10, 14, 9, 27, 41, tzinfo=utils.TZ_SHANGHAI
    )
    assert abs((d["previous_balance"] - d["balance"]) - 39.10) <= 0.005
    timestamps = [r["sfsj"] for r in d["_payment_records"]]
    assert len(timestamps) == len(set(timestamps)) == 17
    assert timestamps == sorted(timestamps, reverse=True)


def test_payment_attributes_distinguish_accounting_month_and_payment_time():
    records = [
        {"xzyf": "20400531", "sfsj": "2040-06-01 04:30:00", "jfje": 0, "scye": 25.0, "bcye": 10.0},
        {"xzyf": "204005", "sfsj": "2040-05-19 20:05:00", "jfje": 24, "scye": 1.0, "bcye": 25.0},
        {"xzyf": "20400230", "sfsj": "2040-02-01 04:30:00", "jfje": 0},
        {"sfsj": "2040-01-01 04:30:00", "jfje": 0},
    ]
    attributes = utils.payment_history_attributes({"_payment_records": records})
    rows = attributes["recent_payments"]
    assert attributes["last_settlement_month"] == "2040-05"
    assert [r.get("settlement_month") for r in rows] == ["2040-05", "2040-05", None, None]
    assert rows[0]["time"] == "2040-06-01 04:30:00"
    assert rows[0]["amount"] == 0 and rows[0]["balance_change"] == -15
    assert "settlement_month" not in rows[-1]
    assert utils.payment_history_attributes({})["recent_payments"] == []


def test_synthetic_payment_invariants_by_type():
    """对账不变式（按记录类型分列）：

    - 自动扣款（jfje=0）：结余下降额 == 对应月份账单合计
    - 人工缴费（jfje>0）：结余上升额 == 缴费金额
    """
    payments = load("payment_records_page1.json")
    usage = load("usage_records_page1.json")
    bills = {r["ysny"]: float(r["hjfy"]) for r in usage}
    auto_months = []
    manual = 0
    for p in payments:
        ym = str(p.get("xzyf", ""))[:6]
        jfje = float(p["jfje"] or 0)
        down = float(p["scye"]) - float(p["bcye"])  # 正 = 扣款，负 = 充值
        if jfje == 0:
            assert abs(down - bills[ym]) <= 0.05, f"{ym}: {down} vs {bills[ym]}"
            auto_months.append(ym)
        else:
            assert jfje > 0
            assert abs(-down - jfje) <= 0.05, f"{p['xzyf']}: {-down} vs {jfje}"
            manual += 1
    assert auto_months == list(bills)
    assert manual == 6
    for newer, older in pairwise(payments):
        assert newer["scye"] == older["bcye"]


# ---- 边缘用例 ----


def test_cross_year_page_previous_falls_back_to_last_year():
    records = load("usage_cross_year.json")
    year_records = utils.year_records(records, "2073")
    d = utils.derive_usage(records, year_records, "2073")
    assert d["latest_reading"] == 5855
    assert d["latest_reading_month"] == "2073年1月"
    # 上一期是去年 12 月：取原始记录而非本年过滤列表。
    assert [rec["ysny"] for rec in d["_usage_records"]] == ["207301"]
    assert d["previous_usage"] == 26.0
    assert d["previous_usage_month"] == "2072年12月"
    assert d["previous_bill"] == 59.80


def test_revised_reading_detects_revision():
    records = load("usage_revised_reading.json")
    d = utils.derive_usage(records, utils.year_records(records, "2075"), "2075")
    prev = ("207508", 6571)
    rev = utils.detect_revision(prev, d)
    assert rev == {"month": "2075年8月", "old": 6571, "new": 6563}


def test_no_revision_when_new_bill_arrives():
    records = load("usage_records_page1.json")
    d = utils.derive_usage(records, utils.year_records(records, "2042"), "2042")
    # 上一轮是上个月账单（不同 ysny）→ 不是修订
    assert utils.detect_revision(("204209", 4243), d) is None
    # 首轮（无历史）→ 不是修订
    assert utils.detect_revision(None, d) is None


def test_dirty_string_numbers():
    records = load("usage_dirty_strings.json")
    d = utils.derive_usage(records, utils.year_records(records, "2074"), "2074")
    assert records[0]["bybs"] == "9147.00"
    assert records[0]["sybs"] == "009128.0"
    assert d["latest_reading"] == 9147
    assert d["previous_month_reading"] == 9128
    assert d["current_usage"] == 19.0
    assert records[0]["wsclf"] == ""
    assert d["sewage_fee"] == 0.0  # 空串回退为 0.0


def test_empty_records():
    assert utils.derive_usage([], [], "2073") == {}
    assert utils.derive_payment([]) == {}


def test_annual_empty_in_cross_year_january():
    """1 月初：本年无记录时年累计为 0，但展示数据回退最近一条。"""
    records = [{"ysny": "207612", "sybs": "7345", "bybs": "7374", "sl": "29",
                "sf": "40.60", "qtxm": "7.25", "hjfy": "47.85",
                "wsclf": "0.00", "ljclf": "0.00"}]
    current_year = "2077"
    d = utils.derive_usage(records, utils.year_records(records, current_year), current_year)
    assert d["latest_reading"] == 7374
    assert d["latest_reading_month"] == "2076年12月"
    assert d["_usage_records"] == []
    assert utils.sum_annual(records, current_year) == (0.0, 0.0)
    assert utils.sum_annual(d["_usage_records"], current_year) == (0.0, 0.0)


def test_nan_reading_does_not_crash():
    rec = {"ysny": "207809", "sybs": "nan", "bybs": "inf", "sl": "31",
           "sf": "0.00", "qtxm": "0.00", "hjfy": "0.00", "wsclf": "0.00", "ljclf": "0.00"}
    d = utils.derive_usage([rec], [rec], "2078")
    assert d["current_usage"] == 31.0
    # 毒值（NaN/Inf）不进长期统计：读数归 None 而非崩溃或透传
    assert d["latest_reading"] is None
    assert d["previous_month_reading"] is None
