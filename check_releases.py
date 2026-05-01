"""Check existing releases"""
import urllib.request, json

token = "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"
headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json",
    "charset": "utf-8",
}
req = urllib.request.Request(
    "https://api.github.com/repos/yahooor/zhangjiajie_water_ha/releases",
    headers=headers,
)
with urllib.request.urlopen(req, timeout=15) as r:
    data = json.loads(r.read())
    for rel in data:
        print(f"ID={rel['id']}  tag={rel['tag_name']}  name={rel['name']}  draft={rel['draft']}  assets={len(rel['assets'])}")