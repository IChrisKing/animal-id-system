"""数据库操作层"""

import os
from datetime import datetime
from typing import Optional

import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.storage.models import Base, CatProfile, MediaSource, ProcessingLog


class Database:
    """SQLite 数据库管理 + CRUD 操作"""

    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

    # ── CatProfile CRUD ────────────────────────────────────

    def create_profile(
        self,
        profile_id: str,
        thumbnail_path: str,
        feature_vector: np.ndarray,
        description: str = "",
    ) -> CatProfile:
        with self.get_session() as session:
            profile = CatProfile(
                id=profile_id,
                thumbnail_path=thumbnail_path,
                feature_vector=feature_vector.astype(np.float32).tobytes(),
                description=description,
                first_seen=datetime.now(),
                last_seen=datetime.now(),
                appearance_count=1,
            )
            session.add(profile)
            session.commit()
            return profile

    def get_profile(self, profile_id: str) -> Optional[CatProfile]:
        with self.get_session() as session:
            return session.query(CatProfile).filter_by(id=profile_id).first()

    def list_profiles(self, limit: int = 50, offset: int = 0) -> list[CatProfile]:
        with self.get_session() as session:
            return (
                session.query(CatProfile)
                .order_by(CatProfile.last_seen.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )

    def count_profiles(self) -> int:
        with self.get_session() as session:
            return session.query(CatProfile).count()

    def update_profile_appearance(
        self,
        profile_id: str,
        description: str = "",
        feature_vector: np.ndarray | None = None,
        alpha: float = 0.3,
    ):
        """更新档案：增加出现次数，更新特征(EMA)，更新 last_seen"""
        with self.get_session() as session:
            profile = session.query(CatProfile).filter_by(id=profile_id).first()
            if profile is None:
                return
            profile.appearance_count += 1
            profile.last_seen = datetime.now()
            if description:
                profile.description = description
            if feature_vector is not None:
                # 指数移动平均更新特征
                old_feat = np.frombuffer(profile.feature_vector, dtype=np.float32)
                new_feat = alpha * feature_vector + (1 - alpha) * old_feat
                profile.feature_vector = new_feat.astype(np.float32).tobytes()
            session.commit()

    def delete_profile(self, profile_id: str) -> bool:
        with self.get_session() as session:
            profile = session.query(CatProfile).filter_by(id=profile_id).first()
            if profile is None:
                return False
            session.delete(profile)
            session.commit()
            return True

    # ── MediaSource ─────────────────────────────────────────

    def add_media_source(
        self,
        profile_id: str,
        source_type: str,
        file_name: str,
        file_path: str,
        file_size: int = 0,
        file_hash: str = "",
    ):
        with self.get_session() as session:
            source = MediaSource(
                profile_id=profile_id,
                source_type=source_type,
                file_name=file_name,
                file_path=file_path,
                file_size=file_size,
                file_hash=file_hash,
            )
            session.add(source)
            session.commit()

    def get_profile_sources(self, profile_id: str) -> list[MediaSource]:
        with self.get_session() as session:
            return (
                session.query(MediaSource)
                .filter_by(profile_id=profile_id)
                .order_by(MediaSource.added_at.desc())
                .all()
            )

    # ── 特征向量查询 (用于匹配) ─────────────────────────────

    def get_all_features(self) -> dict[str, np.ndarray]:
        """返回 {profile_id: feature_vector} 用于个体匹配"""
        with self.get_session() as session:
            profiles = session.query(CatProfile).all()
            return {
                p.id: np.frombuffer(p.feature_vector, dtype=np.float32)
                for p in profiles
                if p.feature_vector is not None
            }

    # ── ProcessingLog ───────────────────────────────────────

    def log_processing(
        self,
        file_path: str,
        file_type: str,
        status: str,
        error_message: str = "",
        profiles_found: int = 0,
        api_calls: int = 0,
    ):
        with self.get_session() as session:
            log = ProcessingLog(
                file_path=file_path,
                file_type=file_type,
                status=status,
                error_message=error_message,
                profiles_found=profiles_found,
                api_calls=api_calls,
            )
            session.add(log)
            session.commit()

    def get_processing_stats(self) -> dict:
        """获取处理统计"""
        with self.get_session() as session:
            total = session.query(ProcessingLog).count()
            success = (
                session.query(ProcessingLog).filter_by(status="success").count()
            )
            skipped = (
                session.query(ProcessingLog).filter_by(status="skipped").count()
            )
            errors = (
                session.query(ProcessingLog).filter_by(status="error").count()
            )
            return {
                "total_files_processed": total,
                "success": success,
                "skipped": skipped,
                "errors": errors,
            }
