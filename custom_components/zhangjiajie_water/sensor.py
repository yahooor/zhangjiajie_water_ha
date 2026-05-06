from __future__ import annotations
from datetime import date, datetime
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN

# (name, icon, unit, device_class, state_class)
BASE_SENSORS = {
    "balance": ("账户余额", "mdi:cash", "CNY", SensorDeviceClass.MONETARY, None),
    "last_payment_date": ("上次缴费日期", "mdi:calendar", None, SensorDeviceClass.DATE, None),
    "last_payment_time": ("上次缴费时间", "mdi:clock-outline", None, SensorDeviceClass.TIMESTAMP, None),
    "last_payment_amount": ("上次缴费金额", "mdi:cash-100", "CNY", SensorDeviceClass.MONETARY, None),
    "previous_balance": ("上次结余", "mdi:cash-minus", "CNY", SensorDeviceClass.MONETARY, None),
    "invoice_code": ("发票编码", "mdi:receipt-text", None, None, None),
    "customer_code": ("客户编码", "mdi:identifier", None, None, None),
    "current_usage": ("本期用水量", "mdi:water", "m³", None, SensorStateClass.MEASUREMENT),
    "current_bill": ("本期费用合计", "mdi:currency-cny", "CNY", SensorDeviceClass.MONETARY, None),
    "current_water_fee": ("本月水费", "mdi:water-outline", "CNY", SensorDeviceClass.MONETARY, None),
    "other_fees": ("其他费用", "mdi:receipt-text-outline", "CNY", SensorDeviceClass.MONETARY, None),
    "sewage_fee": ("污水处理费", "mdi:water-pump", "CNY", SensorDeviceClass.MONETARY, None),
    "garbage_fee": ("垃圾处理费", "mdi:trash-can-outline", "CNY", SensorDeviceClass.MONETARY, None),
    "current_month_reading": ("最新抄表读数", "mdi:gauge", None, None, SensorStateClass.MEASUREMENT),
    "previous_month_reading": ("最新抄表上期读数", "mdi:gauge", None, None, SensorStateClass.MEASUREMENT),
    "latest_reading": ("最新读数", "mdi:gauge", None, None, SensorStateClass.MEASUREMENT),
    "latest_reading_month": ("抄表月份", "mdi:calendar-month", None, None, None),
    "annual_usage": ("年累计用水", "mdi:chart-bar", "m³", None, SensorStateClass.MEASUREMENT),
    "annual_bill": ("年累计水费", "mdi:currency-cny", "CNY", SensorDeviceClass.MONETARY, None),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ZhangjiajieWaterSensor(coordinator, key, *defn)
        for key, defn in BASE_SENSORS.items()
    ])


class ZhangjiajieWaterSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        coordinator,
        key: str,
        name: str,
        icon: str,
        unit: str | None,
        device_class: str | None,
        state_class: str | None,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_device_info = coordinator.device_info
        # 年度传感器名称注入当前年份（coordinator.data 在 add_entities 时已填充）
        if key in ("annual_usage", "annual_bill") and coordinator.data:
            year = coordinator.data.get("_year", "")
            if year:
                self._attr_name = f"{year}年{name}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """数据更新时同步刷新年度传感器名称（跨年自动更新）。"""
        if self._key in ("annual_usage", "annual_bill") and self.coordinator.data:
            year = self.coordinator.data.get("_year", "")
            base_name = BASE_SENSORS[self._key][0]
            if year:
                self._attr_name = f"{year}年{base_name}"
        super()._handle_coordinator_update()

    @property
    def native_value(self):
        value = self.coordinator.data.get(self._key)
        if value is None:
            return None
        # DATE device_class: must return date object
        if self._key == "last_payment_date":
            if isinstance(value, date):
                return value
            if isinstance(value, str) and len(value) >= 10:
                try:
                    return datetime.strptime(value[:10], "%Y-%m-%d").date()
                except ValueError:
                    pass
            return None
        # TIMESTAMP device_class: must return datetime object
        if self._key == "last_payment_time":
            if isinstance(value, datetime):
                return value
            return None
        # MONETARY: round floats
        if isinstance(value, (int, float)) and self._attr_device_class == SensorDeviceClass.MONETARY:
            return round(float(value), 2)
        return value
