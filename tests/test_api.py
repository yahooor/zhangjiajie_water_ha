"""api.py 单元测试：参数构造、重试策略、错误分类。

api.py 依赖 homeassistant 且使用相对导入（`from .const import ...`），
因此这里做两件事绕过依赖：
  1. 往 sys.modules 注入 homeassistant 的最小桩
  2. 用临时包名 `zjw` 注册包路径，使 `from .const import` 可解析

覆盖重点（这些是历史上真出过问题的地方）：
  - 分页参数拼装（`户号,页码,10,1`，末尾 1 是抓包确认的固定值）
  - **4xx 与非 JSON 响应不重试**（曾因 502 网关页面反复重试拖到超时）
  - 业务错误码 res!=100 归类为 AuthError（重试无意义）
  - 客户端关闭后调用直接报错
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

_COMP = (
    Path(__file__).parent.parent / "custom_components" / "zhangjiajie_water"
)


def _install_ha_stubs() -> None:
    """注入 homeassistant 最小桩，避免为跑测试安装整套 HA。"""
    ha = types.ModuleType("homeassistant")
    core = types.ModuleType("homeassistant.core")
    helpers = types.ModuleType("homeassistant.helpers")
    aio = types.ModuleType("homeassistant.helpers.aiohttp_client")

    class HomeAssistant:
        """HA 实例占位。"""

    core.HomeAssistant = HomeAssistant
    aio.async_get_clientsession = lambda hass: None
    helpers.aiohttp_client = aio
    ha.core = core
    ha.helpers = helpers

    sys.modules.setdefault("homeassistant", ha)
    sys.modules.setdefault("homeassistant.core", core)
    sys.modules.setdefault("homeassistant.helpers", helpers)
    sys.modules.setdefault("homeassistant.helpers.aiohttp_client", aio)


def _load_api():
    _install_ha_stubs()
    pkg = types.ModuleType("zjw")
    pkg.__path__ = [str(_COMP)]
    sys.modules["zjw"] = pkg
    for name in ("const", "api"):
        spec = importlib.util.spec_from_file_location(f"zjw.{name}", _COMP / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[f"zjw.{name}"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["zjw.api"]


api = _load_api()


# ── 测试替身 ──────────────────────────────────────────────────────────

class _FakeResp:
    def __init__(self, status: int, text: str):
        self.status = status
        self._text = text

    async def text(self):
        return self._text


class _FakeCtx:
    def __init__(self, resp):
        self._resp = resp

    async def __aenter__(self):
        return self._resp

    async def __aexit__(self, *exc):
        return False


class _FakeSession:
    """按顺序吐出预设响应；queued 元素可为响应元组或异常实例。"""

    def __init__(self, queued):
        self.queued = list(queued)
        self.calls = []
        self.closed = False

    def post(self, url, data=None, headers=None, timeout=None):
        self.calls.append({"url": url, "data": data, "headers": headers})
        item = self.queued.pop(0) if self.queued else (200, "{}")
        if isinstance(item, Exception):
            raise item
        status, text = item
        return _FakeCtx(_FakeResp(status, text))


def _make(account="12345", openid="oid", session=None):
    obj = api.ZhangjiajieWaterAPI(account, openid)
    if session is not None:
        obj._session = session
    return obj


# ── 参数构造 ──────────────────────────────────────────────────────────

def test_make_custcode_format():
    obj = _make(account="888")
    assert obj._make_custcode(1) == "888,1,10,1"
    assert obj._make_custcode(3) == "888,3,10,1"


def test_make_form_contains_type_and_openid():
    obj = _make(account="888", openid="WX-OID")
    form = obj._make_form(1, page=2)
    assert form["type"] == "1"
    assert form["custCode"] == "888,2,10,1"
    assert form["wxid"] == "WX-OID"


def test_make_form_type_is_string():
    """接口按字符串收 type；传 int 会被服务端当成非法值。"""
    obj = _make()
    assert isinstance(obj._make_form(2)["type"], str)


def test_headers_content_type():
    h = _make().headers
    assert h["Content-Type"].startswith("application/x-www-form-urlencoded")
    assert h["X-Requested-With"] == "XMLHttpRequest"


# ── 正常路径 ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_usage_records_returns_data_list():
    session = _FakeSession([(200, '{"res":100,"data":[{"a":1},{"a":2}]}')])
    obj = _make(session=session)
    assert await obj.fetch_usage_records() == [{"a": 1}, {"a": 2}]
    assert session.calls[0]["data"]["type"] == "1"


@pytest.mark.asyncio
async def test_fetch_payment_records_returns_data_list():
    session = _FakeSession([(200, '{"res":100,"data":[{"b":1}]}')])
    obj = _make(session=session)
    assert await obj.fetch_payment_records() == [{"b": 1}]
    assert session.calls[0]["data"]["type"] == "2"


@pytest.mark.asyncio
async def test_fetch_usage_records_missing_data_returns_empty():
    session = _FakeSession([(200, '{"res":100}')])
    obj = _make(session=session)
    assert await obj.fetch_usage_records() == []


@pytest.mark.asyncio
async def test_test_connection_returns_record_count():
    session = _FakeSession([(200, '{"res":100,"data":[1,2,3]}')])
    obj = _make(session=session)
    assert await obj.async_test_connection() == 3


@pytest.mark.asyncio
async def test_test_connection_zero_records_is_valid():
    """新账户尚无缴费记录也属凭据有效。"""
    session = _FakeSession([(200, '{"res":100,"data":[]}')])
    obj = _make(session=session)
    assert await obj.async_test_connection() == 0


# ── 错误分类与重试 ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_business_error_raises_auth_and_no_retry():
    session = _FakeSession([(200, '{"res":101,"msg":"户号不存在"}')])
    obj = _make(session=session)
    with pytest.raises(api.ZhangjiajieWaterApiAuthError) as ei:
        await obj.fetch_usage_records()
    assert "户号不存在" in str(ei.value)
    assert len(session.calls) == 1, "业务错误不应重试"


@pytest.mark.asyncio
async def test_non_json_response_no_retry():
    """502 网关错误页返回 HTML，重试无意义。"""
    session = _FakeSession([(200, "<html>502 Bad Gateway</html>")])
    obj = _make(session=session)
    with pytest.raises(api.ZhangjiajieWaterApiConnectionError):
        await obj.fetch_usage_records()
    assert len(session.calls) == 1


@pytest.mark.asyncio
async def test_http_4xx_no_retry():
    session = _FakeSession([(403, "forbidden")])
    obj = _make(session=session)
    with pytest.raises(api.ZhangjiajieWaterApiConnectionError):
        await obj.fetch_usage_records()
    assert len(session.calls) == 1


@pytest.mark.asyncio
async def test_http_5xx_retries_then_raises(monkeypatch):
    """5xx 可重试：验证重试次数与最终异常类型。"""

    async def _no_sleep(_):
        return None

    monkeypatch.setattr(api.asyncio, "sleep", _no_sleep)
    session = _FakeSession([(500, "err"), (500, "err"), (500, "err")])
    obj = _make(session=session)
    with pytest.raises(api.ZhangjiajieWaterApiConnectionError):
        await obj.fetch_usage_records()
    assert len(session.calls) == 3, "默认 retries=3"


@pytest.mark.asyncio
async def test_network_error_retries_then_wrapped(monkeypatch):
    async def _no_sleep(_):
        return None

    monkeypatch.setattr(api.asyncio, "sleep", _no_sleep)
    session = _FakeSession([RuntimeError("boom"), RuntimeError("boom"), RuntimeError("boom")])
    obj = _make(session=session)
    with pytest.raises(api.ZhangjiajieWaterApiConnectionError) as ei:
        await obj.fetch_usage_records()
    assert "boom" in str(ei.value)


@pytest.mark.asyncio
async def test_closed_client_raises():
    obj = _make(session=_FakeSession([]))
    obj._closed = True
    with pytest.raises(api.ZhangjiajieWaterApiError):
        await obj.fetch_usage_records()


@pytest.mark.asyncio
async def test_close_closes_own_session():
    session = _FakeSession([])

    async def _close():
        session.closed = True

    session.close = _close
    obj = _make(session=session)
    await obj.async_close()
    assert session.closed is True
    assert obj._session is None
