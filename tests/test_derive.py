"""derive_usage / derive_payment / detect_revision 的 fixtures 测试。

真实 fixture 来自实机协调器诊断（tests/fixtures/real/），边缘用例在
tests/fixtures/synthetic/。加载方式与 test_utils 相同：importlib 按路径
加载，绕过集成包 __init__（依赖 homeassistant）。
"""
import importlib.util
import json
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

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> list:
    for sub in ("real", "synthetic"):
        p = FIXTURES / sub / name
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError(name)


# ---- 真实数据：2026 年 1-10 月完整账单 ----


def test_real_usage_derivation_golden():
    records = load("usage_records_page1.json")
    d = utils.derive_usage(records, utils.year_records(records, "2026"), "2026")
    # 实机核对过的黄金值（2026-10 账单）
    assert d["latest_reading"] == 756
    assert d["previous_month_reading"] == 741
    assert d["current_usage"] == 15.0
    assert d["current_bill"] == 69.30
    assert d["current_water_fee"] == 28.35
    assert d["other_fees"] == 40.95
    assert d["sewage_fee"] == 0.0
    assert d["garbage_fee"] == 0.0
    assert d["latest_reading_month"] == "2026年10月"
    # 上一期 = 202609
    assert d["previous_usage"] == 18.0
    assert d["previous_bill"] == 83.16
    assert d["previous_usage_month"] == "2026年9月"
    # 历史记录完整保留
    assert len(d["_usage_records"]) == 10
    assert d["_latest_ym"] == "202610"


def test_real_reading_delta_matches_billed_usage_every_month():
    """对账不变式：每个月 抄表差(bybs-sybs) == 账单用量(sl)"""
    records = load("usage_records_page1.json")
    for rec in records:
        delta = float(rec["bybs"]) - float(rec["sybs"])
        billed = float(rec["sl"])
        assert abs(delta - billed) <= 0.05, f"{rec['ysny']}: delta={delta} billed={billed}"


def test_real_annual_sums():
    records = load("usage_records_page1.json")
    usage, bill = utils.sum_annual(records, "2026")
    assert usage == round(sum(float(r["sl"]) for r in records), 2)
    assert bill == round(sum(float(r["hjfy"]) for r in records), 2)


def test_real_payment_derivation_golden():
    records = load("payment_records_page1.json")
    d = utils.derive_payment(records)
    # 最新一笔：2026-10-03 账单自动扣款（jfje=0，实际扣款 = 结余差）
    assert d["last_payment_date"] == "2026-10-03"
    assert d["last_payment_amount"] == 0.0
    assert d["balance"] == 103.36
    assert d["previous_balance"] == 172.66
    # ".0" 后缀时间戳正确解析为带时区 datetime
    assert d["last_payment_time"] == datetime(
        2026, 10, 3, 4, 16, 58, tzinfo=utils.TZ_SHANGHAI
    )
    # 余额差 = 202610 账单合计（三方对账的第三条边）
    assert abs((d["previous_balance"] - d["balance"]) - 69.30) <= 0.005


def test_real_payment_invariants_by_type():
    """对账不变式（按记录类型分列）：

    - 自动扣款（jfje=0）：结余下降额 == 对应月份账单合计
    - 人工缴费（jfje>0）：结余上升额 == 缴费金额
    """
    payments = load("payment_records_page1.json")
    usage = load("usage_records_page1.json")
    bills = {r["ysny"]: float(r["hjfy"]) for r in usage}
    auto = manual = 0
    for p in payments:
        ym = str(p.get("xzyf", ""))[:6]
        jfje = float(p["jfje"] or 0)
        down = float(p["scye"]) - float(p["bcye"])  # 正 = 扣款，负 = 充值
        if jfje == 0:
            assert abs(down - bills[ym]) <= 0.05, f"{ym}: {down} vs {bills[ym]}"
            auto += 1
        else:
            assert abs(-down - jfje) <= 0.05, f"{p['xzyf']}: {-down} vs {jfje}"
            manual += 1
    assert auto >= 5 and manual >= 5


# ---- 边缘用例 ----


def test_cross_year_page_previous_falls_back_to_last_year():
    records = load("usage_cross_year.json")
    d = utils.derive_usage(records, utils.year_records(records, "2026"), "2026")
    assert d["latest_reading"] == 756
    # 上一期是去年 12 月：取原始记录而非本年过滤列表
    assert d["previous_usage"] == 18.0
    assert d["previous_usage_month"] == "2025年12月"
    assert d["previous_bill"] == 83.16


def test_revised_reading_detects_revision():
    records = load("usage_revised_reading.json")
    d = utils.derive_usage(records, utils.year_records(records, "2026"), "2026")
    prev = ("202610", 756)
    rev = utils.detect_revision(prev, d)
    assert rev == {"month": "2026年10月", "old": 756, "new": 750}


def test_no_revision_when_new_bill_arrives():
    records = load("usage_records_page1.json")
    d = utils.derive_usage(records, utils.year_records(records, "2026"), "2026")
    # 上一轮是上个月账单（不同 ysny）→ 不是修订
    assert utils.detect_revision(("202609", 741), d) is None
    # 首轮（无历史）→ 不是修订
    assert utils.detect_revision(None, d) is None


def test_dirty_string_numbers():
    records = load("usage_dirty_strings.json")
    d = utils.derive_usage(records, utils.year_records(records, "2026"), "2026")
    assert d["latest_reading"] == 756  # "756.00"
    assert d["previous_month_reading"] == 741  # "0741.0"
    assert d["current_usage"] == 15.0
    assert d["sewage_fee"] == 0.0  # 空串 → default 0.0


def test_empty_records():
    assert utils.derive_usage([], [], "2026") == {}
    assert utils.derive_payment([]) == {}


def test_annual_empty_in_cross_year_january():
    """1 月初：本年无记录时年累计为 0，但展示数据回退最近一条"""
    jan_only = [{"ysny": "202512", "sybs": "723", "bybs": "741", "sl": "18",
                 "sf": "33.84", "qtxm": "49.32", "hjfy": "83.16",
                 "wsclf": "0", "ljclf": "0"}]
    d = utils.derive_usage(jan_only, utils.year_records(jan_only, "2026"), "2026")
    assert d["latest_reading"] == 741
    usage, bill = utils.sum_annual(d["_usage_records"], "2026")
    assert usage == 0.0 and bill == 0.0


def test_nan_reading_does_not_crash():
    rec = {"ysny": "202610", "sybs": "nan", "bybs": "inf", "sl": "15",
           "sf": "0", "qtxm": "0", "hjfy": "0", "wsclf": "0", "ljclf": "0"}
    d = utils.derive_usage([rec], [rec], "2026")
    # 毒值（NaN/Inf）不进长期统计：读数归 None 而非崩溃或透传
    assert d["latest_reading"] is None
    assert d["previous_month_reading"] is None
