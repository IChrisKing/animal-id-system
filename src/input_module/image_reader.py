"""图片读取器"""

import cv2
import numpy as np


MAX_DIMENSION = 4096


def read_image(file_path: str, max_dimension: int = MAX_DIMENSION) -> np.ndarray:
    """
    读取图片，返回 BGR numpy array。
    超大图片等比缩放至 max_dimension 以内。
    """
    image = cv2.imread(file_path)
    if image is None:
        raise ValueError(f"无法读取图片: {file_path}")

    h, w = image.shape[:2]
    if max(h, w) > max_dimension:
        scale = max_dimension / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    return image
