"""Refresh regression tests driven without Home Assistant or live account data."""
import asyncio
import sys
from importlib import import_module
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest


class FakeUpdateFailed(Exception):
    pass


@pytest.fixture
def make_coordinator(monkeypatch):
    def stub(name, **attrs):
        module = ModuleType(name)
        vars(module).update(attrs)
        monkeypatch.setitem(sys.modules, name, module)

    stub("homeassistant", __path__=[])
    stub("homeassistant.core", HomeAssistant=object, callback=lambda handler: handler)
    stub("homeassistant.config_entries", ConfigEntry=object)
    stub("homeassistant.exceptions", ConfigEntryAuthFailed=type("ConfigEntryAuthFailed", (Exception,), {}))
    stub("homeassistant.helpers", __path__=[])
    stub("homeassistant.helpers.aiohttp_client", async_get_clientsession=lambda _: None)
    stub("homeassistant.helpers.device_registry", DeviceInfo=dict)
    stub("homeassistant.helpers.event", async_track_time_change=lambda *a, **kw: None)
    stub("homeassistant.helpers.update_coordinator", DataUpdateCoordinator=object, UpdateFailed=FakeUpdateFailed)
    package = "_water_coordinator_under_test"
    root = Path(__file__).resolve().parents[1] / "custom_components" / "zhangjiajie_water"
    stub(package, __path__=[str(root)])
    module = import_module(f"{package}.coordinator")

    def build(previous, rows=None):
        coordinator = object.__new__(module.ZhangjiajieWaterCoordinator)
        coordinator.data = previous
        coordinator.entry = SimpleNamespace(data={"account_no": "synthetic-account"})
        coordinator.api = SimpleNamespace(fetch_usage_records=AsyncMock(return_value=rows or []))
        coordinator._fetch_payment = AsyncMock(return_value={"balance": 0.0})
        coordinator._last_latest = None
        coordinator._consecutive_failures = 0
        coordinator._notification_sent = False
        return coordinator

    try:
        yield build
    finally:
        for key in ("const", "api", "utils", "coordinator"):
            sys.modules.pop(f"{package}.{key}", None)


def test_empty_first_page_does_not_reset_a_previously_reported_total(make_coordinator):
    previous = {"latest_reading_month": "4月", "annual_usage": 27.5}
    coordinator = make_coordinator(previous)

    with pytest.raises(FakeUpdateFailed, match="用水记录首页为空"):
        asyncio.run(coordinator._async_update_data())

    assert coordinator.data == previous
    assert coordinator._consecutive_failures == 1


def test_first_refresh_empty_account_preserves_valid_zero_balance(make_coordinator):
    coordinator = make_coordinator(None)

    result = asyncio.run(coordinator._async_update_data())

    assert result["balance"] == 0.0 and result["annual_usage"] == 0.0
    assert coordinator._consecutive_failures == 0
