"""动物检测器 — YOLOv8 (Layer 1)"""

import base64
import hashlib
import io
from dataclasses import dataclass, field

import cv2
import numpy as np
from ultralytics import YOLO

# COCO 中所有动物相关的 class_id (14=bird, 15=cat, 16=dog, ...)
ANIMAL_CLASS_IDS = set(range(14, 26))


@dataclass
class RawDetection:
    bbox: list[int]              # [x1, y1, x2, y2] 像素坐标
    yolo_class_id: int           # YOLO COCO class_id (仅供参考)
    yolo_confidence: float       # YOLO 检测置信度
    crop: np.ndarray             # 裁剪+padding 后的动物区域 (BGR)
    crop_base64: str             # Base64 编码 (JPEG 压缩)
    crop_hash: str               # SHA-256 哈希
    source_file: str = ""        # 来源文件名
    source_type: str = "image"   # 'image' | 'video'
    timestamp: float | None = None  # 视频时间戳 (图片为 None)


class AnimalDetector:
    """YOLOv8 动物检测器 — 只负责定位，不负责分类"""

    def __init__(
        self,
        model_path: str = "yolov8s.pt",
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        crop_padding_ratio: float = 0.1,
    ):
        self.model = YOLO(model_path)
        self.conf_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.padding = crop_padding_ratio

    def detect(self, image: np.ndarray, source_file: str = "") -> list[RawDetection]:
        """
        检测图片中的所有动物区域。
        返回 RawDetection 列表；无动物时返回空列表。
        """
        results = self.model(
            image,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            verbose=False,
        )

        detections: list[RawDetection] = []
        h, w = image.shape[:2]

        for result in results:
            if result.boxes is None:
                continue
            boxes = result.boxes.xyxy.cpu().numpy()
            classes = result.boxes.cls.cpu().numpy().astype(int)
            confs = result.boxes.conf.cpu().numpy()

            for box, cls_id, conf in zip(boxes, classes, confs):
                if cls_id not in ANIMAL_CLASS_IDS:
                    continue  # 非动物类别，跳过

                x1, y1, x2, y2 = box.astype(int)
                # 添加 padding
                bh, bw = y2 - y1, x2 - x1
                pad_x = int(bw * self.padding)
                pad_y = int(bh * self.padding)
                x1 = max(0, x1 - pad_x)
                y1 = max(0, y1 - pad_y)
                x2 = min(w, x2 + pad_x)
                y2 = min(h, y2 + pad_y)

                crop = image[y1:y2, x1:x2]
                if crop.size == 0:
                    continue

                # Base64 编码 (JPEG 压缩, 最长边 512)
                base64_str = self._encode_crop(crop)
                crop_hash = hashlib.sha256(crop.tobytes()).hexdigest()[:16]

                detections.append(RawDetection(
                    bbox=[x1, y1, x2, y2],
                    yolo_class_id=cls_id,
                    yolo_confidence=float(conf),
                    crop=crop,
                    crop_base64=base64_str,
                    crop_hash=crop_hash,
                    source_file=source_file,
                ))

        return detections

    def _encode_crop(self, crop: np.ndarray, max_edge: int = 512) -> str:
        """将裁剪区域压缩为 JPEG base64 字符串"""
        h, w = crop.shape[:2]
        if max(h, w) > max_edge:
            scale = max_edge / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            crop = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_AREA)

        _, buffer = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return base64.b64encode(buffer).decode("utf-8")
