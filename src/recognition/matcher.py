"""猫个体匹配器 — 余弦相似度 (Layer 3, 仅猫)"""

from dataclasses import dataclass

import numpy as np

from src.recognition.api_classifier import ClassificationResult


@dataclass
class MatchResult:
    profile_id: str | None    # 匹配到的档案 ID，None 表示新个体
    is_new: bool              # 是否为新个体
    similarity: float         # 最高相似度
    description: str = ""     # 匹配到的档案描述


class IndividualMatcher:
    """仅对猫进行个体匹配"""

    SIMILARITY_THRESHOLD = 0.75
    SECONDARY_THRESHOLD = 0.65

    def match(
        self,
        feature: np.ndarray,
        classification: ClassificationResult,
        known_features: dict[str, np.ndarray],
    ) -> MatchResult:
        """
        匹配猫个体。
        - classification.class_name 不为 'cat' → 直接返回 (非猫不匹配)
        - 已知档案为空 → 新猫
        - 余弦相似度 ≥ 0.75 → 匹配到已有猫
        - 余弦相似度 0.65~0.75 + 文字特征匹配 → 匹配到已有猫
        - 余弦相似度 < 0.65 → 新猫
        """
        if classification.class_name != "cat":
            return MatchResult(None, False, 0.0)

        if not known_features:
            return MatchResult(None, True, 0.0)

        max_sim = 0.0
        best_id = None
        for ind_id, stored_feat in known_features.items():
            sim = self._cosine_similarity(feature, stored_feat)
            if sim > max_sim:
                max_sim = sim
                best_id = ind_id

        if max_sim >= self.SIMILARITY_THRESHOLD:
            return MatchResult(best_id, False, round(max_sim, 4))
        elif max_sim >= self.SECONDARY_THRESHOLD:
            # 辅助文字特征匹配
            if self._text_features_match(classification):
                return MatchResult(best_id, False, round(max_sim, 4))

        return MatchResult(None, True, round(max_sim, 4))

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """余弦相似度"""
        a = a.astype(np.float32)
        b = b.astype(np.float32)
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    def _text_features_match(self, classification: ClassificationResult) -> bool:
        """检查 API 返回的文字描述是否有足够信息用于辅助判断"""
        text = classification.color + " " + classification.distinguishing_features
        # 文字描述至少有一定长度才算有效
        return len(text.strip()) > 5
