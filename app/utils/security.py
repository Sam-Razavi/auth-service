import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from app.config import get_settings

settings = get_settings()

_MAX_BCRYPT_LEN = 72  # bcrypt silently truncates at 72 bytes


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:_MAX_BCRYPT_LEN], bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode()[:_MAX_BCRYPT_LEN], hashed.encode())


def generate_raw_token() -> str:
    return secrets.token_hex(32)


def generate_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(subject: str, jti: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "jti": jti,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
