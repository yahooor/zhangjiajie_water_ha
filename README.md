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

### v2.4.0 (2026-05-06)
- **HACS Logo 修复**：`brand/logo.png` 和 `dark_logo.png` 改为 640x320 横幅格式，HACS 仓库列表现在正确展示 logo
- **Brand 图片区分**：icon（正方形 640x640）和 logo（横幅 640x320）分别生成，亮色/暗色各一套
- **年度传感器跨年修复**：年度传感器名称（如"2026年累计用水"）在跨年后自动更新年份
- **HA 共享 session**：API 客户端改用 `async_get_clientsession(hass)` 共享连接池，避免资源泄漏
- **annual_usage 类型优化**：从 `TOTAL_INCREASING` 改为 `MEASUREMENT`，避免跨年数据跳跃
- **hacs.json**：添加 `render_readme: true`，HACS 正确渲染 README
- **类型注解修复**：`_safe_float` 函数支持 `float | None` 返回值
- **.gitignore 清理**：删除末尾 UTF-16 乱码行
- **icon.png 压缩**：组件图标从 38KB 优化到 ~2KB

### v2.3.15 (2026-05-06)
- **日志级别调整**：Coordinator 初始化和轮询日志从 WARNING 降为 DEBUG，消除 HA 误报"此错误来自自定义集成"

### v2.3.14 (2026-05-05)
- **轮询修复**：`DataUpdateCoordinator` 添加 `config_entry` 参数，修复定时轮询不生效问题
- **增强日志**：Coordinator 初始化和数据刷新改用 WARNING 级别，便于排查问题

### v2.3.13 (2026-05-05)
- **ZIP 打包结构修复**：根目录从 `zhangjiajie_water/` 改为 `custom_components/zhangjiajie_water/`，与 HACS 期望路径一致
- **`__init__.py` 中文乱码修复**：GitHub blob 上传改用 base64 编码，修复 manufacturer/model 字符串乱码
- **版本号统一**：`const.py` 和 `manifest.json` 版本号同步为 2.3.13
- **Logo 图片修复**：重新生成 5 张 PNG（icon 256x256，brand/ 四张 640x640）

### v2.3.12 (2026-05-05)
- **重新打包**：v2.3.11 丢失 9 个文件，基于 v2.3.10 完整 tree 重建 19 个文件

### v2.3.11 (2026-05-05)
- **brand 图片编码修复**：改用 base64 编码上传，修复二进制损坏
- **仓库文件恢复**：重建完整文件树（19 个文件）

### v2.3.10 (2026-05-05)
- **Python 文件 UTF-8 编码全面修复**：全部改用 base64 上传，解决中文双编码问题

### v2.3.8 (2026-05-05)
- 尝试修复 Python 文件编码问题（v2.3.10 最终修复）

### v2.3.6 (2026-05-05)
- **zh-Hans.json 乱码修复**：解决翻译文件中文显示乱码

### v2.3.4 (2026-05-04)
- **翻译文件结构修复**：删除错误的 `config.` 前缀，BCP47 改为 `zh-Hans.json`

### v2.3.2 (2026-05-04)
- **P0 跨年分页 bug 修复**：改为逐条过滤 `ysny`，避免边界页数据丢失
- **P0 async_close race condition 修复**：加 `_closed` flag 保护
- 9 文件全量代码审查（+66/-50）

### v2.3.1 (2026-05-04)
- **OptionsFlow 三重操作冲突修复**：简化为标准 `async_create_entry` 模式

### v2.3.0 (2026-05-04)
- OptionsFlow 持久化修复 + listener leak 修复
- TIMESTAMP 时区修复

### v2.2.5 (2026-05-04)
- OptionsFlow 持久化尝试（后由 v2.3.1 彻底修复）

### v2.2.2 (2026-05-04)
- **TIMESTAMP 缺时区修复**：缴费时间添加时区信息

### v2.2.1 (2026-05-04)
- **sfsj 时间格式 3 层兼容**：支持多种日期格式解析

### v2.2.0 (2026-05-04)
- **传感器从 9 个扩展到 19 个**：新增污水费、垃圾费、附加费、月度详情等

### v2.0.0 (2026-05-01)
- **版本号 PEP 440 合规**：从 `1.2.x` 系列跳到 `2.x`，避免 a/b/rc 后缀导致 HA 拒绝加载

### v1.2.5 (2026-05-01)
- **修复**：`last_payment_date` 增加 `isinstance(value, date)` 判断
- MONETARY 传感器 `state_class` 设为 `None`

### v1.2.4 (2026-05-01)
- 添加 brand/ 品牌图标

### v1.2.3 (2026-05-01)
- **修复**：`_fetch_usage` 跨年数据混入

### v1.2.1 (2026-05-01)
- **修复**：翻页逻辑致命错误（annual 数据严重偏少）
- **修复**：版本号不一致

### v1.2.0 (2026-05-01)
- **修复**：金额单位改为 CNY（ISO 4217）
- **修复**：latest_reading 改为 MEASUREMENT
- **新增**：`_safe_float()` 函数防护非法值

### v1.1.0 (2026-05-01)
- **新增**：Options Flow（1~24 小时刷新间隔）
- **新增**：中文翻译 + SensorStateClass 支持长期统计

### v1.0.0 (2026-05-01)
- **首发**：张家界供水 HA 集成，9 个传感器，OpenID + 户号认证

## License

MIT
