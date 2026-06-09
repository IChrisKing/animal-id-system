"""离线降级分类器 — API 不可用时的 Fallback (Layer 2)"""

from src.recognition.api_classifier import ClassificationResult


class FallbackClassifier:
    """基于 YOLO class_id 的简单映射 + 启发式规则"""

    # YOLO COCO class_id → 动物类型
    COCO_MAPPING = {
        14: "bird",
        15: "cat",
        # 其他动物类 16-25 无法精确区分 → other
    }

    def classify(self, yolo_class_id: int, yolo_confidence: float) -> ClassificationResult:
        """
        降级分类：YOLO class_id 直接映射。
        注意：降级模式下无法识别黄鼠狼（COCO 不含该类）。
        """
        class_name = self.COCO_MAPPING.get(yolo_class_id, "other")
        # 降级置信度打折
        confidence = yolo_confidence * 0.6 if class_name != "other" else 0.3

        return ClassificationResult(
            class_name=class_name,
            confidence=round(confidence, 2),
            color="",
            distinguishing_features="(offline fallback — manual review recommended)",
        )
