"""文件扫描器 — 递归扫描图片文件"""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SkipRecord:
    file_path: str
    reason: str


@dataclass
class ScanResult:
    images: list[str] = field(default_factory=list)
    skipped: list[SkipRecord] = field(default_factory=list)

    @property
    def total_found(self) -> int:
        return len(self.images) + len(self.skipped)


class MediaScanner:
    SUPPORTED_IMAGES = {
        '.jpg', '.jpeg', '.jpe', '.jfif',
        '.png', '.bmp', '.dib',
        '.tiff', '.tif', '.webp', '.gif',
    }
    SUPPORTED_VIDEOS = {
        '.mp4', '.m4v', '.avi', '.mov', '.qt',
        '.mkv', '.wmv', '.flv',
    }
    MAX_FILE_SIZE = 4 * 1024 * 1024 * 1024  # 4 GB

    def __init__(self, recursive: bool = True, max_file_size: int | None = None):
        self.recursive = recursive
        self.max_size = max_file_size or self.MAX_FILE_SIZE

    def scan(self, paths: list[str]) -> ScanResult:
        result = ScanResult()

        for raw_path in paths:
            path = os.path.abspath(raw_path)
            if not os.path.exists(path):
                result.skipped.append(SkipRecord(path, "文件不存在"))
                continue

            if os.path.isfile(path):
                self._classify_file(path, result)
            elif os.path.isdir(path):
                self._scan_dir(path, result)
            else:
                result.skipped.append(SkipRecord(path, "不是文件或目录"))

        return result

    def _scan_dir(self, dir_path: str, result: ScanResult):
        if self.recursive:
            for root, dirs, files in os.walk(dir_path):
                # 跳过隐藏目录
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for fname in files:
                    self._classify_file(os.path.join(root, fname), result)
        else:
            for fname in os.listdir(dir_path):
                fpath = os.path.join(dir_path, fname)
                if os.path.isfile(fpath):
                    self._classify_file(fpath, result)

    def _classify_file(self, file_path: str, result: ScanResult):
        ext = Path(file_path).suffix.lower()

        if ext in self.SUPPORTED_IMAGES:
            # 检查文件大小
            try:
                size = os.path.getsize(file_path)
                if size == 0:
                    result.skipped.append(SkipRecord(file_path, "文件大小为 0"))
                    return
                if size > self.max_size:
                    result.skipped.append(
                        SkipRecord(file_path, f"文件过大 ({size / 1e9:.1f} GB > {self.max_size / 1e9:.0f} GB)")
                    )
                    return
            except OSError as e:
                result.skipped.append(SkipRecord(file_path, f"无法读取文件: {e}"))
                return
            result.images.append(file_path)
        elif ext in self.SUPPORTED_VIDEOS:
            # Phase 1 不处理视频
            result.skipped.append(SkipRecord(file_path, "视频文件 (Phase 2 支持)"))
        else:
            result.skipped.append(SkipRecord(file_path, f"不支持的格式: {ext}"))
