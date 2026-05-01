"""Check pagination - how many pages of usage records for 2026?"""
import asyncio, json, aiohttp

ACCOUNT_NO = "115062401"
OPENID = "oumDiv6xOpOgDU0IXeV68Nc963IA"
HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Origin": "https://ccpay.thiscc.com",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 26_4_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.72(0x18004820) NetType/WIFI Language/zh_CN",
}

async def post(page):
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as s:
        r = await s.post(
            "https://ccpay.thiscc.com/waterPay/search/searchRecord.action",
            data={"type": "1", "custCode": f"{ACCOUNT_NO},{page},10,1", "wxid": OPENID},
            headers=HEADERS,
        )
        return json.loads(await r.text())

async def main():
    all_records = []
    current_year = "2026"
    for p in range(1, 25):
        d = await post(p)
        recs = d.get("data", [])
        if not recs:
            print(f"  page {p}: empty, stop")
            break
        last_ym = recs[-1].get("ysny", "")
        print(f"  page {p}: {len(recs)} records, last ysny={last_ym}")
        all_records.extend(recs)
        if last_ym and not last_ym.startswith(current_year):
            print(f"  -> {last_ym} 不属于 {current_year}，停止翻页")
            break

    year_records = [r for r in all_records if str(r.get("ysny", "")).startswith(current_year)]
    total_usage = sum(float(r.get("sl", 0)) for r in year_records)
    total_bill = sum(float(r.get("hjfy", 0)) for r in year_records)
    print(f"\n2026 Total records: {len(year_records)}")
    print(f"2026 Annual usage: {round(total_usage, 2)} m3")
    print(f"2026 Annual bill: {round(total_bill, 2)} CNY")

asyncio.run(main())
