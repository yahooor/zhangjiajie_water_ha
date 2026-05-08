"""张家界供水传感器平台"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ZhangjiajieWaterCoordinator


@dataclass(frozen=True, kw_only=True)
class ZhangjiajieWaterSensorEntityDescription(SensorEntityDescription):
    """扩展描述：支持 value_fn 提取数据"""
    value_fn: Callable[[dict], Any] = lambda d: None


SENSOR_DESCRIPTIONS: tuple[ZhangjiajieWaterSensorEntityDescription, ...] = (
    ZhangjiajieWaterSensorEntityDescription(
        key="balance",
        name="账户余额",
        icon="mdi:cash",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda d: round(float(d["balance"]), 2) if d.get("balance") is not None else None,
    ),
    ZhangjiajieWaterSensorEntityDescription(
        key="last_payment_date",
        name="上次缴费日期",
        icon="mdi:calendar",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda d: (
            datetime.strptime(d["last_payment_date"][:10], "%Y-%m-%d").date()
            if isinstance(d.get("last_payment_date"), str) and len(d["last_payment_date"]) >= 10
            else d.get("last_payment_date") if isinstance(d.get("last_payment_date"), date)
            else None
        ),
    ),
    ZhangjiajieWaterSensorEntityDescription(
        key="last_payment_time",
        name="上次缴费时间",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda d: d.get("last_payment_time") if isinstance(d.get("last_payment_time"), datetime) else None,
    ),
    ZhangjiajieWaterSensorEntityDescription(
        key="last_payment_amount",
        name="上次缴费金额",
        icon="mdi:cash-100",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda d: round(float(d["last_payment_amount"]), 2) if d.get("last_payment_amount") is not None else None,
    ),
    ZhangjiajieWaterSensorEntityDescription(
        key="previous_balance",
        name="上次结余",
        icon="mdi:cash-minus",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda d: round(float(d["previous_balance"]), 2) if d.get("previous_balance") is not None else None,
    ),
    ZhangjiajieWaterSensorEntityDescription(
        key="invoice_code",
        name="发票编码",
        icon="mdi:receipt-text",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("invoice_code"),
    ),
    ZhangjiajieWaterSensorEntityDescription(
        key="customer_code",
        name="客户编码",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("customer_code"),
    ),
    ZhangjiajieWaterSensorEntityDescription(
        key="current_usage",
        name="本期用水量",
        icon="mdi:water",
        native_unit_of_measurement="m³",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("current_usage"),
    ),
    ZhangjiajieWaterSensorEntityDescription(
        key="current_bill",
        name="本期费用合计",
        icon="mdi:currency-cny",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda d: round(float(d["current_bill"]), 2) if d.get("current_bill") is not None else None,
    ),
    ZhangjiajieWaterSensorEntityDescription(
        key="current_water_fee",
        name="本月水费",
        icon="mdi:water-outline",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda d: round(float(d["current_water_fee"]), 2) if d.get("current_water_fee") is not None else None,
    ),
    ZhangjiajieWaterSensorEntityDescription(
        key="other_fees",
        name="其他费用",
        icon="mdi:receipt-text-outline",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda d: round(float(d["other_fees"]), 2) if d.get("other_fees") is not None else None,
    ),
    ZhangjiajieWaterSensorEntityDescription(
        key="sewage_fee",
        name="污水处理费",
        icon="mdi:water-pump",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda d: round(float(d["sewage_fee"]), 2) if d.get("sewage_fee") is not None else None,
    ),
    ZhangjiajieWaterSensorEntityDescription(
        key="garbage_fee",
        name="垃圾处理费",
        icon="mdi:trash-can-outline",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda d: round(float(d["garbage_fee"]), 2) if d.get("garbage_fee") is not None else None,
    ),
    ZhangjiajieWaterSensorEntityDescription(
        key="current_month_reading",
        name="最新抄表读数",
        icon="mdi:gauge",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("current_month_reading"),
    ),
    ZhangjiajieWaterSensorEntityDescription(
        key="previous_month_reading",
        name="最新抄表上期读数",
        icon="mdi:gauge",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("previous_month_reading"),
    ),
    # latest_reading 与 current_month_reading 值相同但语义不同，保留兼容
    ZhangjiajieWaterSensorEntityDescription(
        key="latest_reading",
        name="最新读数",
        icon="mdi:gauge",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("latest_reading"),
    ),
    ZhangjiajieWaterSensorEntityDescription(
        key="latest_reading_month",
        name="抄表月份",
        icon="mdi:calendar-month",
        value_fn=lambda d: d.get("latest_reading_month"),
    ),
    ZhangjiajieWaterSensorEntityDescription(
        key="annual_usage",
        name="年累计用水",
        icon="mdi:chart-bar",
        native_unit_of_measurement="m³",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("annual_usage"),
    ),
    ZhangjiajieWaterSensorEntityDescription(
        key="annual_bill",
        name="年累计水费",
        icon="mdi:currency-cny",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda d: round(float(d["annual_bill"]), 2) if d.get("annual_bill") is not None else None,
    ),
)

# 年度传感器 key 集合（跨年时动态更新名称）
_ANNUAL_KEYS = {"annual_usage", "annual_bill"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ZhangjiajieWaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ZhangjiajieWaterSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    ])


class ZhangjiajieWaterSensor(CoordinatorEntity[ZhangjiajieWaterCoordinator], SensorEntity):
    """张家界供水传感器实体"""

    _attr_has_entity_name = True
    entity_description: ZhangjiajieWaterSensorEntityDescription

    def __init__(
        self,
        coordinator: ZhangjiajieWaterCoordinator,
        description: ZhangjiajieWaterSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"
        self._attr_device_info = coordinator.device_info
        # 年度传感器在初始化时注入年份（coordinator.data 在 add_entities 时已填充）
        if description.key in _ANNUAL_KEYS and coordinator.data:
            year = coordinator.data.get("_year", "")
            if year:
                self._attr_name = f"{year}年{description.name}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """数据更新时同步刷新年度传感器名称（跨年自动更新）。"""
        if self.entity_description.key in _ANNUAL_KEYS and self.coordinator.data:
            year = self.coordinator.data.get("_year", "")
            if year:
                self._attr_name = f"{year}年{self.entity_description.name}"
        super()._handle_coordinator_update()

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        try:
            return self.entity_description.value_fn(self.coordinator.data)
        except (KeyError, ValueError, TypeError):
            return None
