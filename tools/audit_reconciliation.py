"""张家界供水 三方对账审计。

四条对账边：
  A. 抄表差 vs 账单用量:  bybs − sybs == sl（每条用水记录）
  B. 自动扣款 vs 账单:    scye − bcye == hjfy（jfje=0 的缴费记录，按 xzyf 月份匹配）
  C. 人工缴费 vs 金额:    bcye − scye == jfje（jfje>0 的缴费记录）
  D. 长期统计 vs 账单:    statistics 月度 change == sl（仅 --live 且统计已回填时）

用法：
  文件模式（CI）:  python tools/audit_reconciliation.py \
                     --usage tests/fixtures/real/usage_records_page1.json \
                     --payment tests/fixtures/real/payment_records_page1.json
  实机模式:        python tools/audit_reconciliation.py --live \
                     --entry-id <config_entry_id> [--statistic-id sensor.xxx]

退出码：0=全部一致；1=存在不一致；2=输入错误
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOLERANCE = 0.05


def fail(msg: str) -> None:
    print(f"  FAIL {msg}")


def ok(msg: str) -> None:
    print(f"  ok   {msg}")


def audit_records(usage: list, payment: list) -> int:
    """A/B/C 三边对账，返回失败数"""
    errors = 0
    bills_usage: dict[str, float] = {}   # ysny -> sl（账单用量）
    bills_total: dict[str, float] = {}   # ysny -> hjfy（账单合计，自动扣款额）
    print("A. 抄表差 vs 账单用量")
    for rec in usage:
        ym = str(rec.get("ysny", ""))
        try:
            delta = float(rec["bybs"]) - float(rec["sybs"])
            billed = float(rec["sl"])
            total = float(rec["hjfy"])
        except (KeyError, TypeError, ValueError) as e:
            fail(f"{ym}: 字段缺失/非法 ({e})")
            errors += 1
            continue
        bills_usage.setdefault(ym, billed)
        bills_total.setdefault(ym, total)
        if abs(delta - billed) <= TOLERANCE:
            ok(f"{ym}: {delta:g} == {billed:g}")
        else:
            fail(f"{ym}: 抄表差 {delta:g} != 账单用量 {billed:g}")
            errors += 1

    print("B/C. 缴费记录按类型对账")
    for p in payment:
        xzyf = str(p.get("xzyf", ""))
        ym = xzyf[:6]
        try:
            jfje = float(p.get("jfje") or 0)
            down = float(p["scye"]) - float(p["bcye"])  # 正 = 扣款
        except (KeyError, TypeError, ValueError) as e:
            fail(f"{xzyf}: 字段缺失/非法 ({e})")
            errors += 1
            continue
        if jfje == 0:  # 自动扣款：扣款额 == 该月账单合计（hjfy）
            if ym not in bills_total:
                fail(f"{xzyf}: 无对应账单月份 {ym}")
                errors += 1
            elif abs(down - bills_total[ym]) <= TOLERANCE:
                ok(f"{xzyf}: 扣款 {down:g} == 账单合计 {bills_total[ym]:g}")
            else:
                fail(f"{xzyf}: 扣款 {down:g} != 账单合计 {bills_total[ym]:g}")
                errors += 1
        else:  # 人工缴费：结余上升 == 缴费金额
            if abs(-down - jfje) <= TOLERANCE:
                ok(f"{xzyf}: 充值 {-down:g} == 金额 {jfje:g}")
            else:
                fail(f"{xzyf}: 充值 {-down:g} != 金额 {jfje:g}")
                errors += 1
    return errors


def audit_statistics(live_data: dict, statistic_id: str, usage: list) -> int:
    """D 边：长期统计月度 change vs 账单用量（数据就绪的月份才判）"""

    import ha_tools

    print("D. 长期统计月度 change vs 账单用量")
    billed = {r["ysny"]: float(r["sl"]) for r in usage}
    result = ha_tools.ws_call("recorder/statistics_during_period", {
        "statistic_ids": [statistic_id],
        "start_time": "2026-01-01T00:00:00+08:00",
        "period": "month",
        "types": ["change"],
    })
    rows = (result.get("result") or {}).get(statistic_id) or []
    if not rows:
        print("  --   无统计数据（未回填或管道未生效）")
        return 0
    errors = 0
    for row in rows:
        start = row.get("start")  # ms epoch（本地月初零点）
        month_key = __import__("datetime").datetime.fromtimestamp(
            start / 1000, tz=__import__("datetime").timezone(
                __import__("datetime").timedelta(hours=8))
        ).strftime("%Y%m")
        change = row.get("change")
        if month_key not in billed:
            ok(f"{month_key}: 统计 change={change:g}（无账单月份，跳过）")
            continue
        if change is None:
            ok(f"{month_key}: change=None（无数据，跳过）")
            continue
        if abs(change - billed[month_key]) <= TOLERANCE:
            ok(f"{month_key}: 统计 {change:g} == 账单 {billed[month_key]:g}")
        else:
            fail(f"{month_key}: 统计 {change:g} != 账单 {billed[month_key]:g}")
            errors += 1
    missing = [m for m in billed if not any(
        __import__("datetime").datetime.fromtimestamp(
            r["start"] / 1000, tz=__import__("datetime").timezone(
                __import__("datetime").timedelta(hours=8))).strftime("%Y%m") == m
        for r in rows
    )]
    if missing:
        print(f"  --   账单月份无统计点: {', '.join(missing)}（未回填？）")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--usage", help="用水记录 JSON 文件")
    ap.add_argument("--payment", help="缴费记录 JSON 文件")
    ap.add_argument("--live", action="store_true", help="连接实机 HA 追加 D 边对账")
    ap.add_argument("--entry-id", default="01KQV3BYRY67ARVDEMGVX8C9FE")
    ap.add_argument("--statistic-id", default="sensor.li_jing_tian_xia_er_qi_lei_ji_yong_shui")
    args = ap.parse_args()
    if not args.usage or not args.payment:
        ap.error("--usage 与 --payment 必填")
    usage = json.loads(Path(args.usage).read_text(encoding="utf-8"))
    payment = json.loads(Path(args.payment).read_text(encoding="utf-8"))
    errors = audit_records(usage, payment)
    if args.live:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # workspace 根（ha_tools.py）
        errors += audit_statistics(None, args.statistic_id, usage)
    print(f"\n结果: {'PASS' if errors == 0 else 'FAIL'}（{errors} 处不一致）")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
