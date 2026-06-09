"""流水线编排器 — 混合架构图片处理"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field

import cv2

from src.input_module import MediaScanner, ImageValidator, read_image
from src.recognition import (
    AnimalDetector,
    APIClassifier,
    ClassificationResult,
    FallbackClassifier,
    FeatureExtractor,
    IndividualMatcher,
    MatchResult,
    RawDetection,
)
from src.recognition.api_classifier import APIClassificationError
from src.archive.profile_manager import ProfileManager
from src.storage.database import Database
from src.utils.config import Config
from src.utils.logger import setup_logger

logger = logging.getLogger(__name__)


@dataclass
class PipelineReport:
    total_files: int = 0
    processed: int = 0
    skipped: int = 0
    errors: int = 0
    new_profiles: int = 0
    updated_profiles: int = 0
    no_animal: int = 0
    api_calls: int = 0
    api_cache_hits: int = 0
    elapsed_seconds: float = 0.0
    details: list[dict] = field(default_factory=list)


class Pipeline:
    """图片处理流水线 — 协调所有模块"""

    def __init__(self, config: Config):
        self.config = config

        # 输入
        self.scanner = MediaScanner(
            recursive=getattr(config.input, 'recursive', True),
        )
        self.validator = ImageValidator()

        # 识别
        detector_cfg = config.models.detector
        self.detector = AnimalDetector(
            model_path=detector_cfg.path,
            confidence_threshold=detector_cfg.get("confidence_threshold", 0.25),
            iou_threshold=detector_cfg.get("iou_threshold", 0.45),
        )

        api_cfg = config.api
        self.api_classifier = APIClassifier(
            provider=api_cfg.get("provider", "deepseek"),
            api_key=api_cfg.get("api_key", ""),
            base_url=api_cfg.get("base_url", ""),
            model=api_cfg.get("model", "deepseek-chat"),
            timeout=api_cfg.get("timeout", 10),
            max_retries=api_cfg.get("max_retries", 3),
            temperature=api_cfg.get("temperature", 0.1),
        )
        self.fallback_classifier = FallbackClassifier()

        fe_cfg = config.models.feature_extractor
        self.feature_extractor = FeatureExtractor(
            model_path=fe_cfg.path,
        )
        self.matcher = IndividualMatcher()

        # 存储
        storage_cfg = config.storage
        self.db = Database(storage_cfg.database_path)
        self.profile_manager = ProfileManager(
            db=self.db,
            profiles_path=storage_cfg.profiles_path,
            thumbnail_size=tuple(storage_cfg.get("thumbnail_size", [300, 300])),
        )

    def run(self, paths: list[str]) -> PipelineReport:
        """主入口：扫描并处理图片"""
        start_time = time.time()
        report = PipelineReport()

        # 1. 扫描
        scan_result = self.scanner.scan(paths)
        images = scan_result.images
        report.total_files = len(images) + len(scan_result.skipped)
        report.skipped = len(scan_result.skipped)

        logger.info(f"扫描完成: {len(images)} 张图片, {len(scan_result.skipped)} 跳过")

        # 2. 逐张处理
        for i, img_path in enumerate(images):
            logger.info(f"[{i+1}/{len(images)}] 处理: {img_path}")
            try:
                result = self._process_image(img_path)
                report.processed += 1

                if result.get("detections") == 0:
                    report.no_animal += 1

                for profile_id, is_new in result.get("profiles", []):
                    if is_new:
                        report.new_profiles += 1
                    else:
                        report.updated_profiles += 1

                report.details.append({
                    "file": img_path,
                    "status": "success",
                    **result,
                })

                self.db.log_processing(
                    file_path=img_path,
                    file_type="image",
                    status="success",
                    profiles_found=result.get("cat_count", 0),
                    api_calls=result.get("api_calls", 0),
                )

            except Exception as e:
                report.errors += 1
                logger.error(f"处理失败: {img_path}: {e}", exc_info=True)
                report.details.append({
                    "file": img_path,
                    "status": "error",
                    "error": str(e),
                })
                self.db.log_processing(
                    file_path=img_path,
                    file_type="image",
                    status="error",
                    error_message=str(e),
                )

            # 跳过项记录
            for skip in scan_result.skipped:
                self.db.log_processing(
                    file_path=skip.file_path,
                    file_type="image",
                    status="skipped",
                    error_message=skip.reason,
                )

        report.api_calls = self.api_classifier.api_calls
        report.api_cache_hits = self.api_classifier.cache_hits
        report.elapsed_seconds = round(time.time() - start_time, 1)

        logger.info(
            f"处理完成: {report.processed} 成功, {report.skipped} 跳过, "
            f"{report.errors} 错误, {report.new_profiles} 新猫, "
            f"{report.updated_profiles} 已有猫, "
            f"API 调用 {report.api_calls} 次 (缓存命中 {report.api_cache_hits}), "
            f"耗时 {report.elapsed_seconds}s"
        )

        return report

    def _process_image(self, img_path: str) -> dict:
        """处理单张图片"""
        # 1. 验证
        val = self.validator.validate(img_path)
        if not val.valid:
            return {"detections": 0, "cat_count": 0, "profiles": [], "error": val.error}

        # 2. 读取
        image = read_image(img_path)

        # 3. YOLO 检测
        detections = self.detector.detect(image, source_file=img_path)

        if not detections:
            return {"detections": 0, "cat_count": 0, "profiles": [], "api_calls": 0}

        # 4. API 分类 + 特征提取 + 匹配
        api_calls = 0
        cat_count = 0
        profiles = []

        for det in detections:
            # 4a. 分类 (API 主 + Fallback 备)
            try:
                classification = self.api_classifier.classify_sync(
                    det.crop_base64, det.crop_hash
                )
            except APIClassificationError as e:
                logger.warning(f"API 分类失败，降级: {e}")
                classification = self.fallback_classifier.classify(
                    det.yolo_class_id, det.yolo_confidence
                )

            if classification.class_name == "other":
                continue

            # 4b. 仅猫走个体匹配
            if classification.class_name == "cat":
                cat_count += 1

                # 特征提取
                feature = self.feature_extractor.extract(det.crop)

                # 个体匹配
                known_features = self.profile_manager.get_all_features()
                match = self.matcher.match(feature, classification, known_features)

                # 建档
                if match.is_new:
                    profile_id = self.profile_manager.create_profile(
                        det, classification, feature
                    )
                    logger.info(f"  🐱 新猫! ID={profile_id} ({classification.color})")
                else:
                    self.profile_manager.update_profile(
                        match.profile_id, det, classification, feature
                    )
                    profile_id = match.profile_id
                    logger.info(
                        f"  🐱 已有猫 {profile_id} "
                        f"(sim={match.similarity:.3f})"
                    )

                profiles.append((profile_id, match.is_new))

            # 黄鼠狼/鸟: Phase 2 处理

        return {
            "detections": len(detections),
            "cat_count": cat_count,
            "profiles": profiles,
            "api_calls": len(detections),
        }
