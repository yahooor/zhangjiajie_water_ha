"""把历史账单周期的抄表读数回填进累计用水传感器的长期统计。

原理：
  - 上游只提供账单时点的累计读数（月度台阶，无日内数据），因此回填点
    = 每月自动扣款结算时点（xzyf）的 bybs；
  - rebase：live 序列首观测（2026-10-23）sum 基线为 0，为使回填序列与
    live 序列无缝衔接（sum 单调、无假重置），回填点 sum = bybs − 最新读数；
  - 月度 change 因此等于账单用量：9 月窗口 = (−15) − (−33) = 18 ✓。

用法（在仓库根，实机可达时）：
  python tools/backfill_statistics.py \
    --usage tests/fixtures/real/usage_records_page1.json \
    --payment tests/fixtures/real/payment_records_page1.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # workspace 根（ha_tools.py）
import ha_tools

STATISTIC_ID = "sensor.li_jing_tian_xia_er_qi_lei_ji_yong_shui"


def settlement_times(payment: list) -> dict[str, str]:
    """账单月份 -> 自动扣款结算时间（xzyf 日期 + sfsj 时刻，默认 04:00）"""
    out: dict[str, str] = {}
    for p in payment:
        if float(p.get("jfje") or 0) != 0:
            continue  # 只取自动扣款（账单结算）
        ym = str(p.get("xzyf", ""))[:6]
        xzyf = str(p.get("xzyf", ""))
        sfsj = str(p.get("sfsj", ""))
        # 统计点位必须对齐整点（minutes/seconds = 0），地板处理
        hour = int(sfsj[11:13]) if len(sfsj) >= 19 else 4
        date = f"{xzyf[:4]}-{xzyf[4:6]}-{xzyf[6:8]}" if len(xzyf) >= 8 else xzyf
        out[ym] = f"{date}T{hour:02d}:00:00+08:00"
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--usage", required=True)
    ap.add_argument("--payment", required=True)
    args = ap.parse_args()

    import calendar

    usage = json.loads(Path(args.usage).read_text(encoding="utf-8"))
    payment = json.loads(Path(args.payment).read_text(encoding="utf-8"))
    settle = settlement_times(payment)

    ordered = sorted(usage, key=lambda r: r["ysny"])
    # 锚点 = 最早账单的上期读数（= 上一年末累计读数）：
    # 合成基线点（上年末，sum=0）后全序列 sum >= 0，且每月 change == 当期账单用量
    anchor = float(ordered[0]["sybs"])
    latest_bybs = float(ordered[-1]["bybs"])
    target_live_sum = round(latest_bybs - anchor, 3)
    print(f"锚点: 最早账单上期读数 {anchor:g}（{ordered[0]['ysny'][:4]}年末），"
          f"live 目标 sum = {target_live_sum:g}")

    def month_end(ym: str) -> str:
        y, m = int(ym[:4]), int(ym[4:6])
        return f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}T23:00:00+08:00"

    stats = []
    # 基线点：最早账单的上年末（无它则首月 change 无法计算）
    base_ym = ordered[0]["ysny"]
    by, bm = int(base_ym[:4]), int(base_ym[4:6])
    if bm == 1:
        base_date = f"{by - 1:04d}-12-31T23:00:00+08:00"
    else:
        base_date = f"{by:04d}-{bm - 1:02d}-{calendar.monthrange(by, bm - 1)[1]:02d}T23:00:00+08:00"
    stats.append({"start": base_date, "state": anchor, "sum": 0.0})
    print(f"  基线 {base_date} state={anchor:g} sum=0")

    last_point = base_date
    for rec in ordered:
        ym = str(rec["ysny"])
        bybs = float(rec["bybs"])
        start = settle.get(ym) or month_end(ym)  # 有结算用结算时点，否则月末
        stats.append({
            "start": start,
            "state": bybs,
            "sum": round(bybs - anchor, 3),
        })
        last_point = max(last_point, start)
        src_tag = "结算" if ym in settle else "月末"
        print(f"  点位[{src_tag}] {start} state={bybs:g} sum={bybs - anchor:g}")

    metadata = {
        "statistic_id": STATISTIC_ID,
        "source": "recorder",
        "name": "累计用水",
        "has_sum": True,
        "has_mean": False,
        "unit_of_measurement": "m³",
    }
    r = ha_tools.ws_call("recorder/import_statistics",
                         {"metadata": metadata, "stats": stats})
    print("import:", r.get("success"), r.get("error", ""))
    if not r.get("success"):
        return 1

    # live 侧幂等调整：目标 sum（= 最新读数 − 锚点）减当前 live 末端 sum
    if target_live_sum:
        from datetime import datetime, timedelta
        adj_start = (datetime.fromisoformat(last_point).replace(
            minute=0, second=0) + timedelta(hours=1)).isoformat()
        probe = ha_tools.ws_call("recorder/statistics_during_period", {
            "statistic_ids": [STATISTIC_ID],
            "start_time": adj_start,
            "period": "hour",
            "types": ["sum"],
        })
        rows = (probe.get("result") or {}).get(STATISTIC_ID) or []
        current = rows[-1]["sum"] if rows else 0.0
        delta = round(target_live_sum - (current or 0.0), 3)
        print(f"live 末端 sum={current:g}，目标 {target_live_sum:g}，adjust {delta:+g}")
        if abs(delta) > 1e-9:
            adj = ha_tools.ws_call("recorder/adjust_sum_statistics", {
                "statistic_id": STATISTIC_ID,
                "start_time": adj_start,
                "adjustment": delta,
                "adjustment_unit_of_measurement": "m³",
            })
            print("adjust:", adj.get("success"), adj.get("error", ""))
            if not adj.get("success"):
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
