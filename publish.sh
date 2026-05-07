#!/bin/bash
# 一键推送 + 发布脚本
# 在 zhangjiajie_water_ha 目录下运行
# 用法: bash publish.sh

set -e

echo ">>> 推送代码到 GitHub..."
git push origin main

echo ">>> 创建 GitHub Release v2.6.0..."
export GH_TOKEN=$(git credential fill <<EOF | grep "^password=" | cut -d= -f2
protocol=https
host=github.com
EOF
)

gh release create v2.6.0 \
  --repo yahooor/zhangjiajie_water_ha \
  --title "v2.6.0" \
  --notes '## v2.6.0 CI/CD 自动化

### 新增
- **GitHub Actions CI/CD**：自动验证 + 发布流程
  - 每次 push/PR 自动运行 HACS + Hassfest 验证
  - 发布 Release 时自动校验版本号一致性
  - 自动打包 ZIP 并上传为 Release Asset
- **HACS ZIP 发布**：`hacs.json` 启用 `zip_release`，安装更可靠

### 修复
- **UpdateFailed 异常**：`_async_update_data` 改用 `UpdateFailed`，HA UI 显示友好错误
- **智能重试**：API 业务错误码和 HTTP 4xx 不再无意义重试
- **依赖清理**：移除多余 `aiohttp` 依赖
- **诊断传感器**：`发票编码`、`客户编码` 归入诊断类别
- **日志增强**：`manifest.json` 添加 `loggers` 字段

**完整更新日志**: https://github.com/yahooor/zhangjiajie_water_ha#更新日志'

echo ""
echo "✅ 发布完成！"
echo "Release: https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v2.6.0"
echo ""
echo ">>> 注意：GitHub Actions 会自动："
echo "  1. 运行 HACS + Hassfest 验证"
echo "  2. 校验版本号一致性"
echo "  3. 打包 zhangjiajie_water.zip 上传到 Release"
