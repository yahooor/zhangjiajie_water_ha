# AGENTS.md — zhangjiajie_water_ha

> 给 AI 会话与新协作者的项目约定。状态类信息看 README，本文件只记「怎么干活」。

## 一句话

Home Assistant 自定义集成，把**张家界供水**的户号数据接进 HA。
水费阶梯、欠费、账单周期等业务逻辑在本仓实现。当前 v3.6.0。

## 跑测试

```bash
pip install -r requirements-dev.txt   # pytest / pytest-asyncio / aiohttp / ruff
pytest -q                             # 期望 43 passed
ruff check .                          # 必须全绿
```

**依赖已显式声明**（2026-11-03 补）：此前本仓没有任何依赖声明，干净环境 clone 后
直接跑 pytest 会失败——`tests/test_api.py` 用 `@pytest.mark.asyncio`（需 pytest-asyncio），
`custom_components/api.py` 需要 aiohttp。

## 发版（一键脚本）

```bash
bash publish.sh
```

`publish.sh` 会自动读 `custom_components/zhangjiajie_water/manifest.json` 的版本号，
然后 push → 建 GitHub Release → 触发 Actions 的版本一致性 + HACS/Hassfest 校验。
**不需要手动同步版本号。**

> ⚠️ **本仓 tag 保护规则限制直接建 tag**，tag 由 Release 创建。
> 所以**不要**手动跑 `git tag vX.Y.Z && git push origin vX.Y.Z`——会被拒。

**固定交付流程**：审查 → 修复 → 推 GitHub → HA 通过 HACS 更新 → 读日志验证。

## 架构要点

| 文件 | 作用 | 注意 |
|---|---|---|
| `api.py` | 供水司接口客户端 | **参数拼装 + 重试/错误分类都在这里**，是最容易出错的地方 |
| `utils.py` | 纯工具函数 | 已被测试完整覆盖 |
| `const.py` | 常量 | — |
| `coordinator.py` | 轮询协调 | `iot_class: cloud_polling` |
| `sensor.py` / `binary_sensor.py` | 实体 | — |
| `button.py` | 手动刷新等按钮 | — |
| `config_flow.py` | 配置流程 | 改交互同步 `strings.json` / `translations/` |
| `blueprints/` | HA 蓝图 | **仓库根与 `custom_components/zhangjiajie_water/` 下各有一份**，改蓝图前先确认改的是哪一份 |
| `tools/` | 辅助工具 | — |

> **版本号会被 Actions 校验三处**：`tag` / `manifest.json` / `const.py`。
> 注意 `const.py` 里的 `INTEGRATION_VERSION` 是**从 manifest 读取**的
> （`INTEGRATION_VERSION: str = _MANIFEST["version"]`），**不是独立常量**——
> 所以实际只需改 manifest 一处，但 Actions 仍会校验 `const.py` 里读出来的值是否一致。

## 测试覆盖现状

| 文件 | 覆盖情况 |
|---|---|
| `tests/test_utils.py` | 覆盖完整 |
| `tests/test_derive.py` | 覆盖完整 |
| `tests/test_api.py` | 16 个用例，覆盖参数拼装与错误分类 |

> 2026-11-03 补 `tests/test_api.py` 后从 27 → **43 passed**。此前 `api.py`（约 165 行）
> 是零覆盖的缺口，因为它是参数拼装与重试逻辑所在，改错不会立刻报错但会静默拉不到数据。

## 红线

- **不要用 `0.0` 表达「查不到」**——同系列集成历史上的大坑，会被误读成「没交费/没用���」
- **tag 只能由 Release 创建**（保护规则），别手动建 tag
- 版本号唯一来源是 `custom_components/zhangjiajie_water/manifest.json`
- 改 `api.py` 必须跑 `pytest`，它承载重试与错误分类，静默失败风险最高
- `__pycache__` 在仓库根目录出现过，注意 `.gitignore` 覆盖，别把它提交进去
