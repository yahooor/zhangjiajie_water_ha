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
    "balance": ("è´¦æ·ä½é¢", "mdi:cash", "CNY", SensorDeviceClass.MONETARY, None),
    "last_payment_date": ("ä¸æ¬¡ç¼´è´¹æ¥æ", "mdi:calendar", None, SensorDeviceClass.DATE, None),
    "last_payment_time": ("ä¸æ¬¡ç¼´è´¹æ¶é´", "mdi:clock-outline", None, SensorDeviceClass.TIMESTAMP, None),
    "last_payment_amount": ("ä¸æ¬¡ç¼´è´¹éé¢", "mdi:cash-100", "CNY", SensorDeviceClass.MONETARY, None),
    "previous_balance": ("ä¸æ¬¡ç»ä½", "mdi:cash-minus", "CNY", SensorDeviceClass.MONETARY, None),
    "invoice_code": ("åç¥¨ç¼ç ", "mdi:receipt-text", None, None, None),
    "customer_code": ("å®¢æ·ç¼ç ", "mdi:identifier", None, None, None),
    "current_usage": ("æ¬æç¨æ°´é", "mdi:water", "mÂ³", None, SensorStateClass.MEASUREMENT),
    "current_bill": ("æ¬æè´¹ç¨åè®¡", "mdi:currency-cny", "CNY", SensorDeviceClass.MONETARY, None),
    "current_water_fee": ("æ¬ææ°´è´¹", "mdi:water-outline", "CNY", SensorDeviceClass.MONETARY, None),
    "other_fees": ("å¶ä»è´¹ç¨", "mdi:receipt-text-outline", "CNY", SensorDeviceClass.MONETARY, None),
    "sewage_fee": ("æ±¡æ°´å¤çè´¹", "mdi:water-pump", "CNY", SensorDeviceClass.MONETARY, None),
    "garbage_fee": ("åå¾å¤çè´¹", "mdi:trash-can-outline", "CNY", SensorDeviceClass.MONETARY, None),
    "current_month_reading": ("ææ°æè¡¨è¯»æ°", "mdi:gauge", None, None, SensorStateClass.MEASUREMENT),
    "previous_month_reading": ("ææ°æè¡¨ä¸æè¯»æ°", "mdi:gauge", None, None, SensorStateClass.MEASUREMENT),
    "latest_reading": ("ææ°è¯»æ°", "mdi:gauge", None, None, SensorStateClass.MEASUREMENT),
    "latest_reading_month": ("æè¡¨æä»½", "mdi:calendar-month", None, None, None),
    "annual_usage": ("å¹´ç´¯è®¡ç¨æ°´", "mdi:chart-bar", "mÂ³", None, SensorStateClass.TOTAL_INCREASING),
    "annual_bill": ("å¹´ç´¯è®¡æ°´è´¹", "mdi:currency-cny", "CNY", SensorDeviceClass.MONETARY, None),
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
        # å¹´åº¦ä¼ æå¨åç§°æ³¨å¥å½åå¹´ä»½ï¼coordinator.data å¨ add_entities æ¶å·²å¡«åï¼
        if key in ("annual_usage", "annual_bill") and coordinator.data:
            year = coordinator.data.get("_year", "")
            if year:
                self._attr_name = f"{year}å¹´{name}"

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
