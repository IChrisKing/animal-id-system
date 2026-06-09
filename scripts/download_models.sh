#!/bin/bash
# 下载模型权重脚本
set -euo pipefail

MODEL_DIR="src/models"
mkdir -p "$MODEL_DIR"

echo "=== 下载模型权重 ==="

# YOLOv8s (COCO 预训练) — ~22 MB
echo "[1/2] 下载 YOLOv8s..."
if [ -f "$MODEL_DIR/yolov8s.pt" ]; then
    echo "  ✓ yolov8s.pt 已存在，跳过"
else
    # ultralytics 会自动下载，这里提供一个手动下载的备选方案
    wget -q --show-progress -O "$MODEL_DIR/yolov8s.pt" \
        "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8s.pt" \
        || echo "  ⚠️  下载失败，首次运行时会自动从 ultralytics 下载"
fi

# ResNet50 Re-ID — ~98 MB
echo "[2/2] 下载 ResNet50 Re-ID 权重..."
if [ -f "$MODEL_DIR/resnet50_reid.pt" ]; then
    echo "  ✓ resnet50_reid.pt 已存在，跳过"
else
    echo "  ⚠️  Re-ID 模型需要手动准备，请参考 design.md 附录 B"
fi

echo ""
echo "=== 模型下载完成 ==="
echo "YOLO: $( [ -f "$MODEL_DIR/yolov8s.pt" ] && echo '✅' || echo '❌' )"
echo "Re-ID: $( [ -f "$MODEL_DIR/resnet50_reid.pt" ] && echo '✅' || echo '❌ (需手动准备)' )"
