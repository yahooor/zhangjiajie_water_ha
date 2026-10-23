#!/bin/bash
# 一键推送 + 发布脚本（版本号自动读取 manifest.json，无需手动同步）
# 在 zhangjiajie_water_ha 目录下运行
# 用法: bash publish.sh

set -e
cd "$(dirname "$0")"

VER=$(python3 -c "import json; print(json.load(open('custom_components/zhangjiajie_water/manifest.json'))['version'])")

echo ">>> 推送代码到 GitHub..."
git push origin main

echo ">>> 创建 GitHub Release v${VER}..."
export GH_TOKEN=$(git credential fill <<EOF | grep "^password=" | cut -d= -f2
protocol=https
host=github.com
EOF
)

gh release create "v${VER}" \
  --repo yahooor/zhangjiajie_water_ha \
  --title "v${VER}" \
  --notes "更新日志见 README：https://github.com/yahooor/zhangjiajie_water_ha#更新日志"

echo ""
echo "✅ 发布完成！"
echo "Release: https://github.com/yahooor/zhangjiajie_water_ha/releases/tag/v${VER}"
echo ""
echo ">>> 注意：GitHub Actions 会自动："
echo "  1. 运行 HACS + Hassfest 验证"
echo "  2. 校验版本号一致性（tag / manifest / const）"
echo "  3. 打包 zhangjiajie_water.zip 上传到 Release"
