#!/bin/bash
# 一键推送 + 发版脚本（版本号自动读取 manifest.json，无需手动同步）
# 在 zhangjiajie_water_ha 目录下运行
# 用法: bash publish.sh
#
# 发版流程：推送 v* tag → GitHub Actions 自动验证并
# 以「草稿 → 上传 ZIP → 发布」方式创建 Release（GitHub 资产不可变策略要求）

set -e
cd "$(dirname "$0")"

VER=$(python3 -c "import json; print(json.load(open('custom_components/zhangjiajie_water/manifest.json'))['version'])")

echo ">>> 推送代码到 GitHub..."
git push origin main

echo ">>> 创建并推送 tag v${VER}（触发发版流水线）..."
git tag "v${VER}"
git push origin "v${VER}"

echo ""
echo "✅ tag 已推送，发版进行中："
echo "https://github.com/yahooor/zhangjiajie_water_ha/actions"
echo "Release 将出现在: https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v${VER}"
echo ""
echo ">>> 流水线自动执行："
echo "  1. 版本一致性校验（tag / manifest / const）"
echo "  2. HACS + Hassfest 验证"
echo "  3. 打包 zhangjiajie_water.zip 并随 Release 发布"
