# 动物识别与档案管理系统 — 需求文档与技术方案

> **版本**: v2.1
> **日期**: 2026-06-09
> **状态**: Draft (混合方案: YOLO 本地检测 + LLM API 分类 + 猫个体 Re-ID)

---

## 目录

1. [项目概述](#1-项目概述)
2. [需求分析](#2-需求分析)
3. [系统架构](#3-系统架构)
4. [技术选型](#4-技术选型)
5. [模块详细设计](#5-模块详细设计)
6. [数据库设计](#6-数据库设计)
7. [API 设计](#7-api-设计)
8. [错误处理与异常策略](#8-错误处理与异常策略)
9. [测试策略](#9-测试策略)
10. [部署方案](#10-部署方案)
11. [项目计划与里程碑](#11-项目计划与里程碑)
12. [附录](#12-附录)

---

## 1. 项目概述

### 1.1 项目背景

构建一套自动化动物识别与档案管理系统，能够从用户提供的图片和视频中识别常见动物（猫、黄鼠狼、鸟），并为每一只识别到的动物建立独立档案，记录其出现的媒体文件信息。

### 1.2 项目目标

- 支持常见图片和视频格式的输入
- 自动识别图片/视频中的动物类别（猫、黄鼠狼、鸟）
- **对猫进行个体区分**并建立独立档案（每只猫一个档案）
- 黄鼠狼和鸟仅记录发现记录，不做个体区分
- 记录每个动物个体的来源信息（文件名、路径、视频时间段）
- 提供稳健的错误处理机制

### 1.3 适用范围

| 维度 | 说明 |
|------|------|
| 目标动物 | 猫 (Cat)、黄鼠狼 (Weasel)、鸟 (Bird) |
| 图片格式 | JPEG, PNG, BMP, TIFF, WebP, GIF |
| 视频格式 | MP4, AVI, MOV, MKV, WMV, FLV |
| 运行环境 | Linux (主要) / Windows / macOS |
| 用户类型 | 单机用户 / 小规模本地部署 |

### 1.4 技术路线

本项目采用**混合方案（Hybrid Approach）**：

```
本地 YOLO 检测         多模态 LLM API 分类        猫个体 Re-ID 匹配
(快速定位动物位置)  +  (精确判定动物类别)      +  (仅猫区分个体，鸟/黄鼠狼不区分)
     ↓                      ↓                        ↓
  免费/快速             按量付费/高精度            免费/高频调用
```

| 阶段 | 用什么 | 为什么 |
|------|--------|--------|
| **检测** — 动物在哪里？ | 本地 YOLOv8 | 速度快（<50ms）、免费、适合批量帧处理 |
| **分类** — 是什么动物？ | DeepSeek / Claude API | 零训练成本、精度高、天然处理罕见动物（黄鼠狼） |
| **个体匹配** — 是哪一只猫？ | 本地 ResNet50 特征提取 | **仅对猫启用**。频繁比对本地更快更经济 |

**核心思路**：YOLO 做粗筛（过滤掉无动物的帧，减少 API 调用量），只把**有动物的裁剪区域**送给 LLM API 做精确分类，分类结果中**只有猫**进入个体匹配流程，黄鼠狼和鸟仅记录发现日志。视频中大部分帧可能没有动物，这个"先检测再分类"的策略可减少 70-90% 的 API 调用。

---

## 2. 需求分析

### 2.1 功能需求

#### FR-1: 媒体文件输入

| 编号 | 描述 | 优先级 |
|------|------|--------|
| FR-1.1 | 支持通过文件路径（单文件或目录）导入图片 | P0 |
| FR-1.2 | 支持通过文件路径（单文件或目录）导入视频 | P0 |
| FR-1.3 | 支持通过命令行参数指定输入 | P0 |
| FR-1.4 | 支持通过配置文件定义输入源 | P1 |
| FR-1.5 | 递归扫描子目录中的媒体文件 | P1 |

#### FR-2: 动物识别

| 编号 | 描述 | 优先级 |
|------|------|--------|
| FR-2.1 | 使用本地 YOLO 检测图片/视频帧中的动物位置（bounding box） | P0 |
| FR-2.2 | 使用多模态 LLM API 对检测到的动物区域做精确分类（猫/黄鼠狼/鸟） | P0 |
| FR-2.3 | 识别视频中逐帧的动物类别 | P0 |
| FR-2.4 | 对猫进行个体区分（Re-ID），黄鼠狼和鸟不做个体区分 | P0 |
| FR-2.5 | 输出每个识别结果的置信度分数 | P1 |
| FR-2.6 | API 不可用时自动降级为本地规则判断 | P0 |
| FR-2.7 | API 调用失败时自动重试（指数退避，最多 3 次） | P0 |
| FR-2.8 | 支持识别结果的人工校正接口 | P2 |

#### FR-3: 档案管理

| 编号 | 描述 | 优先级 |
|------|------|--------|
| FR-3.1 | 为每一只识别到的动物创建独立档案 | P0 |
| FR-3.2 | 档案包含动物缩略图、类别标签、唯一ID | P0 |
| FR-3.3 | 记录图片来源：文件名、存储路径 | P0 |
| FR-3.4 | 记录视频来源：文件名、存储路径、出现时间段（开始/结束时间戳） | P0 |
| FR-3.5 | 支持按动物类别筛选和查看档案 | P1 |
| FR-3.6 | 支持导出档案数据（JSON/CSV） | P2 |

#### FR-4: 错误处理

| 编号 | 描述 | 优先级 |
|------|------|--------|
| FR-4.1 | 检测并跳过损坏的媒体文件 | P0 |
| FR-4.2 | 检测并跳过不支持的媒体格式 | P0 |
| FR-4.3 | 处理视频解码失败的情况 | P0 |
| FR-4.4 | 输出详细的错误日志 | P0 |
| FR-4.5 | 生成处理摘要报告（成功/失败统计） | P1 |

### 2.2 非功能需求

| 编号 | 描述 | 指标 |
|------|------|------|
| NFR-1 | 图片识别速度 | 单张 < 2s (GPU) / < 5s (CPU)，含 API 调用 |
| NFR-2 | 视频处理速度 | 不低于实时播放速度的 0.5x |
| NFR-3 | 动物分类准确率 | ≥ 95% (LLM API 基准) |
| NFR-4 | 猫个体区分准确率 | ≥ 80% (不同猫之间) |
| NFR-5 | 支持的最大图片尺寸 | 4096×4096 px |
| NFR-6 | 支持的最大视频分辨率 | 4K (3840×2160) |
| NFR-7 | 数据持久化 | SQLite 本地数据库 |
| NFR-8 | 可扩展性 | 支持后续添加新动物类别（仅需改 prompt） |
| NFR-9 | API 调用成功率 | ≥ 99% (含重试) |
| NFR-10 | 离线降级可用性 | 核心检测+个体匹配功能离线可用 |

---

## 3. 系统架构

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI Interface                           │
│                   (Click / Rich)                             │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    Pipeline Orchestrator                     │
│              (任务调度 / 流水线编排 / 降级策略)                  │
└──┬──────────┬──────────┬──────────┬──────────┬──────────────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
┌──────┐ ┌──────┐  ┌──────┐  ┌──────┐  ┌──────────┐
│Input │ │Detect│  │ API  │  │Re-ID │  │ Archive  │
│Module│ │Module│  │Class-│  │Module│  │ Module   │
│      │ │(YOLO)│  │ifier │  │(Local)│  │          │
└──┬───┘ └──┬───┘  └──┬───┘  └──┬───┘  └────┬─────┘
   │        │         │         │           │
   │        │    ┌────▼────┐    │           │
   │        │    │DeepSeek │    │      ┌────▼─────┐
   │        │    │/ Claude │    │      │  Storage │
   │        │    │  API    │    │      │ (SQLite) │
   │        │    └─────────┘    │      └──────────┘
   │        │         │         │
   │        └────┬────┘         │
   │             ▼              │
   │      ┌──────────────┐      │
   │      │ Fallback      │     │
   │      │ (YOLO class   │     │
   │      │  + heuristics)│     │
   │      └──────────────┘      │
   │                            │
   └──────────┬─────────────────┘
              ▼
       ┌──────────────┐
       │  Local Model │
       │  (YOLO +     │
       │   ResNet50)  │
       └──────────────┘
```

### 3.2 数据流

```
                 ═══════════════ 图片处理管线 ═══════════════

图片输入 ──► 格式验证 ──► YOLO 动物检测 ──► 有动物？ ──No──► 跳过，记录
                                                  │
                                                 Yes
                                                  │
                                                  ▼
                                    裁剪动物区域 (crop)
                                                  │
                                                  ▼
                                    ┌─ LLM API 分类 ──────────┐
                                    │ DeepSeek / Claude       │
                                    │ Prompt: "这是什么动物？   │
                                    │  选项: 猫/黄鼠狼/鸟/其他  │
                                    │  返回: {class, conf,     │
                                    │         color, features}"│
                                    └──────────┬──────────────┘
                                                  │
                                    ┌─────────────▼──────────────┐
                                    │ 猫？                         │
                                    │ Yes → 特征提取 + 个体匹配    │
                                    │        → 猫档案 (新建/更新)  │
                                    │ No  → 鸟/黄鼠狼 → 仅记录    │
                                    └─────────────────────────────┘


                 ═══════════════ 视频处理管线 ═══════════════

视频输入 ──► 格式验证 ──► 关键帧提取 ──► YOLO 逐帧检测 ──► 有动物？
                                                              │
                                              ┌─────── No ────┴──── Yes ────┐
                                              ▼                                  ▼
                                         跳过该帧                         裁剪动物区域
                                                                              │
                                                                              ▼
                                                                     LLM API 分类
                                                                              │
                                                                      ┌───────▼────────┐
                                                                      │ 猫？             │
                                                                      │ Yes → 个体匹配   │
                                                                      │ No  → 仅记录    │
                                                                      └─────────────────┘
                                                                              │
                                                                     时间段合并算法
                                                                              │
                                                                     猫档案更新 + 时间戳记录
                                                                     鸟/黄鼠狼发现记录
```

### 3.3 目录结构

```
animal-id-system/
├── design.md                    # 本设计文档
├── README.md
├── requirements.txt             # Python 依赖
├── config.yaml                  # 默认配置文件
├── src/
│   ├── __init__.py
│   ├── main.py                  # 入口
│   ├── cli.py                   # CLI 接口
│   ├── pipeline.py              # 流水线编排器
│   ├── input_module/
│   │   ├── __init__.py
│   │   ├── scanner.py           # 文件扫描器
│   │   ├── validator.py         # 格式验证器
│   │   ├── image_reader.py      # 图片读取器
│   │   └── video_reader.py      # 视频读取器
│   ├── recognition/
│   │   ├── __init__.py
│   │   ├── detector.py          # 动物检测器 (本地 YOLO)
│   │   ├── api_classifier.py    # API 分类器 (DeepSeek/Claude API)
│   │   ├── fallback.py          # 离线降级分类器 (YOLO class + 启发式规则)
│   │   ├── feature_extractor.py # 特征提取器 (本地 Re-ID)
│   │   └── matcher.py           # 个体匹配器
│   ├── archive/
│   │   ├── __init__.py
│   │   ├── profile_manager.py   # 档案管理器
│   │   ├── thumbnail.py         # 缩略图生成器
│   │   └── exporter.py          # 档案导出器
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py          # 数据库操作
│   │   └── models.py            # ORM 模型
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py            # 日志工具
│   │   ├── config.py            # 配置加载
│   │   └── exceptions.py        # 自定义异常
│   └── models/                  # 模型权重存放目录（.gitignore）
│       └── .gitkeep
├── data/                        # 运行时数据目录
│   ├── profiles/                # 动物档案缩略图
│   └── database/                # SQLite 数据库文件
├── logs/                        # 日志输出
├── tests/
│   ├── __init__.py
│   ├── test_input_module/
│   ├── test_recognition/
│   ├── test_archive/
│   └── test_storage/
└── scripts/
    ├── download_models.sh       # 模型下载脚本
    └── setup_env.sh             # 环境初始化脚本
```

---

## 4. 技术选型

### 4.1 技术栈总览

| 层级 | 技术 | 版本 | 选型理由 |
|------|------|------|----------|
| 语言 | Python | 3.10+ | 生态成熟，CV/NN 库丰富 |
| 深度学习框架 | PyTorch + ultralytics | 2.x | YOLO 推理 + Re-ID 特征提取 |
| 目标检测 (本地) | YOLOv8s | latest | 速度快、精度高、COCO 预训练含猫/鸟 |
| 动物分类 (云端) | DeepSeek / Claude API | — | 零训练、高精度、天然理解黄鼠狼等罕见动物 |
| 离线降级 | YOLO COCO class + 启发式规则 | — | API 不可用时的 fallback |
| 特征提取 (本地) | ResNet50 + ArcFace | — | 个体重识别，高频调用走本地 |
| 图像处理 | OpenCV (cv2) | 4.8+ | 全能图像/视频处理库 |
| 视频处理 | FFmpeg + OpenCV | — | 视频解码、帧提取 |
| HTTP 客户端 | httpx | 0.25+ | 异步支持、连接池、超时控制 |
| 数据库 | SQLite + SQLAlchemy | — | 轻量、零配置、便携 |
| CLI 框架 | Click + Rich | 8.x | 简洁、类型安全、终端美观 |
| 配置管理 | PyYAML / OmegaConf | — | YAML 配置文件解析 |
| 日志 | Python logging + Rich | — | 结构化日志 + 终端美观输出 |
| 测试 | pytest + respx | 7.x+ | 单元测试 + HTTP mock |

### 4.2 三层识别架构

```
┌──────────────────────────────────────────────────────────────────┐
│                      识别流水线                                    │
│                                                                  │
│  Layer 1: 检测 (本地)          Layer 2: 分类 (云端)               │
│  ┌──────────────────┐        ┌──────────────────┐               │
│  │     YOLOv8s      │        │  DeepSeek/Claude │               │
│  │                  │        │      API         │               │
│  │ "图里有动物吗？    │──────►│ "这是什么动物？"   │               │
│  │  在哪里？"        │  crop  │                  │               │
│  │                  │        │ 猫/黄鼠狼/鸟/其他  │               │
│  │ 速度: <50ms      │        │ 延迟: 1-3s       │               │
│  │ 成本: 免费        │        │ 成本: ~0.01元/次  │               │
│  └──────────────────┘        └────────┬─────────┘               │
│                                       │                          │
│                                       ▼                          │
│                          Layer 3: 个体匹配 (本地)                  │
│                          ┌──────────────────┐                    │
│                          │  ResNet50 +      │                    │
│                          │  Cosine Match    │                    │
│                          │                  │                    │
│                          │ "这是哪一只？"     │                    │
│                          │ 速度: <30ms      │                    │
│                          │ 成本: 免费        │                    │
│                          └──────────────────┘                    │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2.1 Layer 1: 动物检测 — YOLOv8s (本地)

```
用途: 快速定位图片/视频帧中的动物区域
输入: RGB 图像 (640×640 缩放)
输出: [x1, y1, x2, y2, confidence, class_id]
预训练: COCO 数据集
目标类别:
  - class_id=15: cat (猫)
  - class_id=14: bird (鸟)
  - class_id=*: animal (通用动物类，用于捕获黄鼠狼等)
裁剪: 检测到的区域放大 10% padding 后裁剪，传给 Layer 2
```

**为什么选 YOLOv8s（而非 nano）：**
- 在速度和精度之间取得更好平衡
- COCO 预训练权重已能识别猫和鸟
- 仅需检测"是否动物"的粗粒度任务，不需要精细分类
- 原生支持 ONNX/TensorRT 导出加速推理
- 核心价值：**过滤无动物帧，减少 70-90% 的 API 调用**

**YOLO 检测结果处理：**

```python
# YOLO 只负责"找到动物"，不负责"判断是什么动物"
# COCO 类别中与动物相关的 class_id 全部视为候选
ANIMAL_CLASS_IDS = {
    14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25,
    # bird, cat, dog, horse, sheep, cow, elephant, bear, zebra, giraffe, (other animals)
}
```

### 4.2.2 Layer 2: 动物分类 — 多模态 LLM API (云端)

```
用途: 对 YOLO 裁剪的动物区域做精确分类
输入: Base64 编码的动物裁剪区域 + 分类 Prompt
输出: 结构化 JSON {class, confidence, color, distinguishing_features}
Provider: DeepSeek (推荐) / Claude / OpenAI
```

**Prompt 设计：**

```python
CLASSIFICATION_PROMPT = """
你是一个野生动物识别专家。请仔细观察这张动物图片的裁剪区域，判断它属于以下哪一类：
- cat (猫，包括家猫、野猫、各种毛色的猫)
- weasel (黄鼠狼，包括黄鼬、白鼬、雪貂等鼬科动物)
- bird (鸟，包括各种常见的鸟类)
- other (其他动物，不属于以上三类)

请以 JSON 格式返回，包含以下字段：
{
  "class": "cat|weasel|bird|other",
  "confidence": 0.0-1.0,
  "color": "描述该动物的主要颜色/花纹",
  "distinguishing_features": "该动物的显著外形特征，用于个体区分"
}

注意：
- 如果图片模糊、遮挡严重或角度不好，请在 confidence 中体现
- distinguishing_features 请描述毛色花纹、体型、耳朵形状、尾巴特征等可用于区分同类的特征
"""
```

**API 响应示例：**

```json
{
  "class": "cat",
  "confidence": 0.95,
  "color": "橘色虎斑，白色胸口和爪子",
  "distinguishing_features": "中等体型，耳朵尖端有小缺口，尾巴末端有深色环纹，左眼上方有一小块白色斑点"
}
```

**为什么用 DeepSeek：**
- 性价比高（约 ¥1/百万 token），单次分类约 ¥0.005-0.01
- 支持图片输入，视觉理解能力强
- 中文生态友好
- 备选：Claude API（更高精度，略贵）

**API 调用优化策略：**

| 策略 | 说明 | 节省比例 |
|------|------|----------|
| YOLO 预筛选 | 无动物的帧不调 API | 70-90% |
| 帧去重 | 视频相邻帧相似度 > 0.95 不重复调用 | 30-50% |
| 结果缓存 | 同一图片 SHA-256 缓存，避免重复调用 | 视重复率 |
| 小图压缩 | crop 区域压缩至 512px 以内再编码 | 减少 token 消耗 |

### 4.2.3 Layer 2 Fallback: 离线降级分类器

当 API 不可用时（网络故障、额度用尽、超时），自动降级：

```python
class FallbackClassifier:
    """
    离线降级策略 (按优先级):
    1. YOLO COCO class_id 直接映射: 15→cat, 14→bird
    2. 启发式规则: 体型比例、颜色直方图分析
    3. 无法判断时标记为 'unknown'，提示用户手动标注
    """

    COCO_MAPPING = {
        15: 'cat',
        14: 'bird',
        # 黄鼠狼在 COCO 中没有直接对应，降级时无法自动识别
    }

    def classify(self, crop: np.ndarray, yolo_class_id: int) -> FallbackResult:
        """降级模式下置信度较低，但保证系统不中断"""
```

### 4.2.4 Layer 3: 猫个体重识别 — ResNet50 (本地)

```
用途: 仅对猫进行个体区分，黄鼠狼和鸟跳过此步骤
输入: 猫的裁剪区域图像 (256×128)
输出: 512 维特征向量 (L2 归一化)
匹配方式: 余弦相似度 > 阈值 0.75 判定为同一只猫
训练: Market-1501 预训练 → 猫数据集微调
适用范围: 仅 class='cat' 的检测结果
```

**个体区分策略（仅猫）：**

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ 检测 + 分类   │ ──► │  是猫吗？     │ ──► │  特征匹配     │
│ (animal #N)  │     │ Yes → 特征提取 │     │  cosine sim  │
│              │     │ No  → 仅记录  │     └──────┬───────┘
└──────────────┘     └──────────────┘            │
                                    ┌─────────────▼─────────────┐
                                    │ sim ≥ 0.75 → 已有猫档案   │
                                    │ sim < 0.75 → 新建猫档案   │
                                    └───────────────────────────┘

黄鼠狼/鸟 → 仅记录发现 (class + time + source)，不进入个体匹配
```

**为什么个体匹配放在本地而非 API：**
- 每次新检测都要与所有已知猫的特征向量逐一比对
- 猫档案增长到 100 只时，单次检测需要 100 次比对
- 本地余弦相似度计算极快（<1ms），走 API 成本和时间都不现实

### 4.3 API 成本估算

以 DeepSeek 视觉模型为例（¥1/百万输入 token，¥4/百万输出 token）：

| 场景 | 估算量 | API 调用次数 | 月成本估计 |
|------|--------|-------------|-----------|
| 100 张图片处理 | 50 张有动物 | 50 次 | ¥0.25-0.50 |
| 10 分钟视频处理 | ~300 关键帧 / ~60 帧有动物 | 60 次 | ¥0.30-0.60 |
| 日常轻度使用 | 200 张图 + 5 个视频/月 | ~400 次 | ¥2-4 |
| 重度批量处理 | 5000 张图 + 100 个视频/月 | ~8000 次 | ¥40-80 |

> **结论**: 对于个人用户，月成本在 ¥10 以内；批量处理场景成本可控。

### 4.4 硬件需求

| 配置项 | 最低要求 | 推荐配置 |
|--------|----------|----------|
| CPU | 4 核 | 8 核+ |
| RAM | 8 GB | 16 GB+ |
| GPU | 无 (CPU 推理 YOLO) | NVIDIA GPU 6GB+ VRAM |
| 磁盘 | 2 GB (不含媒体文件) | SSD 10 GB+ |
| 网络 | 需要 (API 调用) | 稳定宽带 |

---

## 5. 模块详细设计

### 5.1 输入模块 (Input Module)

#### 5.1.1 文件扫描器 (`scanner.py`)

```
功能: 递归扫描指定路径，收集所有支持的媒体文件
输入: 路径列表 (文件或目录)
输出: 分类后的文件列表 {images: [...], videos: [...], skipped: [...]}
```

**Pseudo-code:**

```python
class MediaScanner:
    SUPPORTED_IMAGES = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.gif'}
    SUPPORTED_VIDEOS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv'}
    MAX_FILE_SIZE = 4 * 1024 * 1024 * 1024  # 4 GB

    def scan(self, paths: list[str]) -> ScanResult:
        """
        1. 遍历 paths
        2. 若是目录 → 递归扫描
        3. 若是文件 → 检查扩展名
        4. 分类至 images / videos / skipped
        5. 跳过超过大小限制的文件，记录 warning
        """
```

#### 5.1.2 格式验证器 (`validator.py`)

```
功能: 验证媒体文件是否有效可读
验证项:
  - 文件存在且可读
  - 文件大小 > 0
  - 图片: 可用 cv2.imread() 成功读取，且像素尺寸 > 0
  - 视频: 可用 cv2.VideoCapture 打开，且总帧数 > 0
  - 文件头魔数 (magic bytes) 校验
```

**图片魔数校验表：**

| 格式 | 魔数 (Hex) |
|------|------------|
| JPEG | FF D8 FF |
| PNG  | 89 50 4E 47 |
| BMP  | 42 4D |
| TIFF | 49 49 2A 00 / 4D 4D 00 2A |
| WebP | 52 49 46 46 ... 57 45 42 50 |
| GIF  | 47 49 46 38 |

**视频魔数校验表：**

| 格式 | 魔数 (Hex) |
|------|------------|
| MP4  | ... 66 74 79 70 (ftyp box) |
| AVI  | 52 49 46 46 ... 41 56 49 20 |
| MOV  | ... 66 74 79 70 71 74 (qt) |
| MKV  | 1A 45 DF A3 (EBML) |
| WMV  | 30 26 B2 75 (ASF) |
| FLV  | 46 4C 56 01 |

#### 5.1.3 视频帧提取 (`video_reader.py`)

```
功能: 从视频中按策略提取关键帧
策略:
  1. 等间隔采样: 每秒取 1 帧 (fps=1)
  2. 运动检测采样: 帧间差分 > 阈值时采样 (避免冗余)
  3. 场景切换检测: 使用直方图比较，变化 > 阈值时采样

默认使用策略 1 + 2 混合:
  - 基础: 每秒 1 帧
  - 增强: 运动区域变化时额外采样
```

```python
class VideoFrameExtractor:
    def __init__(self, sample_fps: float = 1.0,
                 motion_threshold: float = 0.15):
        self.sample_fps = sample_fps
        self.motion_threshold = motion_threshold

    def extract(self, video_path: str) -> Iterator[VideoFrame]:
        """
        生成器: 逐帧 yield VideoFrame(timestamp, frame_array)
        内部维护一个采样间隔计数器 + 运动检测器
        """
```

**帧信息数据结构：**

```python
@dataclass
class VideoFrame:
    timestamp: float       # 秒 (视频内时间)
    frame_index: int       # 帧序号
    image: np.ndarray      # BGR 图像数组
    is_keyframe: bool      # 是否为关键帧
```

### 5.2 识别模块 (Recognition Module)

#### 5.2.1 动物检测器 (`detector.py`) — Layer 1

```
职责: 快速定位动物位置，不负责具体分类
模型: YOLOv8s
推理尺寸: 640×640
置信度阈值: 0.25 (偏低，宁可多检不漏检)
NMS IoU 阈值: 0.45
动物类 ID: 14(bird), 15(cat), 16-25(其他动物全部纳入候选)
```

```python
class AnimalDetector:
    # COCO 中所有动物相关的 class_id
    ANIMAL_CLASS_IDS = set(range(14, 26))  # 14=bird, 15=cat, 16=dog, ...

    def __init__(self, model_path: str, confidence_threshold: float = 0.25):
        self.model = YOLO(model_path)
        self.conf_threshold = confidence_threshold

    def detect(self, image: np.ndarray) -> list[RawDetection]:
        """
        返回: [
          RawDetection(bbox=[x1,y1,x2,y2], yolo_class_id=15,
                       yolo_confidence=0.88, crop=image_region),
          ...
        ]
        注意: 此阶段不输出最终 class_name，交给 API 层判定
        """
```

**关键设计决策 — 宁多勿漏**：
- YOLO 置信度阈值设为较低的 0.25（默认 0.35），确保黄鼠狼等 YOLO 不擅长的动物不被漏掉
- 所有动物类 ID（14-25）全部纳入候选，不限于猫/鸟
- 假阳性代价低（多调一次 API），假阴性代价高（漏掉一只动物）

**检测结果数据结构：**

```python
@dataclass
class RawDetection:
    bbox: list[int]           # [x1, y1, x2, y2] 像素坐标
    yolo_class_id: int        # YOLO COCO class_id (仅供参考)
    yolo_confidence: float    # YOLO 检测置信度
    crop: np.ndarray          # 裁剪+padding 后的动物区域 (BGR)
    crop_base64: str          # Base64 编码 (JPEG 压缩, 512px)
    crop_hash: str            # SHA-256 (用于缓存去重)
    source_file: str          # 来源文件名
    source_type: str          # 'image' | 'video'
    timestamp: float | None   # 视频时间戳，图片为 None
```

#### 5.2.2 API 分类器 (`api_classifier.py`) — Layer 2

```
职责: 调用多模态 LLM API 对动物裁剪区域做精确分类
支持 Provider: DeepSeek (主), Claude (备)
超时: 10s
重试: 指数退避 (1s → 2s → 4s)，最多 3 次
```

```python
import httpx
import hashlib
from dataclasses import dataclass
from typing import Optional

@dataclass
class ClassificationResult:
    class_name: str           # 'cat' | 'weasel' | 'bird' | 'other'
    confidence: float         # 0.0 ~ 1.0
    color: str                # 颜色/花纹描述
    distinguishing_features: str  # 显著特征描述

class APIClassifier:
    CLASSIFICATION_PROMPT = """你是一个野生动物识别专家。请仔细观察这张动物图片，判断它属于以下哪一类：
- cat (猫，包括家猫、野猫、各种毛色的猫)
- weasel (黄鼠狼，包括黄鼬、白鼬、雪貂等鼬科动物)
- bird (鸟，包括各种常见的鸟类)
- other (其他动物，不属于以上三类)

请以 JSON 格式返回，只返回 JSON 不要其他内容：
{"class": "...", "confidence": 0.0-1.0, "color": "...", "distinguishing_features": "..."}"""

    def __init__(self, provider: str = "deepseek",
                 api_key: str = "",
                 timeout: float = 10.0,
                 max_retries: int = 3):
        self.provider = provider
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.cache: dict[str, ClassificationResult] = {}  # crop_hash → result

    async def classify(self, detection: RawDetection) -> ClassificationResult:
        """
        1. 检查缓存 (crop_hash)
        2. 构建 API 请求 (Base64 图片 + Prompt)
        3. 发送请求，超时 10s
        4. 解析 JSON 响应
        5. 验证 class_name 在允许列表中
        6. 异常时重试 (指数退避)
        7. 重试耗尽后抛出 APIClassificationError
        """
        # 缓存命中
        if detection.crop_hash in self.cache:
            return self.cache[detection.crop_hash]

        for attempt in range(self.max_retries):
            try:
                result = await self._call_api(detection.crop_base64)
                self.cache[detection.crop_hash] = result
                return result
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise APIClassificationError(
                        f"API classification failed after {self.max_retries} retries: {e}"
                    )
                await asyncio.sleep(2 ** attempt)  # 指数退避

    async def _call_api(self, image_base64: str) -> ClassificationResult:
        """根据 provider 调用对应的 API endpoint"""
        if self.provider == "deepseek":
            return await self._call_deepseek(image_base64)
        elif self.provider == "claude":
            return await self._call_claude(image_base64)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    async def _call_deepseek(self, image_base64: str) -> ClassificationResult:
        """调用 DeepSeek API (OpenAI 兼容格式)"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": "deepseek-chat",  # 支持视觉的模型
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "image_url",
                             "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                            {"type": "text", "text": self.CLASSIFICATION_PROMPT}
                        ]
                    }],
                    "temperature": 0.1,  # 低温度确保稳定输出
                    "max_tokens": 200
                }
            )
            raw = response.json()["choices"][0]["message"]["content"]
            return self._parse_response(raw)

    async def _call_claude(self, image_base64: str) -> ClassificationResult:
        """调用 Claude API"""
        # ... 类似实现，使用 Anthropic SDK 或 HTTP
        pass

    def _parse_response(self, raw_text: str) -> ClassificationResult:
        """解析 LLM 返回的 JSON，带容错处理"""
        # 提取 JSON (处理 markdown code block 包裹的情况)
        import re, json
        match = re.search(r'\{[^}]+\}', raw_text)
        if not match:
            raise ClassificationParseError(f"Cannot parse JSON from: {raw_text[:100]}")
        data = json.loads(match.group())
        # 验证
        if data["class"] not in ("cat", "weasel", "bird", "other"):
            raise ClassificationParseError(f"Unknown class: {data['class']}")
        return ClassificationResult(
            class_name=data["class"],
            confidence=float(data["confidence"]),
            color=data.get("color", ""),
            distinguishing_features=data.get("distinguishing_features", "")
        )
```

#### 5.2.3 离线降级分类器 (`fallback.py`) — Layer 2 Fallback

```python
class FallbackClassifier:
    """API 不可用时的本地降级方案"""

    def classify(self, detection: RawDetection) -> ClassificationResult:
        """
        降级策略:
        1. YOLO class_id 直接映射:
           - 15 (cat) → 'cat', confidence=0.6
           - 14 (bird) → 'bird', confidence=0.6
        2. 其他 class_id → 'other', confidence=0.3
        3. 无法判定 → 'unknown', confidence=0.0

        注意: 降级模式下黄鼠狼无法被识别 (COCO 不含该类)
              结果会标记为 'other' 或 'unknown'
        """
        mapping = {15: 'cat', 14: 'bird'}
        class_name = mapping.get(detection.yolo_class_id, 'other')
        confidence = 0.6 if detection.yolo_class_id in mapping else 0.3

        return ClassificationResult(
            class_name=class_name,
            confidence=confidence,
            color="",
            distinguishing_features="(offline fallback - manual review recommended)"
        )
```

#### 5.2.4 特征提取器 (`feature_extractor.py`) — Layer 3

用于个体重识别的特征提取，运行在本地：

```python
class FeatureExtractor:
    EMBEDDING_DIM = 512
    INPUT_SIZE = (256, 128)  # H×W

    def __init__(self, model_path: str):
        backbone = ResNet50(pretrained=True)
        self.backbone = nn.Sequential(*list(backbone.children())[:-1])
        self.embedding = nn.Linear(2048, 512)
        self.model = nn.Sequential(self.backbone, nn.Flatten(), self.embedding)

    def extract(self, crop: np.ndarray) -> np.ndarray:
        """返回 512 维 L2 归一化特征向量"""
        tensor = self.transform(crop).unsqueeze(0)
        with torch.no_grad():
            vec = self.model(tensor)
        return F.normalize(vec, p=2, dim=1).numpy().flatten()
```

#### 5.2.5 个体匹配器 (`matcher.py`) — Layer 3 (仅猫)

```python
class IndividualMatcher:
    """仅对猫进行个体匹配"""
    SIMILARITY_THRESHOLD = 0.75
    SECONDARY_THRESHOLD = 0.65

    def __init__(self, feature_db: FeatureDatabase):
        self.feature_db = feature_db

    def match(self, feature: np.ndarray, classification: ClassificationResult) -> MatchResult:
        """
        前置条件: classification.class_name == 'cat'
        黄鼠狼和鸟不会进入此方法

        两层匹配:
        1. 特征向量余弦相似度 (主)
        2. API 返回的 distinguishing_features 文本相似度 (辅)
        """
        if classification.class_name != 'cat':
            return MatchResult(None, False, 0.0, None)  # 不匹配，仅记录

        candidates = self.feature_db.get_by_class('cat')
        if not candidates:
            return MatchResult(None, True, 0.0, None)  # 第一只猫，创建档案

        max_sim = 0.0
        best_match = None
        for ind_id, stored_feat in candidates.items():
            sim = cosine_similarity(feature, stored_feat)
            if sim > max_sim:
                max_sim = sim
                best_match = ind_id

        if max_sim >= self.SIMILARITY_THRESHOLD:
            return MatchResult(best_match, False, max_sim,
                               self.feature_db.get_profile(best_match))
        elif max_sim >= self.SECONDARY_THRESHOLD:
            if self._text_features_match(classification, best_match):
                return MatchResult(best_match, False, max_sim,
                                   self.feature_db.get_profile(best_match))

        return MatchResult(None, True, max_sim, None)  # 新猫
```

### 5.3 视频时间段合并算法

视频中连续帧可能检测到同一动物，需要将离散检测合并为时间段：

```python
def merge_time_segments(detections: list[Detection],
                        max_gap: float = 3.0) -> list[TimeSegment]:
    """
    输入: 按时间戳排序的检测结果列表
    输出: 合并后的时间段列表

    算法:
    1. 按时间戳排序
    2. 相邻检测间隔 ≤ max_gap (3秒) → 合并为同一段
    3. 间隔 > max_gap → 切分为新段
    4. 每段保留: start_time, end_time, best_frame (置信度最高)
    5. 过滤掉短于 0.5 秒的段 (可能是误检)
    """
```

**时间段数据结构：**

```python
@dataclass
class TimeSegment:
    start_time: float       # 秒
    end_time: float         # 秒
    best_frame: np.ndarray  # 最佳帧 (用于档案缩略图)
    confidence_avg: float   # 段内平均置信度
    frame_count: int        # 段内检测帧数
```

### 5.4 档案模块 (Archive Module)

#### 5.4.1 档案管理器 (`profile_manager.py`)

```python
class ProfileManager:
    def __init__(self, db: Database, storage_path: str):
        self.db = db
        self.storage_path = storage_path

    def create_profile(self, detection: Detection,
                       feature: np.ndarray,
                       time_segment: TimeSegment | None) -> AnimalProfile:
        """
        新建动物个体档案:
        1. 生成唯一 ID: {class_name}_{uuid_short} (如 cat_a3f2b1c0)
        2. 保存最佳帧缩略图至 storage_path/profiles/{id}.jpg
        3. 写入数据库记录
        4. 存储特征向量
        5. 返回 AnimalProfile
        """

    def update_profile(self, profile_id: str, detection: Detection,
                       time_segment: TimeSegment | None) -> None:
        """
        更新已有动物档案:
        1. 添加新的媒体来源记录 (source record)
        2. 如果新帧质量更好 → 更新缩略图
        3. 更新特征向量 (移动平均)
        4. 更新 last_seen 时间戳
        """

    def get_profile(self, profile_id: str) -> AnimalProfile | None:
        """按 ID 获取档案"""

    def list_profiles(self, class_name: str | None = None,
                      limit: int = 100, offset: int = 0) -> list[AnimalProfile]:
        """按类别筛选档案列表"""

    def delete_profile(self, profile_id: str) -> bool:
        """删除档案及其关联数据"""
```

**档案数据结构：**

```python
@dataclass
class AnimalProfile:
    id: str                    # 唯一标识
    class_name: str            # 'cat' | 'weasel' | 'bird'
    nickname: str | None       # 可选昵称 (用户自定义)
    description: str | None    # API 返回的颜色/特征描述 (辅助个体匹配)
    thumbnail_path: str        # 缩略图路径
    feature_vector: bytes      # 序列化的特征向量 (用于后续匹配)
    first_seen: datetime       # 首次发现时间
    last_seen: datetime        # 最近发现时间
    appearance_count: int      # 累计出现次数
    sources: list[MediaSource] # 来源列表

@dataclass
class MediaSource:
    source_type: str           # 'image' | 'video'
    file_name: str             # 文件名
    file_path: str             # 文件完整路径
    file_size: int             # 文件大小 (bytes)
    time_segments: list[TimeSegment] | None  # 视频的时间段，图片为 None
    added_at: datetime         # 添加时间
```

### 5.5 流水线编排器 (`pipeline.py`)

```python
class Pipeline:
    """
    混合架构流水线 — 协调本地模型 + 云端 API

    ═══════════════ 图片处理 ═══════════════

    图片路径
       │
       ▼
    ┌──────────────────┐
    │  Validate & Read  │
    └────────┬─────────┘
             ▼
    ┌──────────────────┐
    │  YOLO 动物检测    │ ◄── Layer 1 (本地)
    └────────┬─────────┘
             ▼
       有动物吗？── No ──► 跳过
             │
            Yes
             ▼
    ┌──────────────────┐
    │  去重检查 (hash)   │  检查 SHA-256 是否已处理过
    └────────┬─────────┘
             ▼
    ┌──────────────────┐
    │  API 分类 (主)    │ ◄── Layer 2 (云端: DeepSeek/Claude)
    │  │ 失败？          │
    │  ▼                │
    │  Fallback (备)    │ ◄── Layer 2 Fallback (本地: YOLO class 映射)
    └────────┬─────────┘
             ▼
    ┌──────────────────┐
    │ 特征提取 + 个体匹配 │ ◄── Layer 3 (本地: ResNet50 + Cosine)
    └────────┬─────────┘
             ▼
    ┌──────────────────┐
    │  档案创建/更新     │ ◄── ProfileManager
    └──────────────────┘


    ═══════════════ 视频处理 ═══════════════

    视频路径
       │
       ▼
    ┌──────────────────┐
    │  Validate & Open  │
    └────────┬─────────┘
             ▼
    ┌──────────────────┐
    │  关键帧提取       │  等间隔 1fps + 运动检测
    └────────┬─────────┘
             ▼
    ┌──────────────────┐
    │  逐帧 YOLO 检测   │  过滤无动物帧 (节省 70-90% API 调用)
    └────────┬─────────┘
             ▼
    ┌──────────────────┐
    │  帧间去重         │  相似度 > 0.95 的相邻帧复用结果
    └────────┬─────────┘
             ▼
    ┌──────────────────┐
    │  时间段合并       │  ≤3s 间隔合并为同一段
    └────────┬─────────┘
             ▼
    ┌──────────────────┐
    │  API 批量分类     │  每段取最佳帧 + 首帧 + 尾帧调用 API
    └────────┬─────────┘
             ▼
       (接特征提取 + 匹配 + 建档，同上)
    """

    def __init__(self, config: Config):
        self.detector = AnimalDetector(config.models.detector)
        self.api_classifier = APIClassifier(config.api)
        self.fallback = FallbackClassifier()
        self.extractor = FeatureExtractor(config.models.feature_extractor)
        self.matcher = IndividualMatcher(self.db)
        self.profile_manager = ProfileManager(self.db, config.storage)

    async def process_image(self, path: str) -> ProcessResult:
        """处理单张图片"""
        # 1. 读取 + 验证
        image = self.read_image(path)
        # 2. YOLO 检测 (Layer 1)
        detections = self.detector.detect(image)
        if not detections:
            return ProcessResult.no_animal(path)
        # 3. 去重
        unique_dets = self.deduplicate(detections)
        # 4. API 分类 (Layer 2) — 异步并发
        results = []
        for det in unique_dets:
            try:
                classification = await self.api_classifier.classify(det)
            except APIClassificationError:
                classification = self.fallback.classify(det)  # 降级
            if classification.class_name == 'other':
                continue  # 非目标动物，跳过
            # 5. 特征提取 + 匹配 (Layer 3) — 仅猫
            if classification.class_name == 'cat':
                feature = self.extractor.extract(det.crop)
                match = self.matcher.match(feature, classification)
                if match.is_new:
                    profile = self.profile_manager.create_profile(
                        det, classification, feature)
                else:
                    profile = self.profile_manager.update_profile(
                        match.profile_id, det, classification)
                results.append(profile)
            else:
                # 黄鼠狼/鸟: 仅记录发现，不进入档案系统
                self.profile_manager.record_sighting(det, classification)
        return ProcessResult.success(path, results)

    async def process_video(self, path: str) -> ProcessResult:
        """处理单个视频"""
        # 1. 帧提取
        frames = self.video_reader.extract(path)
        # 2. 逐帧 YOLO 检测 + 帧间去重
        all_detections = []
        prev_frame_hash = None
        for frame in frames:
            # 帧间去重：相邻帧相似度过高则跳过
            frame_hash = self.compute_frame_hash(frame)
            if self.frame_similar(frame_hash, prev_frame_hash) > 0.95:
                prev_frame_hash = frame_hash
                continue
            prev_frame_hash = frame_hash
            dets = self.detector.detect(frame.image)
            for d in dets:
                d.timestamp = frame.timestamp
                all_detections.append(d)
        # 3. 时间段合并
        segments = merge_time_segments(all_detections)
        # 4. 每段选取代表帧 (最佳帧 + 首帧 + 尾帧) 调 API
        representative_dets = []
        for seg in segments:
            representative_dets.append(seg.best_detection)
            if seg.frame_count > 5:
                representative_dets.append(seg.first_detection)
                representative_dets.append(seg.last_detection)
        # 5. API 批量分类 (并发)
        classifications = await asyncio.gather(
            *[self.api_classifier.classify(d) for d in representative_dets],
            return_exceptions=True
        )
        # 6-7. 特征提取 + 匹配 + 建档 (同图片流程)
        # ...

    async def run(self, inputs: list[str]) -> PipelineReport:
        """
        返回: PipelineReport
          - total_files, processed, skipped, errors
          - api_calls: API 调用统计
          - api_cost_estimate: 费用估算
          - new_profiles, updated_profiles
          - elapsed_time
        """
```

### 5.6 API 调用优化与缓存

#### 5.6.1 帧间去重策略

```python
def should_call_api(detection: RawDetection,
                    prev_hash: str | None,
                    similarity_threshold: float = 0.95) -> bool:
    """
    决定是否需要对当前检测调用 API:

    图片场景:
      - 基于 crop_hash (SHA-256), 完全相同 → 缓存命中，不调用

    视频场景:
      - 连续两帧 crop 感知哈希 (pHash) 相似度 > 0.95 → 复用前一帧结果
      - 跳过 30-50% 的冗余 API 调用
    """
    if detection.crop_hash == prev_hash:
        return False
    if prev_hash and image_similarity(detection.crop_hash, prev_hash) > similarity_threshold:
        return False
    return True
```

#### 5.6.2 结果缓存层

```python
class ClassificationCache:
    """
    两级缓存:
      L1: 内存 dict (crop_hash → ClassificationResult) — 本次运行有效
      L2: SQLite 表 (file_hash → result JSON) — 跨运行持久化
    """

    def get(self, crop_hash: str) -> ClassificationResult | None:
        if crop_hash in self.memory_cache:
            return self.memory_cache[crop_hash]
        row = self.db.execute(
            "SELECT result_json FROM classification_cache WHERE crop_hash = ?",
            (crop_hash,)
        ).fetchone()
        if row:
            result = ClassificationResult.from_json(row[0])
            self.memory_cache[crop_hash] = result
            return result
        return None

    def set(self, crop_hash: str, result: ClassificationResult):
        self.memory_cache[crop_hash] = result
        self.db.execute(
            "INSERT OR REPLACE INTO classification_cache VALUES (?, ?, ?)",
            (crop_hash, result.to_json(), datetime.now())
        )
```

#### 5.6.3 API 调用统计

```python
@dataclass
class APIUsageStats:
    total_calls: int           # 总调用次数
    cache_hits: int            # 缓存命中次数
    fallback_used: int         # 降级使用次数
    total_tokens_input: int    # 总输入 token
    total_tokens_output: int   # 总输出 token
    estimated_cost_cny: float  # 估算费用 (人民币)
```

---

## 6. 数据库设计

### 6.1 ER 图

```
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────────┐
│  animal_profiles │       │  media_sources   │       │ classification_cache │
├──────────────────┤       ├──────────────────┤       ├──────────────────────┤
│ PK id (TEXT)     │──┐    │ PK id (INTEGER)  │       │ PK crop_hash (TEXT)  │
│    class (TEXT)   │  │    │    profile_id    │──┐    │    result_json (TEXT)│
│    nickname (TEXT)│  │    │    source_type   │  │    │    created_at        │
│    description    │  │    │    file_name     │  │    └──────────────────────┘
│    thumbnail_path │  │    │    file_path     │  │
│    feature_vector │  │    │    file_size     │  │
│    first_seen     │  │    │    file_hash     │  │
│    last_seen      │  │    │    added_at      │  │
│    appear_count   │  │    └────────┬─────────┘  │
└──────────────────┘  │             │             │
                       │    ┌────────▼─────────┐   │
                       │    │  time_segments   │   │
                       │    ├──────────────────┤   │
                       └────│ FK media_id      │───┘
                            │    start_time    │
                            │    end_time      │
                            │    confidence_avg│
                            │    best_frame_path│
                            └──────────────────┘
```

### 6.2 SQL Schema

```sql
-- 动物档案表
CREATE TABLE animal_profiles (
    id              TEXT PRIMARY KEY,       -- cat_a3f2b1c0
    class_name      TEXT NOT NULL,          -- 'cat' | 'weasel' | 'bird'
    nickname        TEXT,                   -- 用户自定义昵称 (可选)
    description     TEXT,                   -- API 返回的 color + distinguishing_features
    thumbnail_path  TEXT NOT NULL,          -- 缩略图文件路径
    feature_vector  BLOB NOT NULL,          -- 特征向量 (numpy 序列化)
    first_seen      TIMESTAMP NOT NULL,     -- 首次发现时间
    last_seen       TIMESTAMP NOT NULL,     -- 最近发现时间
    appearance_count INTEGER DEFAULT 1,     -- 累计出现次数
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_profiles_class ON animal_profiles(class_name);
CREATE INDEX idx_profiles_last_seen ON animal_profiles(last_seen);

-- 媒体来源表
CREATE TABLE media_sources (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id      TEXT NOT NULL,          -- 关联动物档案
    source_type     TEXT NOT NULL,          -- 'image' | 'video'
    file_name       TEXT NOT NULL,          -- 文件名
    file_path       TEXT NOT NULL,          -- 文件完整路径
    file_size       INTEGER,               -- 文件大小 (bytes)
    file_hash       TEXT,                   -- SHA-256 哈希
    added_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES animal_profiles(id) ON DELETE CASCADE
);

CREATE INDEX idx_sources_profile ON media_sources(profile_id);
CREATE INDEX idx_sources_path ON media_sources(file_path);

-- 视频时间段表
CREATE TABLE time_segments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id        INTEGER NOT NULL,       -- 关联 media_sources
    start_time      REAL NOT NULL,          -- 开始时间 (秒)
    end_time        REAL NOT NULL,          -- 结束时间 (秒)
    confidence_avg  REAL,                   -- 段内平均置信度
    best_frame_path TEXT,                   -- 最佳帧截图路径
    FOREIGN KEY (media_id) REFERENCES media_sources(id) ON DELETE CASCADE
);

CREATE INDEX idx_segments_media ON time_segments(media_id);

-- API 分类缓存表 (跨运行持久化)
CREATE TABLE classification_cache (
    crop_hash       TEXT PRIMARY KEY,       -- 动物裁剪区域的 SHA-256
    result_json     TEXT NOT NULL,          -- ClassificationResult JSON
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 动物发现记录表 (黄鼠狼/鸟 — 仅记录，不建档)
CREATE TABLE animal_sightings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    class_name      TEXT NOT NULL,          -- 'weasel' | 'bird'
    file_name       TEXT NOT NULL,          -- 来源文件名
    file_path       TEXT NOT NULL,          -- 来源文件路径
    source_type     TEXT NOT NULL,          -- 'image' | 'video'
    timestamp       REAL,                   -- 视频时间戳 (图片为 NULL)
    confidence      REAL,                   -- 分类置信度
    color           TEXT,                   -- API 返回的颜色描述
    features        TEXT,                   -- API 返回的特征描述
    thumbnail_path  TEXT,                   -- 截图路径
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sightings_class ON animal_sightings(class_name);
CREATE INDEX idx_sightings_date ON animal_sightings(created_at);

- 处理日志表 (记录每次处理的文件状态)
CREATE TABLE processing_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path       TEXT NOT NULL,
    file_type       TEXT NOT NULL,          -- 'image' | 'video'
    status          TEXT NOT NULL,          -- 'success' | 'skipped' | 'error'
    error_message   TEXT,                   -- 错误信息
    profiles_found  INTEGER DEFAULT 0,      -- 发现的动物档案数
    api_calls       INTEGER DEFAULT 0,      -- 该文件的 API 调用次数
    processed_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_log_status ON processing_log(status);
CREATE INDEX idx_log_processed ON processing_log(processed_at);
```

### 6.3 特征向量存储方案

```
方案选择: BLOB 存储 (numpy array → bytes)

序列化:
  np.ndarray.tobytes()  # float32 → bytes

反序列化:
  np.frombuffer(blob, dtype=np.float32)

优势:
  - 无需额外依赖
  - 512 维 float32 ≈ 2KB/条，存储开销低
  - 查询时批量加载，内存占用可接受
```

---

## 7. API 设计

### 7.1 CLI 接口

```
Usage: animal-id [OPTIONS] COMMAND [ARGS]...

Commands:
  scan     扫描并识别媒体文件中的动物
  list     列出所有动物档案
  show     显示单个动物档案详情
  export   导出档案数据
  delete   删除动物档案
  stats    显示统计信息
```

#### `scan` 命令

```bash
# 扫描单张图片
animal-id scan /path/to/cat_photo.jpg

# 扫描整个目录
animal-id scan /path/to/media/

# 递归扫描 + 自定义配置
animal-id scan /path/to/media/ --recursive --config custom_config.yaml

# 只扫描图片
animal-id scan /path/ --type image

# 只扫描视频
animal-id scan /path/ --type video
```

#### `list` 命令

```bash
# 列出所有档案
animal-id list

# 按类别筛选
animal-id list --class cat
animal-id list --class bird

# 分页
animal-id list --limit 20 --offset 40

# JSON 输出
animal-id list --format json
```

#### `show` 命令

```bash
# 显示档案详情
animal-id show cat_a3f2b1c0

# 输出格式
animal-id show cat_a3f2b1c0 --format json
```

#### `export` 命令

```bash
# 导出所有档案
animal-id export --output profiles.json

# 按类别导出
animal-id export --class cat --output cats.csv --format csv
```

#### `delete` 命令

```bash
# 删除档案
animal-id delete cat_a3f2b1c0

# 强制删除 (不确认)
animal-id delete cat_a3f2b1c0 --force
```

#### `stats` 命令

```bash
animal-id stats
# 输出:
# Total animals: 12
#   - Cat: 5
#   - Weasel: 3
#   - Bird: 4
# Total media processed: 50
# Last scan: 2026-06-09 14:30:00
```

### 7.2 配置文件 (YAML)

```yaml
# config.yaml
models:
  detector:
    path: "models/yolov8s.pt"          # YOLOv8s COCO 预训练权重
    confidence_threshold: 0.25         # 偏低，宁多不漏
    iou_threshold: 0.45
  feature_extractor:
    path: "models/resnet50_reid.pt"
    embedding_dim: 512

api:
  provider: "deepseek"                 # deepseek | claude | openai
  api_key: "${API_KEY}"                # 从环境变量读取
  base_url: "https://api.deepseek.com/v1/chat/completions"
  model: "deepseek-chat"              # 支持视觉的模型
  timeout: 10                          # 单次请求超时 (秒)
  max_retries: 3                       # 最大重试次数
  temperature: 0.1                     # 低温度确保稳定输出

fallback:
  enabled: true                        # API 不可用时是否降级
  yolo_class_mapping:                  # YOLO COCO class → 动物类型
    14: "bird"
    15: "cat"

matching:
  similarity_threshold: 0.75           # 余弦相似度主阈值
  secondary_threshold: 0.65            # 辅助阈值 (配合文字特征)
  max_gap_seconds: 3.0                 # 视频时间段合并最大间隔
  min_segment_duration: 0.5            # 最短有效时间段 (秒)

video:
  sample_fps: 1.0                      # 采样帧率
  motion_threshold: 0.15               # 运动检测阈值
  resize_width: 1280                   # 视频帧预处理宽度
  frame_similarity_threshold: 0.95     # 帧间去重相似度阈值

storage:
  database_path: "data/database/animal_id.db"
  profiles_path: "data/profiles/"
  thumbnail_size: [300, 300]           # 缩略图尺寸

input:
  recursive: true                      # 默认递归扫描
  max_file_size_gb: 4                  # 最大文件大小

logging:
  level: "INFO"                        # DEBUG | INFO | WARNING | ERROR
  file: "logs/animal_id.log"
  max_size_mb: 50
  backup_count: 5

performance:
  batch_size: 8                        # 批量推理大小
  num_workers: 4                       # DataLoader workers
  use_gpu: true                        # 是否使用 GPU
  api_concurrency: 5                   # API 并发请求数
```

---

## 8. 错误处理与异常策略

### 8.1 异常分类

```
┌─────────────────────────────────────────────────────────────┐
│                      异常层次结构                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  AnimalIDError (Base)                                       │
│  ├── InputError                                             │
│  │   ├── FileNotFoundError                                  │
│  │   ├── UnsupportedFormatError                             │
│  │   ├── CorruptedFileError                                 │
│  │   └── FileTooLargeError                                  │
│  ├── RecognitionError                                       │
│  │   ├── ModelNotFoundError                                 │
│  │   ├── InferenceError                                     │
│  │   └── NoAnimalDetectedError  (非严重，仅记录)              │
│  ├── APIError                                               │
│  │   ├── APIConnectionError     (网络不通)                   │
│  │   ├── APITimeoutError        (请求超时)                   │
│  │   ├── APIRateLimitError      (频率限制)                   │
│  │   ├── APIAuthError           (API Key 无效)              │
│  │   ├── APIClassificationError (分类失败/重试耗尽)           │
│  │   └── ClassificationParseError (响应解析失败)             │
│  ├── StorageError                                           │
│  │   ├── DatabaseConnectionError                            │
│  │   ├── DatabaseWriteError                                 │
│  │   └── StorageFullError                                   │
│  └── ConfigurationError                                     │
│      ├── InvalidConfigError                                 │
│      └── ModelPathNotFoundError                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 错误处理策略表

| 场景 | 检测方式 | 处理策略 | 日志级别 | 是否中断 |
|------|----------|----------|----------|----------|
| 文件不存在 | `os.path.exists()` | 跳过，记录错误 | ERROR | 否 |
| 不支持的格式 | 扩展名 + 魔数校验 | 跳过，记录 SKIPPED | WARNING | 否 |
| 文件大小为 0 | `os.path.getsize()` | 跳过 | WARNING | 否 |
| 图片损坏 | `cv2.imread()` 返回 None | 跳过 | ERROR | 否 |
| 视频无法打开 | `cv2.VideoCapture.isOpened()` | 跳过 | ERROR | 否 |
| 视频解码失败 | 帧读取异常 | 跳过剩余帧 | ERROR | 否 |
| 模型文件缺失 | 启动时检查文件存在性 | 拒绝启动 | CRITICAL | 是 |
| GPU 不可用 | 推理前检测 CUDA | 回退到 CPU，记录 | WARNING | 否 |
| 未检测到动物 | 检测结果为空列表 | 正常处理，记录 | INFO | 否 |
| **API 连接失败** | `httpx.ConnectError` | 自动降级到 Fallback | ERROR | 否 |
| **API 超时** | `httpx.TimeoutException` | 重试 3 次，仍失败则降级 | WARNING | 否 |
| **API Rate Limit** | HTTP 429 | 指数退避等待，超限则降级 | WARNING | 否 |
| **API Key 无效** | HTTP 401/403 | 降级处理 + 提示用户检查 Key | CRITICAL | 否 |
| **API 响应解析失败** | JSON 解析异常 | 重试 1 次，仍失败则降级 | ERROR | 否 |
| 数据库写入失败 | 捕获 SQL 异常 | 重试 3 次，之后跳过 | ERROR | 否 |
| 磁盘空间不足 | 写入前检查 | 终止处理，保留已处理结果 | CRITICAL | 是 |
| 内存不足 | `MemoryError` 捕获 | 减小批次，清理缓存 | ERROR | 否 |
| 配置文件解析失败 | YAML 解析异常 | 使用默认配置 | WARNING | 否 |
| 路径权限不足 | `PermissionError` | 跳过该路径 | ERROR | 否 |
| 视频帧提取超时 | 计时器检测 | 跳过该视频 | ERROR | 否 |

### 8.3 优雅降级策略

```
GPU 不可用     ──► CPU 推理 (YOLO 性能下降但功能完整)
API 不可用      ──► Fallback 本地分类 (YOLO class 映射 + 启发式)
                     ↓ 黄鼠狼等无法识别 → 标记 'unknown'
API 超时/限流   ──► 指数退避重试 (1s→2s→4s) → 仍失败则 Fallback
模型缺失       ──► 提示下载命令，拒绝启动
磁盘不足       ──► 提前检测，预留 500MB 安全余量
单文件失败     ──► 不影响其他文件的处理
大批量文件     ──► 分批处理，每批之间可暂停/恢复
API Key 无效   ──► 警告 + 全部走 Fallback 模式 (功能受限但可运行)
```

**降级等级：**

| 等级 | 状态 | 检测能力 | 分类能力 | 个体匹配 |
|------|------|----------|----------|----------|
| 🟢 正常 | API 可用 | YOLO ✅ | LLM API (高精度) ✅ | ResNet50 ✅ |
| 🟡 降级 | API 不可用 | YOLO ✅ | Fallback (低精度) ⚠️ | ResNet50 ✅ |
| 🔴 最小 | 模型缺失 | ❌ | ❌ | ❌ |

### 8.4 处理摘要报告格式

```json
{
  "scan_id": "scan_20260609_143000",
  "started_at": "2026-06-09T14:30:00",
  "finished_at": "2026-06-09T14:35:22",
  "elapsed_seconds": 322.5,
  "api_usage": {
    "total_calls": 45,
    "cache_hits": 12,
    "fallback_triggers": 2,
    "estimated_cost_cny": 0.35
  },
  "summary": {
    "total_files": 100,
    "processed_successfully": 87,
    "skipped_unsupported": 5,
    "skipped_corrupted": 3,
    "skipped_no_animal": 40,
    "errors": 5
  },
  "animals_found": {
    "new_profiles": 3,
    "updated_profiles": 7,
    "total_detections": 45
  },
  "errors": [
    {
      "file": "/path/to/broken.jpg",
      "error_type": "CorruptedFileError",
      "message": "cv2.imread returned None"
    },
    {
      "file": "/path/to/cat_video.mp4",
      "error_type": "APITimeoutError",
      "message": "API timeout after 3 retries, used fallback"
    }
  ],
  "details": {
    "cat_detections": 20,
    "weasel_detections": 12,
    "bird_detections": 13
  }
}
```

---

## 9. 测试策略

### 9.1 测试金字塔

```
        ┌───────┐
        │  E2E  │  ← 端到端: 完整 pipeline 测试
        │  5%   │
       ┌┴───────┴┐
       │Integration│ ← 集成: 模块间交互
       │   15%     │
      ┌┴───────────┴┐
      │   Unit Tests  │ ← 单元: 每个函数/类
      │     80%       │
      └───────────────┘
```

### 9.2 测试用例清单

#### 单元测试

| 模块 | 测试用例 | 预期结果 |
|------|----------|----------|
| Scanner | 传入图片目录 | 返回所有图片路径 |
| Scanner | 传入混合目录 (含不支持格式) | 分类正确，不支持格式记入 skipped |
| Scanner | 传入空目录 | 返回空列表 |
| Validator | 有效 JPEG 文件 | 通过 |
| Validator | 损坏的 PNG 文件 | 抛出 CorruptedFileError |
| Validator | 不支持的 .txt 文件 | 抛出 UnsupportedFormatError |
| Validator | 0 字节文件 | 抛出 CorruptedFileError |
| Detector | 含猫的图片 | 返回 RawDetection (有动物区域) |
| Detector | 不含动物的风景图 | 返回空列表 |
| Detector | 多只动物的图片 | 返回多个 RawDetection |
| Detector | 较低置信度的动物 | 仍返回 (阈值 0.25, 宁多勿漏) |
| APIClassifier | 猫的特写图 | 返回 class='cat', conf > 0.9 |
| APIClassifier | 黄鼠狼图片 | 返回 class='weasel', conf > 0.8 |
| APIClassifier | API 超时 | 重试 3 次后抛 APIClassificationError |
| APIClassifier | 缓存命中 | 不调用 API，直接返回缓存结果 |
| Fallback | 猫图片 (YOLO class_id=15) | 返回 class='cat' (降级模式) |
| Fallback | 黄鼠狼图片 (COCO 无对应) | 返回 class='other' (无法识别) |
| FeatureExtractor | 同一只猫的两张不同图片 | 特征向量余弦相似度 > 0.8 |
| FeatureExtractor | 两只不同猫的图片 | 特征向量余弦相似度 < 0.7 |
| Matcher | 已知个体的特征 | 返回匹配 (is_new=False) |
| Matcher | 新个体的特征 | 返回不匹配 (is_new=True) |
| Matcher | 空数据库 | 返回 is_new=True |
| Matcher | 模糊匹配 (0.65-0.75) + 特征文字匹配 | 基于 API 描述辅助判断 |
| VideoReader | 有效 MP4 文件 | 正常提取帧 |
| VideoReader | 损坏的 AVI 文件 | 抛出 CorruptedFileError |
| FrameDedup | 连续相同帧 | 跳过 30%+ 冗余帧 |
| TimeSegmentMerger | 连续检测 | 合并为单一段 |
| TimeSegmentMerger | 间隔 > 3s | 切分为两段 |
| Database | 创建档案 | 写入成功，可查询 |
| Database | 添加来源 | 关联正确 |
| Database | 级联删除 | 关联的来源和段一并删除 |

#### 集成测试

| 场景 | 描述 |
|------|------|
| 图片完整流程 | 输入图片 → YOLO检测 → API分类 → Re-ID匹配 → 建档 |
| 视频完整流程 | 输入视频 → 帧提取 → 检测 → 去重 → 时间段合并 → API分类 → 建档 |
| API 降级流程 | 模拟 API 不可用 → 自动切换到 Fallback 分类器 |
| API 重试流程 | 模拟 API 超时 → 指数退避重试 → 恢复 or 降级 |
| 缓存命中流程 | 相同图片再次处理 → 跳过 API 调用，直接复用结果 |
| 重复检出同一动物 | 同一只猫的两张不同图片 → 归入同一档案 |
| 新动物 | 新动物 → 创建新档案 |
| 批量处理 | 100 张混合图片 → 全部处理，无遗漏 |
| 中断恢复 | 处理中途退出 → 已处理数据持久化 |
| 配置加载 | 加载自定义 YAML → 参数生效 |
| API 并发控制 | 多个检测并发调 API → 不超过配置的 api_concurrency |

### 9.3 测试数据准备

```
tests/fixtures/
├── images/
│   ├── cat_single.jpg          # 单只猫
│   ├── cat_multi.jpg           # 多只猫
│   ├── weasel.jpg              # 黄鼠狼
│   ├── bird.jpg                # 鸟
│   ├── no_animal.jpg           # 无动物风景
│   ├── corrupted.jpg           # 损坏文件 (0 字节)
│   └── large_4k.jpg            # 4K 大图
├── videos/
│   ├── cat_video_short.mp4     # 5 秒猫视频
│   ├── birds_multi.mp4         # 多只鸟视频
│   ├── no_animal_scene.mp4     # 无动物视频
│   └── corrupted_video.avi     # 损坏视频
├── api_responses/              # Mock API 响应
│   ├── deepseek_cat.json
│   ├── deepseek_weasel.json
│   ├── deepseek_bird.json
│   └── deepseek_error.json
└── expected/                   # 预期结果 (用于断言)
    ├── cat_detection.json
    └── cat_profile.json
```

### 9.4 评估指标

| 指标 | 测试方法 | 目标值 |
|------|----------|--------|
| 检测召回率 (YOLO) | 标注测试集评估 | ≥ 95% (宁可多检) |
| 检测精确率 (YOLO) | 标注测试集评估 | ≥ 70% (允许误检，API 会过滤) |
| API 分类准确率 | 标注测试集评估 | ≥ 95% |
| Fallback 分类准确率 | 标注测试集评估 | ≥ 60% (降级模式预期较低) |
| 猫个体 Re-ID Rank-1 | 同一只猫的不同图片 | ≥ 80% |
| 猫个体 Re-ID mAP | 多查询评估 | ≥ 75% |
| YOLO 推理延迟 (GPU) | 单张 640×640 | < 50ms |
| YOLO 推理延迟 (CPU) | 单张 640×640 | < 500ms |
| API 调用延迟 (P50) | 端到端测试 | < 2s |
| API 调用延迟 (P99) | 端到端测试 | < 8s (含重试) |
| 视频帧去重率 | 10 分钟视频测试 | ≥ 30% |

---

## 10. 部署方案

### 10.1 环境搭建

```bash
# 1. 克隆仓库
git clone <repo_url> animal-id-system
cd animal-id-system

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 下载模型权重
bash scripts/download_models.sh
# 该脚本从模型仓库下载:
#   - yolov8s.pt              (~22 MB) — YOLOv8s COCO 预训练
#   - resnet50_reid.pt        (~98 MB) — Re-ID 特征提取器

# 5. 配置 API Key
export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxx"
# 或写入 .env 文件

# 6. 验证安装
python -m src.main --version
python -m src.main test-run   # 使用内置测试图片验证
```

### 10.2 Docker 部署 (可选)

```dockerfile
FROM nvidia/cuda:12.1-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y \
    python3.10 python3-pip \
    ffmpeg libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY models/ ./models/
COPY config.yaml .

ENTRYPOINT ["python", "-m", "src.main"]
```

### 10.3 依赖清单 (`requirements.txt`)

```
# 核心依赖
torch>=2.0.0
torchvision>=0.15.0
ultralytics>=8.0.0              # YOLO 推理
opencv-python>=4.8.0
numpy>=1.24.0
Pillow>=10.0.0

# HTTP 客户端 (API 调用)
httpx>=0.25.0                    # 异步 HTTP
tenacity>=8.0.0                  # 重试策略

# 数据库
sqlalchemy>=2.0.0

# CLI
click>=8.1.0
rich>=13.0.0

# 配置
PyYAML>=6.0
omegaconf>=2.3.0
python-dotenv>=1.0.0             # .env 文件加载

# 工具
tqdm>=4.65.0
python-magic>=0.4.27             # 文件类型检测
imagehash>=4.3.0                 # 感知哈希 (帧去重)

# 测试
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-asyncio>=0.21.0           # 异步测试
respx>=0.20.0                    # HTTP Mock
```

---

## 11. 项目计划与里程碑

### 里程碑

| 阶段 | 内容 | 预计工期 | 交付物 |
|------|------|----------|--------|
| M1 | 项目初始化 + 设计文档 | 1 周 | design.md, 项目骨架, CI 配置 |
| M2 | 输入模块开发 | 1.5 周 | Scanner, Validator, VideoReader |
| M3 | YOLO 检测 + API 分类器开发 | 2 周 | Detector, APIClassifier, Fallback, Mock 测试 |
| M4 | 猫特征提取 + 个体匹配 | 1 周 | FeatureExtractor (仅猫), Matcher, sightings 记录 |
| M5 | 档案模块 + 数据库 | 1.5 周 | ProfileManager, sightings 表, CLI (list/show/delete) |
| M6 | 流水线编排 + 缓存 + CLI 完善 | 1.5 周 | Pipeline, 去重缓存, CLI scan/export/stats |
| M7 | 测试 + 错误处理完善 | 1.5 周 | 单元测试, 集成测试, API Mock, 异常覆盖 |
| M8 | 文档 + 部署脚本 + 发布 | 1 周 | README, 部署文档, Docker 配置 |

**总工期: 约 11 周**

> 相比纯本地方案，混合方案省去了模型训练数据收集和标注的时间（约 2-3 周）。
> 个体匹配仅针对猫，鸟/黄鼠狼不做 Re-ID，进一步节省约 0.5 周。

---

## 12. 附录

### A. 支持的文件格式完整列表

| 类型 | 格式 | 扩展名 | MIME Type |
|------|------|--------|-----------|
| 图片 | JPEG | .jpg, .jpeg, .jpe, .jfif | image/jpeg |
| 图片 | PNG | .png | image/png |
| 图片 | BMP | .bmp, .dib | image/bmp |
| 图片 | TIFF | .tiff, .tif | image/tiff |
| 图片 | WebP | .webp | image/webp |
| 图片 | GIF | .gif | image/gif |
| 视频 | MPEG-4 | .mp4, .m4v | video/mp4 |
| 视频 | AVI | .avi | video/x-msvideo |
| 视频 | QuickTime | .mov, .qt | video/quicktime |
| 视频 | Matroska | .mkv | video/x-matroska |
| 视频 | Windows Media | .wmv | video/x-ms-wmv |
| 视频 | Flash Video | .flv | video/x-flv |

### B. 模型准备说明

#### B.1 需要下载的模型

| 模型 | 用途 | 大小 | 来源 |
|------|------|------|------|
| YOLOv8s | 动物检测 (Layer 1) | ~22 MB | ultralytics 官方 (COCO 预训练) |
| ResNet50 Re-ID | 个体特征提取 (Layer 3) | ~98 MB | 自定义训练 or 开源 Re-ID 权重 |

#### B.2 分类无需训练

动物分类由 LLM API 完成，**无需任何训练数据**。仅需在 Prompt 中明确定义目标类别（猫/黄鼠狼/鸟/其他），LLM 的预训练知识已覆盖这些常见动物。

#### B.3 Re-ID 模型微调建议 (可选)

如需提升个体区分精度，可收集同类别动物的多角度图片微调 Re-ID 模型：

| 类别 | 推荐个体数 | 每个体推荐图片数 | 数据来源 |
|------|-----------|-----------------|----------|
| 猫 | ≥ 50 只 | ≥ 20 张/只 | Oxford Pets, 网络采集 |
| 黄鼠狼 | ≥ 20 只 | ≥ 15 张/只 | 野生动物数据集, 网络采集 |
| 鸟 | ≥ 50 只 | ≥ 20 张/只 | CUB-200-2011 |

### C. 特征向量更新策略

当同一动物多次出现时，更新其特征向量采用**指数移动平均**：

```
new_feature = α × current_feature + (1 - α) × stored_feature
其中 α = 0.3 (新特征的权重)
```

这确保了随着同一动物出现次数增加，其特征表示越来越稳定，同时也能适应因光照、角度等因素造成的特征变化。

### D. 关键设计决策记录

| 决策 | 选项 | 选择 | 理由 |
|------|------|------|------|
| 数据库 | SQLite vs PostgreSQL | SQLite | 单机部署、零配置、便携 |
| 检测框架 | YOLO vs Faster R-CNN | YOLOv8 | 速度快、COCO 预训练含猫/鸟、免费 |
| 分类方案 | 本地模型 vs LLM API | **LLM API (混合)** | 零训练、高精度、天然理解黄鼠狼，成本可控 |
| 个体区分 | Re-ID vs 追踪 | Re-ID (本地) | 跨视频/跨时间匹配，高频调用走本地 |
| LLM Provider | DeepSeek vs Claude vs OpenAI | DeepSeek (主) + Claude (备) | 性价比最高，中文生态友好 |
| API 降级 | 直接失败 vs 本地降级 | 本地 Fallback | 保证离线可用，功能降级但不断线 |
| 视频采样 | 全帧 vs 采样 | 混合采样 + 帧去重 | 平衡精度和 API 调用成本 |
| CLI 框架 | Click vs argparse | Click | 类型安全、可组合、美观 |
| 个体匹配增强 | 纯视觉 vs 视觉+文字 | **视觉特征 + API 文字描述** | 利用 API 返回的颜色/特征文字辅助模糊匹配 |

### E. 与原纯本地方案对比

| 维度 | 纯本地模型 (v1.0) | 混合方案 (v2.0) |
|------|-------------------|-----------------|
| 训练数据需求 | 需标注 10,000+ 张图片 | **零训练数据** |
| 黄鼠狼识别 | 难 (数据稀缺) | **易** (LLM 天然理解) |
| 新增动物类别 | 需重新训练模型 | **改 Prompt 即可** |
| 分类精度 | 80-90% (取决于训练质量) | **95%+** (取决于 LLM) |
| 离线可用性 | ✅ 完全离线 | ⚠️ API 不可用时降级 (精度下降) |
| 单次分类成本 | 免费 | ~¥0.01 |
| 月使用成本 | 免费 | ¥2-80 (视使用量) |
| GPU 需求 | 需 GPU 训练 | 仅推理 (CPU 可运行) |
| 维护成本 | 高 (模型更新需重训) | **低** (Prompt 迭代即可) |

---

> **文档维护**: 本文档随着项目推进持续更新。任何架构变更需先在本文档中反映并经过评审。
>
> **相关文档**:
> - API 详细文档: (待创建)
> - 用户手册: (待创建)
> - 模型训练指南: (待创建)
