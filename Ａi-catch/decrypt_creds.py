
import base64
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def decrypt_data(encrypted_data: str, secret_key: str) -> str:
    """解密加密的數據"""
    try:
        if not encrypted_data or not secret_key:
            return ""
            
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
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA512(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(secret_key.encode())
        
        # AES-256-GCM 解密
        aesgcm = AESGCM(key)
        decrypted = aesgcm.decrypt(iv, encrypted + auth_tag, None)
        
        return decrypted.decode('utf-8')
    except Exception as e:
        return f"Error: {e}"

# Credentials from .env
secret_key = "K@bm47g7117"
user_id_enc = "0Zw7wSf7lgmNAYqTTLjst7uTC5jBTQGdIJQoGIK+l2fI5JZrwNezqVAqg186KPsnmEvslh//46h6IMUHOmQ5+Arl3/7f0ZNN7sBMkEgDg9k/9Y5Z+ugFujpoP+69nuY+O/hY47kJEvjtDQ=="
password_enc = "q4UY/rPGXhG75f19BcyUuLgiIfbac91icyI0tiCdsYwZAxO24+fBGOdazQyp1tK5L3qGq9zdGxqg98qWvts95AaumlcmiylyvrLkRBzpE9NWhov3C3dhLdIQJNLIBCt1R7ahG7SQncglVg=="
cert_pass_enc = "F2jFNSdBwkymFW3hPwFc8J5b6YqN629IB3iyKbecwX9PrM0fKhWej7QQ/wEniTlvEN3/6MQDBu7OZflNvoxGfgT+/BTeOPXD9YoSz4m6BJ7Rpou9cxp5PkUmbqeHfsTABSIF+YEXCPVAFUY="

print("Fubon Credentials:")
print(f"User ID: {decrypt_data(user_id_enc, secret_key)}")
print(f"Password: {decrypt_data(password_enc, secret_key)}")
print(f"Cert Password: {decrypt_data(cert_pass_enc, secret_key)}")
