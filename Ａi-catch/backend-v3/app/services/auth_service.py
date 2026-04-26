"""
用戶認證服務
JWT Token 認證系統
"""

import os
import hashlib
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.database.connection import async_session

logger = logging.getLogger(__name__)

# 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "ai_stock_secret_key_2025_very_secure")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 小時


def get_password_hash(password: str) -> str:
    """取得密碼雜湊"""
    # 使用 sha256 預處理以避免 bcrypt 72 字節限制
    password_sha = hashlib.sha256(password.encode()).digest()
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_sha, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """驗證密碼"""
    # 使用 sha256 預處理
    password_sha = hashlib.sha256(plain_password.encode()).digest()
    return bcrypt.checkpw(password_sha, hashed_password.encode('utf-8'))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """創建 JWT Token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """解碼 JWT Token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.error(f"Token 解碼失敗: {e}")
        return None


class AuthService:
    """認證服務類"""
    
    @staticmethod
    async def register_user(username: str, password: str, email: str = None) -> Dict[str, Any]:
        """
        註冊新用戶
        """
        try:
            from app.models.user import User
            
            async with async_session() as session:
                # 檢查用戶名是否已存在
                result = await session.execute(
                    select(User).where(User.username == username)
                )
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    return {"success": False, "error": "用戶名已存在"}
                
                # 檢查 email 是否已存在
                if email:
                    result = await session.execute(
                        select(User).where(User.email == email)
                    )
                    existing_email = result.scalar_one_or_none()
                    if existing_email:
                        return {"success": False, "error": "Email 已被使用"}
                
                # 創建新用戶
                hashed_password = get_password_hash(password)
                new_user = User(
                    username=username,
                    email=email,
                    password_hash=hashed_password,
                    role="user",
                    is_active=True
                )
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)
                
                # 創建 Token
                access_token = create_access_token(
                    data={"sub": username, "user_id": new_user.id}
                )
                
                return {
                    "success": True,
                    "user": {
                        "id": new_user.id,
                        "username": new_user.username,
                        "email": new_user.email,
                        "role": new_user.role
                    },
                    "access_token": access_token,
                    "token_type": "bearer"
                }
                
        except Exception as e:
            logger.error(f"註冊失敗: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def login_user(username: str, password: str) -> Dict[str, Any]:
        """
        用戶登入
        """
        try:
            from app.models.user import User
            
            async with async_session() as session:
                # 查詢用戶
                result = await session.execute(
                    select(User).where(User.username == username)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    return {"success": False, "error": "用戶名或密碼錯誤"}
                
                if not user.is_active:
                    return {"success": False, "error": "帳號已停用"}
                
                # 驗證密碼
                if not verify_password(password, user.password_hash):
                    return {"success": False, "error": "用戶名或密碼錯誤"}
                
                # 更新最後登入時間
                user.last_login = datetime.utcnow()
                await session.commit()
                
                # 創建 Token
                access_token = create_access_token(
                    data={"sub": username, "user_id": user.id}
                )
                
                return {
                    "success": True,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "role": user.role
                    },
                    "access_token": access_token,
                    "token_type": "bearer"
                }
                
        except Exception as e:
            logger.error(f"登入失敗: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_current_user(token: str) -> Optional[Dict[str, Any]]:
        """
        根據 Token 獲取當前用戶（包含設定）
        """
        try:
            from app.models.user import User, UserSettings
            from sqlalchemy.orm import selectinload
            
            payload = decode_token(token)
            if not payload:
                return None
            
            username = payload.get("sub")
            if not username:
                return None
            
            async with async_session() as session:
                result = await session.execute(
                    select(User)
                    .options(selectinload(User.settings))
                    .where(User.username == username)
                )
                user = result.scalar_one_or_none()
                
                if not user or not user.is_active:
                    return None
                
                # 準備設定資料
                settings_data = {
                    "watchlist": [],
                    "alert_rules": {},
                    "notification_channels": {},
                    "theme": "light",
                    "language": "zh-TW"
                }
                
                if user.settings:
                    settings_data = {
                        "watchlist": user.settings.watchlist or [],
                        "alert_rules": user.settings.alert_rules or {},
                        "notification_channels": user.settings.notification_channels or {},
                        "theme": user.settings.theme or "light",
                        "language": user.settings.language or "zh-TW"
                    }
                
                return {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "settings": settings_data
                }
                
        except Exception as e:
            logger.error(f"獲取用戶失敗: {e}")
            return None
    
    @staticmethod
    async def update_user_settings(user_id: int, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新用戶設定
        """
        try:
            from app.models.user import UserSettings
            
            async with async_session() as session:
                # 查詢現有設定
                result = await session.execute(
                    select(UserSettings).where(UserSettings.user_id == user_id)
                )
                user_settings = result.scalar_one_or_none()
                
                if user_settings:
                    # 更新設定
                    if "watchlist" in settings:
                        user_settings.watchlist = settings["watchlist"]
                    if "alert_rules" in settings:
                        user_settings.alert_rules = settings["alert_rules"]
                    if "notification_channels" in settings:
                        user_settings.notification_channels = settings["notification_channels"]
                else:
                    # 創建新設定
                    user_settings = UserSettings(
                        user_id=user_id,
                        watchlist=settings.get("watchlist", []),
                        alert_rules=settings.get("alert_rules", {}),
                        notification_channels=settings.get("notification_channels", {})
                    )
                    session.add(user_settings)
                
                await session.commit()
                return {"success": True, "message": "設定已更新"}
                
        except Exception as e:
            logger.error(f"更新設定失敗: {e}")
            return {"success": False, "error": str(e)}


# 單例實例
auth_service = AuthService()
