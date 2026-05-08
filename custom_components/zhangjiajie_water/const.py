"""Constants for Zhangjiajie Water integration."""
DOMAIN = "zhangjiajie_water"
BASE_URL = "https://ccpay.thiscc.com"
API_PATH = "/waterPay/search/searchRecord.action"
INTEGRATION_VERSION = "3.0.0"

# 刷新模式选项
CONF_UPDATE_MODE = "update_mode"
CONF_DAILY_HOUR = "daily_hour"
CONF_DAILY_MINUTE = "daily_minute"
UPDATE_MODE_DAILY = "daily"
UPDATE_MODE_INTERVAL = "interval"
