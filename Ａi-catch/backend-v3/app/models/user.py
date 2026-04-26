"""
User Models
用戶相關的數據模型
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Boolean, JSON, DateTime

from app.database.base import Base


class User(Base):
    """用戶表"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="user")  # admin/user
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # 關聯
    settings: Mapped[Optional["UserSettings"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.username}>"


class UserSettings(Base):
    """用戶設定表"""
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, index=True)
    
    # 監控清單（JSON 陣列）
    watchlist: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    
    # 警報規則（JSON 物件）
    alert_rules: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    
    # 通知渠道（LINE, Email 等）
    notification_channels: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    
    # 偏好設定
    theme: Mapped[str] = mapped_column(String(20), default="light")  # light/dark
    language: Mapped[str] = mapped_column(String(10), default="zh-TW")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    user: Mapped["User"] = relationship(back_populates="settings")

    def __repr__(self):
        return f"<UserSettings for user_id={self.user_id}>"
