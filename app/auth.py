import hashlib
import hmac
import os
import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session as DBSession

from app import models
from app.database import get_db

PBKDF2_ITERATIONS = 200000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(digest_hex)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return hmac.compare_digest(expected, actual)


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def get_current_user(
    authorization: str = Header(default=None), db: DBSession = Depends(get_db)
) -> models.User:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    token = authorization.removeprefix("Bearer ").strip()
    session = db.query(models.UserSession).filter(models.UserSession.token == token).first()
    if session is None:
        raise HTTPException(status_code=401, detail="Токен недействителен")
    user = db.get(models.User, session.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user
