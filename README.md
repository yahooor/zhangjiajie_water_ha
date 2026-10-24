# 张家界供水

Home Assistant 自定义集成，通过抓取张家界供水微信公众号获取用水数据。

## 功能

| 功能类别 | 具体内容 |
|---------|---------|
| 💧 用水记录 | 月度用水量、抄表读数、水费明细 |
| 💰 缴费记录 | 缴费时间、金额、余额、方式 |
| 📊 年度统计 | 年累计用水量、年累计水费 |
| ⚡ 能源面板 | 累计用水传感器（total_increasing），可加入 HA 能源面板水耗统计 |
| 📈 历史数据 | 本期用水量传感器附带逐月用水/费用属性，上次缴费金额附带最近缴费记录属性 |
| 🔄 自动更新 | 默认 6 小时刷新一次，支持每日定时模式 |
| 🔔 低余额提醒 | 可配置阈值的「余额不足」二进制传感器 |
| 🧩 自动化蓝图 | 内置低余额、高用水提醒蓝图，一键导入 |
| 🩺 诊断支持 | 支持下载诊断（凭据自动脱敏） |
| 🏠 多户支持 | 支持添加多个供水账户 |

## 安装

### HACS（推荐）

1. HACS → 集成 → 添加自定义仓库：`https://github.com/yahooor/zhangjiajie_water_ha`
2. 搜索 "张家界供水" 安装
3. 重启 Home Assistant

### 手动安装

