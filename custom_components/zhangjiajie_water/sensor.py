from __future__ import annotations
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN

BASE_SENSORS = {
    "balance": ("账户余额", "mdi:cash", "元", SensorDeviceClass.MONETARY),
    "last_payment_date": ("上次缴费日期", "mdi:calendar", None, None),
    "last_payment_amount": ("上次缴费金额", "mdi:cash-100", "元", SensorDeviceClass.MONETARY),
    "current_usage": ("本期用水量", "mdi:water", "m³", None),
    "current_bill": ("本期水费", "mdi:currency-cny", "元", SensorDeviceClass.MONETARY),
    "latest_reading": ("最新读数", "mdi:gauge", "m³", None),
    "latest_reading_month": ("抄表月份", "mdi:calendar-month", None, None),
    "annual_usage": ("年累计用水", "mdi:chart-bar", "m³", None),
    "annual_bill": ("年累计水费", "mdi:currency-cny", "元", SensorDeviceClass.MONETARY),
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
        unit: str,
        device_class: str | None,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._base_name = name
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_device_info = coordinator.device_info

    @property
    def name(self) -> str:
        # 年度传感器名字拼入当前年份
        if self._key in ("annual_usage", "annual_bill"):
            year = self.coordinator.data.get("_year", "")
            return f"{year}{self._base_name}" if year else self._base_name
        return self._base_name

    @property
    def native_value(self):
        value = self.coordinator.data.get(self._key)
        if value is None:
            return None
        if isinstance(value, (int, float)) and self._attr_device_class == SensorDeviceClass.MONETARY:
            return round(float(value), 2)
        return value
