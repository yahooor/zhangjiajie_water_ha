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

### [v2.5.0](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.5.0) (2026-05-06)

- **Logo 替换**：使用官方张家界供水 Logo 重新生成全部 brand 图片和组件图标
- **更新日志整合**：合并 v2.2.0 之前碎片化的版本记录，所有版本链接到正确的 GitHub Release

> ⚠️ **HACS 仓库列表不显示 Logo 已知问题**：这是 HACS 的 [已知 Bug #5171](https://github.com/hacs/integration/issues/5171)——HACS 前端仍从 CDN 获取图标，未回退到本地 brands API。Logo 在 HA 集成页面正常显示，等待 HACS 上游修复。

### [v2.4.0](https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.4.0) (2026-05-06)

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
