# Animal ID System

基于混合架构的动物识别与档案管理系统 — YOLO 本地检测 + 多模态 LLM API 分类 + 猫个体 Re-ID 匹配。

## 架构概览

```
本地 YOLO 检测         多模态 LLM API 分类        猫个体 Re-ID 匹配
(快速定位动物位置)  +  (精确判定动物类别)      +  (仅猫区分个体)
     ↓                      ↓                        ↓
  免费/快速             按量付费/高精度            免费/高频调用
```

## 支持的动物

- 🐱 **猫** (Cat)
- 🦦 **黄鼠狼** (Weasel)
- 🐦 **鸟** (Bird)

## 支持的格式

| 类型 | 格式 |
|------|------|
| 图片 | JPEG, PNG, BMP, TIFF, WebP, GIF |
| 视频 | MP4, AVI, MOV, MKV, WMV, FLV |

## 快速开始

```bash
# 1. 克隆仓库
git clone <repo_url>
cd animal-id-system

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 下载模型
bash scripts/download_models.sh

# 5. 配置 API Key
export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxx"

# 6. 运行
python -m src.main scan /path/to/media/
```

## 使用示例

```bash
# 扫描图片目录
animal-id scan ~/Pictures/wildlife/

# 扫描视频
animal-id scan ~/Videos/backyard.mp4

# 列出所有已识别的动物
animal-id list

# 按类别筛选
animal-id list --class cat

# 查看某只动物的档案
animal-id show cat_a3f2b1c0

# 导出档案数据
animal-id export --output profiles.json

# 查看统计
animal-id stats
```

## 项目结构

```
animal-id-system/
├── design.md                # 详细设计文档
├── README.md
├── requirements.txt
├── config.yaml
├── src/
│   ├── main.py
│   ├── cli.py
│   ├── pipeline.py
│   ├── input_module/
│   ├── recognition/
│   ├── archive/
│   ├── storage/
│   └── utils/
├── tests/
├── scripts/
├── data/
└── logs/
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 目标检测 | YOLOv8 (本地) |
| 动物分类 | DeepSeek / Claude API (云端) |
| 猫个体重识别 | ResNet50 (本地，仅猫) |
| 鸟/黄鼠狼 | 仅记录发现，不区分个体 |
| 图像处理 | OpenCV |
| 数据库 | SQLite + SQLAlchemy |
| CLI | Click + Rich |

## 文档

- [设计文档 (design.md)](design.md) — 完整的需求分析与技术方案

## License

MIT
