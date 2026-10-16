from pydantic_settings import BaseSettings
from typing import Optional
import os
from cryptography.fernet import Fernet
import base64
import hashlib

class Settings(BaseSettings):
    # Fubon API 設定
    use_fubon_api: bool = True
    fubon_user_id_encrypted: Optional[str] = None
    fubon_password_encrypted: Optional[str] = None
    fubon_cert_path: Optional[str] = None
    fubon_cert_password_encrypted: Optional[str] = None
    encryption_secret_key: Optional[str] = None
    
    # 服務設定
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # 忽略多餘的環境變數

settings = Settings()

def decrypt_data(encrypted_data: str, secret_key: str) -> str:
    """解密加密的數據"""
    try:
        if not encrypted_data or not secret_key:
            return ""
            
        # 使用與 Node.js 相同的解密邏輯
        import struct
        
        # Base64 解碼
        buffer = base64.b64decode(encrypted_data)
        
        # 提取各部分
        SALT_LENGTH = 64
        IV_LENGTH = 16
        TAG_LENGTH = 16
        
        salt = buffer[:SALT_LENGTH]
        iv = buffer[SALT_LENGTH:SALT_LENGTH + IV_LENGTH]
        auth_tag = buffer[SALT_LENGTH + IV_LENGTH:SALT_LENGTH + IV_LENGTH + TAG_LENGTH]
        encrypted = buffer[SALT_LENGTH + IV_LENGTH + TAG_LENGTH:]
        
        # 使用 PBKDF2 衍生密鑰
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.backends import default_backend
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA512(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(secret_key.encode())
        
        # AES-256-GCM 解密
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        aesgcm = AESGCM(key)
        decrypted = aesgcm.decrypt(iv, encrypted + auth_tag, None)
        
        return decrypted.decode('utf-8')
    except Exception as e:
        print(f"解密失敗: {e}")
        # 如果解密失敗，嘗試直接返回（可能是未加密的數據）
        return encrypted_data

def get_decrypted_credentials():
    """取得解密後的憑證"""
    if not settings.encryption_secret_key:
        print("警告: 未設定 ENCRYPTION_SECRET_KEY")
    
    user_id = decrypt_data(
        settings.fubon_user_id_encrypted, 
        settings.encryption_secret_key
    ) if settings.fubon_user_id_encrypted else None
    
    password = decrypt_data(
        settings.fubon_password_encrypted,
        settings.encryption_secret_key
    ) if settings.fubon_password_encrypted else None
    
    cert_password = decrypt_data(
        settings.fubon_cert_password_encrypted,
        settings.encryption_secret_key
    ) if settings.fubon_cert_password_encrypted else ""
    
    return {
        "user_id": user_id,
        "password": password,
        "cert_path": settings.fubon_cert_path,
        "cert_password": cert_password
    }
