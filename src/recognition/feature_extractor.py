"""猫特征提取器 — ResNet50 (Layer 3, 仅猫)"""

import logging

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """ResNet50 + Linear 投影 → 512 维特征向量"""

    EMBEDDING_DIM = 512
    INPUT_SIZE = (256, 128)  # H × W

    def __init__(self, model_path: str = "src/models/resnet50_reid.pt"):
        self.model_path = model_path
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self._build_model()
        self.model.to(self.device)
        self.model.eval()

        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize(self.INPUT_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

        logger.info(f"FeatureExtractor 初始化完成 (device={self.device})")

    def _build_model(self) -> nn.Module:
        """构建 ResNet50 backbone + embedding"""
        try:
            from torchvision.models import resnet50, ResNet50_Weights
            backbone = resnet50(weights=ResNet50_Weights.DEFAULT)
        except Exception:
            from torchvision.models import resnet50
            backbone = resnet50(weights=None)

        # 去掉最后的 FC 层，保留 avgpool 后的 2048-d 特征
        modules = list(backbone.children())[:-1]
        self.backbone = nn.Sequential(*modules)
        self.embedding = nn.Linear(2048, self.EMBEDDING_DIM)

        model = nn.Sequential(
            self.backbone,
            nn.Flatten(),
            self.embedding,
        )

        # 尝试加载微调权重
        try:
            state_dict = torch.load(self.model_path, map_location=self.device, weights_only=True)
            model.load_state_dict(state_dict, strict=False)
            logger.info(f"已加载 Re-ID 模型: {self.model_path}")
        except FileNotFoundError:
            logger.warning(
                f"Re-ID 模型文件未找到: {self.model_path}。"
                f"将使用未微调的 ResNet50 特征（个体区分精度有限）"
            )
        except Exception as e:
            logger.warning(f"加载 Re-ID 模型失败: {e}。使用未微调特征")

        return model

    def extract(self, crop: np.ndarray) -> np.ndarray:
        """
        提取猫的 512 维特征向量 (L2 归一化)。
        输入: BGR crop
        输出: np.ndarray shape=(512,), dtype=float32
        """
        # BGR → RGB
        rgb_crop = crop[:, :, ::-1]

        try:
            tensor = self.transform(rgb_crop).unsqueeze(0).to(self.device)
            with torch.no_grad():
                vec = self.model(tensor)
            vec = F.normalize(vec, p=2, dim=1)
            return vec.cpu().numpy().flatten().astype(np.float32)
        except Exception as e:
            logger.error(f"特征提取失败: {e}")
            # 返回随机向量作为 fallback (后续匹配会视为新个体)
            rng = np.random.RandomState(hash(crop.tobytes()) % (2**31))
            vec = rng.randn(self.EMBEDDING_DIM).astype(np.float32)
            vec = vec / np.linalg.norm(vec)
            return vec
