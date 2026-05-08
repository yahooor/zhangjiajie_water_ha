"""Constants for Zhangjiajie Water integration."""
from __future__ import annotations

import json
from pathlib import Path

DOMAIN = "zhangjiajie_water"
BASE_URL = "https://ccpay.thiscc.com"
API_PATH = "/waterPay/search/searchRecord.action"

# 版本号：从 manifest.json 单一来源读取，避免三处手动同步
_MANIFEST = json.loads(
    (Path(__file__).parent / "manifest.json").read_text(encoding="utf-8")
)
INTEGRATION_VERSION: str = _MANIFEST["version"]

# 刷新模式选项
CONF_UPDATE_MODE = "update_mode"
CONF_DAILY_HOUR = "daily_hour"
CONF_DAILY_MINUTE = "daily_minute"
UPDATE_MODE_DAILY = "daily"
UPDATE_MODE_INTERVAL = "interval"