1. 下载 [最新版本](https://github.com/yahooor/zhangjiajie_water_ha/releases/latest) 页面的 **Source code (zip)**
2. 解压后把其中的 `custom_components/zhangjiajie_water/` 复制到 HA 配置目录的 `custom_components/` 下
3. 重启 Home Assistant

> 注：自 2025 年起 GitHub 发布资产不可变，Release 不再额外附带集成专用 ZIP；HACS 安装不受影响。

## 配置

设置 → 设备与服务 → 添加集成 → 搜索 "张家界供水"

### 必填参数

| 参数 | 说明 | 获取方式 |
|-----|------|---------|
| 户号 | 供水公司分配的客户编号 | 水费账单或供水公司查询 |
| OpenID | 微信用户标识 | 见下方获取方法 |
| 账户名称 | 显示名称（可选） | 自定义，如"家中水表" |

### 获取 OpenID

OpenID 是微信公众号的用户标识，获取方法：

1. 手机安装 [Stream](https://getstream.io/) 抓包工具
2. Stream → 抓包 → 打开微信
3. 进入「张家界供水」公众号 → 水费缴纳
4. 回到 Stream → 停止抓包 → 筛选 `ccpay.thiscc.com`
5. 找到 POST `searchRecord.action` 请求，查看请求体中的 `wxid` 参数

示例请求：
```
type=1&custCode=123456789,1,10,1&wxid=oXxXxXxXxXxXxXxXxXxXxXxXxX
```

其中 `oXxXxXxXxXxXxXxXxXxXxXxXxX` 即为 OpenID。

## 传感器

### 缴费信息

| 传感器 | 单位 | 说明 |
|--------|-----|------|
| balance | ¥ | 账户余额（最近一次缴费后余额） |
| last_payment_date | - | 最近缴费日期 |
| last_payment_time | - | 最近缴费时间 |
| last_payment_amount | ¥ | 最近缴费金额 |
| previous_balance | ¥ | 上次结余 |
| invoice_code | - | 发票编码 |
| customer_code | - | 客户编码（户号） |

### 用水信息

| 传感器 | 单位 | 说明 |
|--------|-----|------|
| current_usage | m³ | 本期用水量 |
| current_bill | ¥ | 本期费用合计 |
| current_water_fee | ¥ | 本月水费 |
| other_fees | ¥ | 其他费用 |
| sewage_fee | ¥ | 污水处理费 |
| garbage_fee | ¥ | 垃圾处理费 |
| current_month_reading | - | 本月表数 |
| previous_month_reading | - | 上月表数 |
| latest_reading | - | 最新抄表读数 |
| latest_reading_month | - | 抄表月份 |
| total_water | m³ | 累计用水（表读数，total_increasing） |

### 年度统计

| 传感器 | 单位 | 说明 |
|--------|-----|------|
| annual_usage | m³ | 年累计用水量 |
| annual_bill | ¥ | 年累计水费 |

### 其他实体

| 实体 | 类型 | 说明 |
|------|------|------|
| 余额不足 | 二进制传感器 | 余额低于选项中配置的阈值时开启（0 = 关闭，默认） |
| 刷新数据 | 按钮 | 手动触发数据刷新 |
| 本期用水量（属性） | - | `monthly_usage`：本年度逐月用水量与费用 |
| 上次缴费金额（属性） | - | `recent_payments`：最近 5 笔缴费记录 |

### 加入能源面板水耗统计

「累计用水」传感器（`total_water`，m³，total_increasing）可直接加入 HA 能源面板：

设置 → 仪表盘 → 能源 → **水耗个体用量** → 添加该传感器。HA 会按表读数差值自动统计日/月/年用水量。

配置时会**实际调用 API 验证**户号与 OpenID，填写错误会立即提示，无需等到加载后查日志。

## 自动化蓝图

v3.4.1 起**蓝图随集成自动部署**：HACS 安装/升级后，集成启动时会自动把两个蓝图复制到 `<配置目录>/blueprints/automation/`，在 设置 → 自动化与场景 → 蓝图 中直接可用，无需导入。

| 蓝图 | 说明 |
|------|------|
| 低余额提醒 | 「余额不足」开启时发通知（需先在集成选项中配置阈值） |
| 高用水提醒 | 本期用水量超过阈值（m³）时发通知 |

也可以点击链接一键导入（设置 → 自动化 → 蓝图 → 导入蓝图）：

| 蓝图 | 导入链接 |
|------|---------|
| 低余额提醒 | [导入](https://myhomeassistant.io/redirect/blueprint/?repo=yahooor%2Fzhangjiajie_water_ha&path=blueprints%2Fautomation%2Fzhangjiajie_water_low_balance.yaml) |
| 高用水提醒 | [导入](https://myhomeassistant.io/redirect/blueprint/?repo=yahooor%2Fzhangjiajie_water_ha&path=blueprints%2Fautomation%2Fzhangjiajie_water_high_usage.yaml) |

## 数据说明

- **余额**：为最近一次缴费后的余额快照，非实时余额
- **费用构成**：current_bill 为合计（含水费 + 污水处理费 + 垃圾处理费 + 其他费用），可对照各分项传感器；某分项为 0 表示本期账单未产生该项费用
- **上次缴费金额为 0**：上游 type=2 记录同时包含人工缴费与账单自动扣款——扣款记录的缴费金额为 0，实际扣款额 = 上次结余 − 账户余额（详见"上次缴费金额"传感器 `recent_payments` 属性中的 `balance_change` 字段）
- **表数**：current_month_reading / previous_month_reading 为当月和上月抄表读数，差值即为用水量
- **更新间隔**：默认 6 小时，可在集成选项中修改（1~24小时）

## 注意事项

- 本集成仅支持张家界市自来水有限责任公司用户
- OpenID 与微信号绑定，更换微信需重新获取；**凭据失效时**集成页面会出现「重新配置」提示，输入新的微信 OpenID 即可完成重新认证，无需删除重建
- 数据来自供水公司微信公众号接口，仅供个人使用

## Lovelace 卡片

内置自定义 Lovelace 卡片。集成启动时会自动把卡片文件和 Logo 复制到 `<配置目录>/www/zhangjiajie_water/`，只需一次性注册资源：

1. 设置 → 仪表盘 → 右上角 **⋮** → **管理资源** → **添加资源**
2. URL 填 `/local/zhangjiajie_water/zhangjiajie-water-card.js`，类型选 **JavaScript 模块**
3. 刷新浏览器后在卡片编辑器中搜索「张家界供水卡片」

### 卡片配置

```yaml
type: custom:zhangjiajie-water-card
# 多账户时（可选）：指定该账户下任一传感器实体，将卡片绑定到该账户
# entity: sensor.xxx
```

v3.2.0 起卡片通过**实体注册表**自动发现本集成的实体（中英文实体名、拼音实体 ID 均可识别），并支持多账户绑定；标题右侧会在余额不足时显示红色提示；摘要区下方展示**月度用水趋势柱状图**（数据来自本期用水量的 `monthly_usage` 属性）。

> 注：v3.1 时代的 `entity_prefix` 配置已废弃（无法匹配中文实体名），请改用 `entity`。

### 刷新模式

在集成选项（设置 → 设备与服务 → 张家界供水 → 配置）中可选择：

| 模式 | 说明 |
|------|------|
| **固定间隔**（默认） | 每 N 小时刷新一次（1~24 小时可调） |
| **每日定时** | 每天指定时间（默认 07:30）刷新一次，适合节省流量 |

另可配置**低余额提醒阈值**（元）：余额低于该值时「余额不足」传感器开启，`0` 表示关闭。

## 更新日志

### v3.4.1 (2026-10-24)

- **蓝图自动部署**：两个自动化蓝图随集成分发，启动时自动复制到 `<配置目录>/blueprints/automation/`（此前 HACS 只装集成目录，仓库根的蓝图根本不会上机，一键导入链接形同虚设）

### v3.4.0 (2026-10-24)

- **重新认证流程**：户号/OpenID 被服务端拒绝时（业务错误码），协调器抛出 `ConfigEntryAuthFailed`，HA 会在集成页面弹出「重新配置」，输入新 OpenID 即可恢复，替代以往仅靠持久通知提示的方式；诊断接口同时可看到原始记录（上一版已含）

### v3.3.2 (2026-10-24)

- **修复**：`_merge_data` 未把 `_usage_records`/`_payment_records` 并入合并数据——逐月历史属性（`monthly_usage`）与卡片月度用水趋势图的数据源一直为空
- 缴费历史属性新增 `balance_before`/`balance_change` 字段：上游记录中"缴费金额 0"是账单自动扣款（实际扣款额 = 上次结余 − 本次余额），属性与数据说明均已标注

### v3.3.1 (2026-10-24)

- 发版流水线适配 GitHub tag 保护规则与发布资产不可变策略（v3.3.0 tag 因不可变记录无法复用，跳版至 3.3.1）

### v3.3.0 (2026-10-24)

- **修复跨年空窗**：每年 1 月本年账单未出时，用水量/读数不再变 unknown，回退显示最近一条跨年记录（年累计仍按本年计 0）
- **修复诊断脱敏**：`customer_code`（值为户号）加入脱敏列表
- **能源面板水耗**：新增「累计用水」传感器（`total_increasing` + m³），可直接加入 HA 能源面板的水耗统计
- **卡片趋势图**：摘要区下方新增月度用水柱状图；检测到已废弃的 `entity_prefix` 配置时给出控制台提示
- **自动化蓝图**：内置低余额、高用水提醒两个蓝图，README 提供一键导入链接
- **测试与 Lint**：纯函数抽取到 `utils.py`（不依赖 HA），CI 新增 pytest 单元测试与 Ruff 检查

### v3.2.0 (2026-10-24)

- **修复 CI**：`hacs.json` 非法键 `render_readme_as_markdown` 导致 Validate 工作流自 5 月起每日失败，改回 `render_readme`
- **修复发布流水线**：release.yml 的版本提取正则与「单一来源」改造后的 const.py 不再匹配，v3.1.0 起 Release 一直失败，改为直接 import 读取
- **修复内置卡片部署**：卡片文件从未被 `/local/` 服务过（缺少复制步骤），现集成启动时自动复制到 `<配置目录>/www/zhangjiajie_water/`
- **修复卡片实体探测**：旧版 `*_balance` 后缀探测无法匹配中文实体名（拼音实体 ID），改为基于实体注册表发现，支持多账户绑定（`entity` 配置）
- **修复每日定时失效**：首刷失败时不再跳过定时器注册
- **请求超时**：共享 session 补上 20 秒单请求超时，接口挂起不再拖满 5 分钟
- **配置验证**：添加集成时实测户号/OpenID，错误立即反馈
- **新增**：低余额二进制传感器（阈值可配）、下载诊断支持（凭据脱敏）、逐月用水与缴费历史属性、抄表数据自检告警
- **选项流**：模式下拉与数字输入改用标准选择器，数值边界在 UI 层校验

### v3.1.0 (2026-05-08)

- 版本号单一来源：const.py 改为从 manifest.json 读取
- 翻译补全、暗色模式适配、代码质量优化

### v3.0.0 (2026-05-08)

- **架构重构**：代码拆分为 `api.py`（API 客户端）+ `coordinator.py`（数据协调器）+ `__init__.py`（精简入口）
- **混合刷新模式**：支持"每日定时"（`async_track_time_change`）和"固定间隔"两种刷新策略，可在选项中切换
- **SensorEntityDescription 重构**：传感器使用 `@dataclass + value_fn` 模式，代码更简洁、可扩展
- **内置 Lovelace 卡片**：新增 `www/zhangjiajie-water-card.js`（LitElement，无需构建），展示余额/用水/费用/年累计等信息
- **ConfigEntry VERSION 升至 2**：添加 `async_migrate_entry` 自动迁移旧版配置，现有用户升级无感
- **coordinator.async_shutdown()**：卸载时正确清理每日定时监听器，避免内存泄漏
- **OptionsFlow 扩展**：新增刷新模式、定时小时、定时分钟配置项
- 借鉴 [合肥供水集成](https://github.com/Cyborg2017/ha_hfwater) 最佳实践

### [v2.7.0](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.7.0) (2026-05-08)

- **手动刷新按钮**：新增"刷新数据"按钮实体，用户可随时手动触发数据更新
- **API 失败通知**：连续 3 次刷新失败后自动发送 HA 持久通知，引导用户排查
- **`_attr_has_entity_name`**：传感器实体启用标准命名，显示为"设备名 + 实体名"
- **`integration_type: "device"`**：manifest.json 声明设备类型集成
- 借鉴 [温州水务集成](https://github.com/C3H3-AI/ha-wenzhou-water) 最佳实践

### [v2.6.2](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.6.2) (2026-05-07)

- **紧急修复**：`UpdateFailed` 从 `homeassistant.helpers.update_coordinator` 导入（非 `homeassistant.exceptions`）
- **manifest.json 规范**：keys 按 Hassfest 要求排序（domain, name, alphabetical）

### [v2.6.1](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.6.1) (2026-05-07)

- **GitHub Actions CI/CD**：新增自动验证 + 发布流程
  - 每次 push/PR 自动运行 HACS + Hassfest 验证
  - 发布 Release 时自动校验版本号一致性（tag/manifest/const）
- **HACS 安装修复**：移除 `zip_release`，恢复默认下载方式（更可靠）
- **manifest.json 规范**：移除 Hassfest 不允许的 `icon` 字段

### [v2.5.1](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.5.1) (2026-05-07)

- **Logo 替换**：使用官方张家界供水 Logo 重新生成全部 brand 图片和组件图标
- **UpdateFailed 异常**：`_async_update_data` 改用 `UpdateFailed`，HA UI 显示友好错误信息
- **智能重试优化**：API 业务错误码（如户号错误）和 HTTP 4xx 不再无意义重试
- **移除多余依赖**：`manifest.json` 删除 `aiohttp`（HA 核心已自带）
- **诊断传感器分类**：`发票编码`、`客户编码` 归入诊断类别，不 clutter 主传感器列表
- **日志配置增强**：`manifest.json` 添加 `loggers` 字段，支持在集成详情页直接调日志级别
- **更新日志整合**：合并 v2.2.0 之前碎片化版本记录，修正 v2.4.0 内容错误

> ⚠️ **HACS 仓库列表不显示 Logo 已知问题**：这是 HACS 的 [已知 Bug #5171](https://github.com/hacs/integration/issues/5171)——HACS 前端仍从 CDN 获取图标，未回退到本地 brands API。Logo 在 HA 集成页面正常显示，等待 HACS 上游修复。

### [v2.4.0](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.4.0) (2026-05-06)

- **年度传感器跨年修复**：年度传感器名称在跨年后自动更新年份
- **HA 共享 session**：API 客户端改用共享连接池，避免资源泄漏
- **annual_usage 类型优化**：从 `TOTAL_INCREASING` 改为 `MEASUREMENT`，避免跨年数据跳跃
- **hacs.json**：添加 `render_readme: true`
- **类型注解修复**：`_safe_float` 函数支持 `float | None` 返回值

### [v2.3.15](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.3.15) (2026-05-06)

- **日志级别调整**：Coordinator 初始化和轮询日志从 WARNING 降为 DEBUG，消除 HA 误报

### [v2.3.14](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.3.14) (2026-05-05)

- **轮询修复**：`DataUpdateCoordinator` 添加 `config_entry` 参数，修复定时轮询不生效
- **增强日志**：Coordinator 改用 WARNING 级别，便于排查

### [v2.3.13](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.3.13) (2026-05-05)

- **ZIP 打包结构修复**：根目录改为 `custom_components/zhangjiajie_water/`
- **中文乱码修复**：改用 base64 编码上传
- **版本号统一**：`const.py` 和 `manifest.json` 同步

### [v2.3.10](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.3.10) ~ [v2.3.12](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.3.12) (2026-05-05)

- Python 文件 UTF-8 编码全面修复，brand 图片二进制修复，文件树重建

### [v2.3.6](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.3.6) ~ [v2.3.8](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.3.8) (2026-05-05)

- zh-Hans.json 乱码修复，Python 文件编码尝试修复（v2.3.10 最终修复）

### [v2.3.4](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.3.4) (2026-05-04)

- **翻译文件结构修复**：删除错误的 `config.` 前缀，BCP47 改为 `zh-Hans.json`

### [v2.3.2](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.3.2) (2026-05-04)

- **P0 跨年分页 bug 修复**：改为逐条过滤 `ysny`，避免边界页数据丢失
- **P0 async_close race condition 修复**：加 `_closed` flag 保护
- 9 文件全量代码审查（+66/-50）

### [v2.3.1](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.3.1) (2026-05-04)

- **OptionsFlow 三重操作冲突修复**：简化为标准 `async_create_entry` 模式

### [v2.3.0](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.3.0) (2026-05-04)

- OptionsFlow 持久化修复 + listener leak 修复
- TIMESTAMP 时区修复

### [v2.2.0](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.2.0) (2026-05-04)

- **传感器从 9 个扩展到 19 个**：新增污水费、垃圾费、附加费、月度详情等
- sfsj 时间格式 3 层兼容（[v2.2.1](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.2.1)）
- TIMESTAMP 缺时区修复（[v2.2.2](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.2.2)）
- OptionsFlow 持久化尝试（[v2.2.3](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.2.3)~v2.2.5，v2.3.1 彻底修复）

### [v2.0.0](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.0.0) (2026-05-01)

- **版本号 PEP 440 合规**：从 `1.2.x` 跳到 `2.x`，避免 a/b/rc 后缀导致 HA 拒绝加载
- sensor.py datetime import 修复（[v2.1.1](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.1.1)）
- 其他 Bug 修复（[v2.0.2](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.0.2)~[v2.1.3](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.1.3)）

### [v1.0.0](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v1.2.0) ~ [v1.2.5](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v1.2.5) (2026-05-01)

- **首发**：9 个传感器，OpenID + 户号认证
- **新增**：Options Flow（1~24 小时刷新间隔）+ 中文翻译 + SensorStateClass 长期统计（v1.1.0）
- **修复**：金额单位改为 CNY、latest_reading 改为 MEASUREMENT、`_safe_float()` 防护（[v1.2.0](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v1.2.0)）
- **修复**：翻页逻辑致命错误、跨年数据混入、brand/ 品牌图标、last_payment_date 类型判断（v1.2.1~v1.2.5）

## License

MIT
