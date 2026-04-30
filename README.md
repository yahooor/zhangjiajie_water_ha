# 张家界供水 - Home Assistant 集成

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)

张家界市自来水有限责任公司水费查询 Home Assistant 自定义集成。

## 安装

### HACS（推荐）

1. HACS → 集成 → 右上角三个点 → 自定义仓库
2. 添加 `https://github.com/yahooor/zhangjiajie_water_ha`，类型选「集成」
3. 搜索「张家界供水」并安装
4. 重启 Home Assistant

### 手动安装

1. 下载 [最新发布](https://github.com/yahooor/zhangjiajie_water_ha/releases/latest)
2. 解压到 `custom_components/zhangjiajie_water/`
3. 重启 Home Assistant

## 配置

1. 设置 → 设备与服务 → 添加集成 → 搜索「张家界供水」
2. 填写：
   - **户号**：账单上的用户编号（如 115062401）
   - **微信 OpenID**：从微信抓包获取（见下方说明）
   - **账户名称**（可选）：自定义显示名称

### 获取微信 OpenID

1. 手机安装 Stream 抓包工具
2. 在微信中打开「张家界供水」公众号 → 营业厅 → 查水费
3. 在抓包列表中找到 `ccpay.thiscc.com` 的请求
4. 请求体中 `wxid` 参数即为 OpenID

## 传感器

| 传感器 | 说明 | 单位 |
|--------|------|------|
| 账户余额 | 当前账户余额 | 元 |
| 上次缴费日期 | 最近一次缴费时间 | - |
| 上次缴费金额 | 最近一次缴费金额 | 元 |
| 本期用水量 | 最近抄表周期用水量 | m3 |
| 本期水费 | 最近抄表周期水费 | 元 |
| 最新读数 | 水表最新读数 | m3 |
| 抄表月份 | 最近抄表月份 | - |
| 年累计用水 | 当前年度累计用水 | m3 |
| 年累计水费 | 当前年度累计水费 | 元 |

数据每 6 小时更新一次。

## License

MIT