"""Debug script for v1.2.1 - 全面验证 API + 数据流"""
import asyncio, json, aiohttp, sys

ACCOUNT_NO = "115062401"
OPENID = "oumDiv6xOpOgDU0IXeV68Nc963IA"
BASE_URL = "https://ccpay.thiscc.com"
API_PATH = "/waterPay/search/searchRecord.action"

HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Origin": BASE_URL,
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 26_4_2 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
        "MicroMessenger/8.0.72(0x18004820) NetType/WIFI Language/zh_CN"
    ),
}

def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

async def post(data_type, page=1):
    url = BASE_URL + API_PATH
    form = {
        "type": str(data_type),
        "custCode": f"{ACCOUNT_NO},{page},10,1",
        "wxid": OPENID,
    }
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
        async with session.post(url, data=form, headers=HEADERS) as resp:
            text = await resp.text()
            result = json.loads(text)
            return result

def check(label, condition, got=None):
    status = "[PASS]" if condition else "[FAIL]"
    if got is not None:
        print(f"  {status} {label}: {got}")
    else:
        print(f"  {status} {label}")
    return condition

async def main():
    ok = True
    print("=" * 60)
    print("TEST 1: type=1 用水记录 (page=1)")
    print("=" * 60)
    r1 = await post(1, 1)
    ok &= check("res == 100", r1.get("res") == 100, r1.get("res"))
    records1 = r1.get("data", [])
    ok &= check("data is list, len >= 1", isinstance(records1, list) and len(records1) >= 1, len(records1))
    if records1:
        rec = records1[0]
        fields = ["ysny", "sybs", "bybs", "sl", "sf", "qtxm", "hjfy", "wsclf", "ljclf"]
        for f in fields:
            ok &= check(f"field {f} present", f in rec, rec.get(f))
        print(f"  First record: ysny={rec.get('ysny')}, sl={rec.get('sl')}, sf={rec.get('sf')}, hjfy={rec.get('hjfy')}")

    print()
    print("=" * 60)
    print("TEST 2: type=1 用水记录 (page=2)")
    print("=" * 60)
    r2 = await post(1, 2)
    ok &= check("res == 100", r2.get("res") == 100, r2.get("res"))

    print()
    print("=" * 60)
    print("TEST 3: type=2 缴费记录 (page=1)")
    print("=" * 60)
    r3 = await post(2, 1)
    ok &= check("res == 100", r3.get("res") == 100, r3.get("res"))
    records3 = r3.get("data", [])
    ok &= check("data is list, len >= 1", isinstance(records3, list) and len(records3) >= 1, len(records3))
    if records3:
        rec = records3[0]
        fields = ["kphm", "xzyf", "jfje", "scye", "bcye", "sfsj", "sfy"]
        for f in fields:
            ok &= check(f"field {f} present", f in rec, rec.get(f))
        print(f"  First record: kphm={rec.get('kphm')}, jfje={rec.get('jfje')}, bcye={rec.get('bcye')}")

    print()
    print("=" * 60)
    print("TEST 4: 无 OpenID (应返回 res != 100)")
    print("=" * 60)
    form_no_wx = {"type": "1", "custCode": f"{ACCOUNT_NO},1,10,1", "wxid": ""}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
        async with session.post(BASE_URL + API_PATH, data=form_no_wx, headers=HEADERS) as resp:
            text = await resp.text()
            r4 = json.loads(text)
    ok &= check("res != 100", r4.get("res") != 100, r4.get("res"))

    print()
    print("=" * 60)
    print("TEST 5: 完整数据模拟（年度汇总）")
    print("=" * 60)
    current_year = "2026"
    all_usage = []
    page = 1
    while page <= 20:
        r = await post(1, page)
        data = r.get("data", [])
        if not data:
            break
        all_usage.extend(data)
        last_ym = data[-1].get("ysny", "")
        if not last_ym or not last_ym.startswith(current_year):
            break
        page += 1

    print(f"  Total pages fetched: {page}")
    print(f"  Total records: {len(all_usage)}")
    if all_usage:
        latest = all_usage[0]
        raw_month = latest.get("ysny", "")
        formatted_month = f"{raw_month[:4]}年{int(raw_month[4:])}月" if len(raw_month) == 6 and raw_month.isdigit() else raw_month
        print(f"  Latest month: {formatted_month}")
        print(f"  Latest reading: {latest.get('bybs')} (raw: {latest.get('bybs')})")

        annual = sum(_safe_float(r.get("sl", 0)) for r in all_usage if r.get("ysny", "").startswith(current_year))
        annual_bill = sum(_safe_float(r.get("hjfy", 0)) for r in all_usage if r.get("ysny", "").startswith(current_year))
        print(f"  Annual usage: {round(annual, 2)} m3")
        print(f"  Annual bill: {round(annual_bill, 2)} CNY")

        r3b = await post(2, 1)
        data3b = r3b.get("data", [])
        if data3b:
            bcye = _safe_float(data3b[0].get("bcye"), 0.0)
            print(f"  Balance: {bcye} CNY")

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Overall: {'ALL PASS' if ok else 'SOME FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
