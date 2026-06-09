"""猫档案管理器"""

import os
import uuid
from datetime import datetime

import cv2
import numpy as np

from src.recognition.api_classifier import ClassificationResult
from src.recognition.detector import RawDetection
from src.recognition.matcher import MatchResult
from src.storage.database import Database


class ProfileManager:
    """管理猫个体档案的创建、更新、查询、删除"""

    def __init__(self, db: Database, profiles_path: str, thumbnail_size: tuple = (300, 300)):
        self.db = db
        self.profiles_path = profiles_path
        self.thumbnail_size = thumbnail_size
        os.makedirs(profiles_path, exist_ok=True)

    def create_profile(
        self,
        detection: RawDetection,
        classification: ClassificationResult,
        feature: np.ndarray,
    ) -> str:
        """创建新猫档案，返回 profile_id"""
        profile_id = self._generate_id("cat")
        thumbnail_path = self._save_thumbnail(profile_id, detection.crop)

        description = f"{classification.color} | {classification.distinguishing_features}"

        self.db.create_profile(
            profile_id=profile_id,
            thumbnail_path=thumbnail_path,
            feature_vector=feature,
            description=description,
        )

        self._add_source(profile_id, detection)
        return profile_id

    def update_profile(
        self,
        profile_id: str,
        detection: RawDetection,
        classification: ClassificationResult,
        feature: np.ndarray,
    ):
        """更新已有猫档案"""
        description = f"{classification.color} | {classification.distinguishing_features}"

        # 检查是否需要更新缩略图（置信度更高时）
        profile = self.db.get_profile(profile_id)
        if profile and classification.confidence > 0.8:
            self._save_thumbnail(profile_id, detection.crop)

        self.db.update_profile_appearance(
            profile_id=profile_id,
            description=description,
            feature_vector=feature,
            alpha=0.3,
        )
        self._add_source(profile_id, detection)

    def get_profile(self, profile_id: str) -> dict | None:
        """获取档案详情"""
        profile = self.db.get_profile(profile_id)
        if profile is None:
            return None
        sources = self.db.get_profile_sources(profile_id)
        return {
            "id": profile.id,
            "nickname": profile.nickname,
            "description": profile.description,
            "thumbnail_path": profile.thumbnail_path,
            "first_seen": profile.first_seen.isoformat() if profile.first_seen else "",
            "last_seen": profile.last_seen.isoformat() if profile.last_seen else "",
            "appearance_count": profile.appearance_count,
            "sources": [
                {
                    "type": s.source_type,
                    "file_name": s.file_name,
                    "file_path": s.file_path,
                    "added_at": s.added_at.isoformat() if s.added_at else "",
                }
                for s in sources
            ],
        }

    def list_profiles(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """列出所有猫档案"""
        profiles = self.db.list_profiles(limit=limit, offset=offset)
        return [
            {
                "id": p.id,
                "nickname": p.nickname,
                "description": p.description,
                "first_seen": p.first_seen.isoformat() if p.first_seen else "",
                "last_seen": p.last_seen.isoformat() if p.last_seen else "",
                "appearance_count": p.appearance_count,
            }
            for p in profiles
        ]

    def count_profiles(self) -> int:
        return self.db.count_profiles()

    def delete_profile(self, profile_id: str) -> bool:
        profile = self.db.get_profile(profile_id)
        if profile and profile.thumbnail_path:
            try:
                os.remove(profile.thumbnail_path)
            except OSError:
                pass
        return self.db.delete_profile(profile_id)

    def get_all_features(self) -> dict[str, np.ndarray]:
        return self.db.get_all_features()

    # ── Private helpers ─────────────────────────────────────

    def _generate_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:8]}"

    def _save_thumbnail(self, profile_id: str, crop: np.ndarray) -> str:
        """保存缩略图，返回路径"""
        thumb = cv2.resize(crop, self.thumbnail_size, interpolation=cv2.INTER_AREA)
        path = os.path.join(self.profiles_path, f"{profile_id}.jpg")
        cv2.imwrite(path, thumb, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return path

    def _add_source(self, profile_id: str, detection: RawDetection):
        import os as _os
        file_name = _os.path.basename(detection.source_file)
        file_size = 0
        try:
            file_size = _os.path.getsize(detection.source_file)
        except OSError:
            pass

        self.db.add_media_source(
            profile_id=profile_id,
            source_type=detection.source_type,
            file_name=file_name,
            file_path=detection.source_file,
            file_size=file_size,
            file_hash=detection.crop_hash,
        )
