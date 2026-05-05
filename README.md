# 张家界供水

Home Assistant 自定义集成，通过抓取张家界供水微信公众号获取用水数据。

## 功能

| 功能类别 | 具体内容 |
|---------|---------|
| 💧 用水记录 | 月度用水量、抄表读数、水费明细 |
| 💰 缴费记录 | 缴费时间、金额、余额、方式 |
| 📊 年度统计 | 年累计用水量、年累计水费 |
| 🔄 自动更新 | 默认 6 小时刷新一次 |
| 🏠 多户支持 | 支持添加多个供水账户 |

## 安装

### HACS（推荐）

1. HACS → 集成 → 添加自定义仓库：`https://github.com/yahooor/zhangjiajie_water_ha`
2. 搜索 "张家界供水" 安装
3. 重启 Home Assistant

### 手动安装

1. 下载 [最新版本](https://github.com/yahooor/zhangjiajie_water_ha/releases/latest)
2. 解压到 `custom_components/zhangjiajie_water/` 目录
3. 重启 Home Assistant

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

### 年度统计

| 传感器 | 单位 | 说明 |
|--------|-----|------|
| annual_usage | m³ | 年累计用水量 |
| annual_bill | ¥ | 年累计水费 |

## 数据说明

- **余额**：为最近一次缴费后的余额快照，非实时余额
- **费用构成**：current_bill 为合计（含水费 + 污水处理费 + 垃圾处理费 + 其他费用），可对照各分项传感器
- **表数**：current_month_reading / previous_month_reading 为当月和上月抄表读数，差值即为用水量
- **更新间隔**：默认 6 小时，可在集成选项中修改（1~24小时）

## 注意事项

- 本集成仅支持张家界市自来水有限责任公司用户
- OpenID 与微信号绑定，更换微信需重新获取
- 数据来自供水公司微信公众号接口，仅供个人使用

## 更新日志

### v2.3.13 (2026-05-05)
- **ZIP 打包结构修复**：v2.3.12 的 ZIP 根目录为 `zhangjiajie_water/`，与 HACS 期望的 `custom_components/zhangjiajie_water/` 不匹配，导致安装失败
- **`__init__.py` 中文乱码修复**：GitHub blob 上传时 `encoding: utf-8` 导致中文字符串（manufacturer/model）运行时乱码，改用 base64 编码上传
- **版本号统一**：`const.py` INTEGRATION_VERSION 从 2.3.5 更新到 2.3.13，`manifest.json` 同步更新

### v2.3.12 (2026-05-05)
- **重新打包**：v2.3.11 commit 只有 10 文件（丢失 brand/translations/icon.png/__init__.py），基于 v2.3.10 的 19 文件完整 tree 重建

### v1.2.5 (2026-05-01)
- **修复**：`last_payment_date` 的 `native_value` 增加 `isinstance(value, date)` 判断，避免重复解析 date 对象
- 字符串解析失败时返回 `None`
- MONETARY 传感器 `state_class` 设为 `None`

### v2.3.11 (2026-05-05)
- **brand 图片编码修复**：`brand/*.png` 4 个文件因 GitHub blob 上传时使用 `encoding: utf-8` 导致二进制图片数据损坏，GitHub 在线查看显示乱码。本版本已通过 base64 编码重新上传
- **仓库文件恢复**：由于操作失误导致仓库只剩 brand 目录，本版本重建完整文件树（19 个文件）
- **版本号修复**：`manifest.json` 从 2.3.8 更新到 2.3.11

### v2.3.10 (2026-05-05)
- **Python 文件 UTF-8 编码全面修复**：重新上传 `__init__.py`、`sensor.py`、`config_flow.py`，通过 base64 编码避免 UTF-8 双编码问题
- **版本号修复**：`manifest.json` 更新到 2.3.8

### v1.2.4 (2026-05-01)
- 添加 brand/ 品牌图标（dark_icon、dark_logo、icon、logo）

### v1.2.3 (2026-05-01)
- **修复**：`_fetch_usage` 跨年数据混入 — 先检查 `records[0].ysny` 是否为本年，再决定是否 extend，避免将旧年度数据混入本年统计
- 删除冗余的 `first_ym` 变量赋值

### v1.2.2 (2026-05-01)
- **同步**：README 与 GitHub 在线仓库保持一致

### v1.2.1 (2026-05-01)
- **修复**：翻页逻辑致命错误 — `current_year` 判断从 `records[-1]` 改为 `records[0]`，此前 annual_usage/annual_bill 数据严重偏少
- **修复**：const.py 版本号 1.2.0 与 manifest.json 1.2.1 不一致，已统一为 1.2.1
- **修复**：last_payment_amount 缺少 state_class，已补上 MEASUREMENT

### v1.2.0 (2026-05-01)
- **修复**：金额单位 `"元"` → `"CNY"`（ISO 4217 货币码，MONETARY device_class 规范要求）
- **修复**：latest_reading 改为 `SensorStateClass.MEASUREMENT`（水表读数非累计增量，换表回退不再触发 HA 警告）
- **修复**：年度传感器年份前缀不显示 → 使用 `translation_placeholders` 注入年份，实体名正确显示如 "2026年累计用水"
- **修复**：`float()` 未防护非法值 → 新增 `_safe_float()` 函数，API 返回非数字不再导致整次更新失败
- **优化**：`sw_version` 改为跟踪集成版本号

### v1.1.0 (2026-05-01)
- **新增**：Options Flow — 支持在集成选项中调整刷新间隔（1~24小时）
- **新增**：translations/zh.json — 配置流和选项界面完整中文翻译
- **新增**：`_attr_has_entity_name = True` + `translation_key` — HA 2024.1+ 实体命名规范
- **新增**：`SensorStateClass` — 余额/用量 MEASUREMENT，累计 TOTAL_INCREASING，支持长期统计
- **新增**：`issue_tracker` — manifest 添加 Issues 链接
- **修复**：latest_read 单位移除 m³（读数无量纲）
- **优化**：strings.json 增加 options 和 entity 翻译段

### v1.0.1 (2026-05-01)
- 优化配置流中文字段标签（户号/账户名称）
- 全量代码逻辑审查通过

### v1.0.0 (2026-05-01)
- **首发**：张家界供水 HA 集成首发
- 支持 9 个传感器：余额、缴费、用水、读数、年度统计
- OpenID + 户号认证，无需用户名密码
- HACS 兼容目录结构

## License

MIT
