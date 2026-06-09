"""SQLAlchemy ORM 模型"""

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    LargeBinary,
    DateTime,
    Text,
    ForeignKey,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class CatProfile(Base):
    """猫个体档案表"""
    __tablename__ = "cat_profiles"

    id = Column(String, primary_key=True)               # cat_a3f2b1c0
    nickname = Column(String, nullable=True)             # 用户自定义昵称
    description = Column(Text, nullable=True)            # API 返回的颜色/特征描述
    thumbnail_path = Column(String, nullable=False)      # 缩略图文件路径
    feature_vector = Column(LargeBinary, nullable=True)  # 特征向量 (numpy 序列化)
    first_seen = Column(DateTime, nullable=False, default=datetime.now)
    last_seen = Column(DateTime, nullable=False, default=datetime.now)
    appearance_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    sources = relationship("MediaSource", back_populates="profile", cascade="all, delete-orphan")


class MediaSource(Base):
    """媒体来源表"""
    __tablename__ = "media_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(String, ForeignKey("cat_profiles.id", ondelete="CASCADE"), nullable=False)
    source_type = Column(String, nullable=False)         # 'image' | 'video'
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)
    file_hash = Column(String, nullable=True)            # SHA-256
    added_at = Column(DateTime, default=datetime.now)

    profile = relationship("CatProfile", back_populates="sources")


class ProcessingLog(Base):
    """处理日志表"""
    __tablename__ = "processing_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)           # 'image' | 'video'
    status = Column(String, nullable=False)              # 'success' | 'skipped' | 'error'
    error_message = Column(Text, nullable=True)
    profiles_found = Column(Integer, default=0)
    api_calls = Column(Integer, default=0)
    processed_at = Column(DateTime, default=datetime.now)
