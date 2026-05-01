from __future__ import annotations
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
    "last_payment_amount": ("上次缴费金额", "mdi:cash-100", "CNY", SensorDeviceClass.MONETARY, None),
    "current_usage": ("本期用水量", "mdi:water", "m³", None, SensorStateClass.MEASUREMENT),
    "current_bill": ("本期水费", "mdi:currency-cny", "CNY", SensorDeviceClass.MONETARY, None),
    "latest_reading": ("最新读数", "mdi:gauge", None, None, SensorStateClass.MEASUREMENT),
    "latest_reading_month": ("抄表月份", "mdi:calendar-month", None, None, None),
    "annual_usage": ("年累计用水", "mdi:chart-bar", "m³", None, SensorStateClass.TOTAL_INCREASING),
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

    @property
    def native_value(self):
        from datetime import datetime, date
        value = self.coordinator.data.get(self._key)
        if value is None:
            return None
        # DATE device_class: must return date object, not string
        if self._key == "last_payment_date":
            if isinstance(value, date):
                return value
            if isinstance(value, str) and len(value) == 10:
                try:
                    return datetime.strptime(value, "%Y-%m-%d").date()
                except ValueError:
                    pass
            return None  # return None instead of string to avoid HA error
        # MONETARY: round floats
        if isinstance(value, (int, float)) and self._attr_device_class == SensorDeviceClass.MONETARY:
            return round(float(value), 2)
        return value
