"""格式验证器 — 验证图片文件是否有效可读"""

import os
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class ValidationResult:
    valid: bool
    file_path: str
    error: str = ""
    width: int = 0
    height: int = 0
    format: str = ""


# 图片文件头魔数
MAGIC_BYTES = {
    b'\xff\xd8\xff': 'jpeg',
    b'\x89PNG': 'png',
    b'BM': 'bmp',
    b'II*\x00': 'tiff',
    b'MM\x00*': 'tiff',
    b'RIFF': 'webp',       # RIFF .... WEBP
    b'GIF8': 'gif',
}


class ImageValidator:

    def validate(self, file_path: str) -> ValidationResult:
        # 1. 存在性检查
        if not os.path.exists(file_path):
            return ValidationResult(False, file_path, "文件不存在")
        if not os.path.isfile(file_path):
            return ValidationResult(False, file_path, "不是文件")

        # 2. 大小检查
        try:
            size = os.path.getsize(file_path)
            if size == 0:
                return ValidationResult(False, file_path, "文件大小为 0")
        except OSError as e:
            return ValidationResult(False, file_path, f"无法读取文件: {e}")

        # 3. 魔数检查
        fmt = self._check_magic(file_path)
        if fmt is None:
            return ValidationResult(False, file_path, "文件头魔数不匹配，可能不是有效图片或格式不支持")

        # 4. OpenCV 读取检查
        image = cv2.imread(file_path)
        if image is None:
            return ValidationResult(False, file_path, "cv2.imread 返回 None，文件可能已损坏")
        if image.size == 0:
            return ValidationResult(False, file_path, "图片像素为 0")

        h, w = image.shape[:2]
        if h == 0 or w == 0:
            return ValidationResult(False, file_path, f"无效的图片尺寸: {w}x{h}")

        return ValidationResult(True, file_path, "", w, h, fmt)

    def _check_magic(self, file_path: str) -> str | None:
        """读取文件头字节，匹配已知格式"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(12)
        except IOError:
            return None

        for magic, fmt in MAGIC_BYTES.items():
            if header.startswith(magic):
                # WebP 需要额外检查: RIFF .... WEBP
                if fmt == 'webp' and header[8:12] == b'WEBP':
                    return 'webp'
                elif fmt == 'webp':
                    continue  # RIFF 但不是 WEBP (可能是 AVI)
                return fmt

        # TIFF 和 WebP 可能匹配到 RIFF — 回退到扩展名
        ext = Path(file_path).suffix.lower()
        if ext in {'.tiff', '.tif'}:
            return 'tiff'
        if ext == '.webp':
            return 'webp'

        return None
