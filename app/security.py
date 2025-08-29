import secrets
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Tuple

from fastapi import HTTPException, Depends, Header, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import APIKey
from databse import get_db

def hash_secret(secret: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(secret.encode('utf-8'), salt).decode('utf-8')

def verify_secret(plain_secret: str, hashed_secret: str) -> bool:
    return bcrypt.checkpw(plain_secret.encode('utf-8'), hashed_secret.encode('utf-8'))


def generate_api_key() -> Tuple[str, str, str]:
    public_id = f"akp_{secrets.token_urlsafe(16)}"
    secret = secrets.token_urlsafe(32)
    full_key = f"{public_id}.{secret}"
    return full_key, public_id, secret

async def create_api_key(
    db: AsyncSession,
    user_id: str,
    requests_per_minute: int = 100,
    expires_days: int = 30
) -> str:
    full_key, public_id, secret = generate_api_key()
    hashed_key = hash_secret(secret)

    expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days) if expires_days else None

    db_key = APIKey(
        user_id=user_id,
        public_id=public_id,
        hashed_secret=hashed_key,
        requests_per_minute_limit=requests_per_minute,
        expires_at=expires_at
    )

    db.add(db_key)
    await db.commit()
    await db.refresh(db_key)

    return full_key

async def authenticate_api_key(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
) -> APIKey:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authorization header")

    api_key_str = authorization[7:]

    try:
        public_id, plain_secret = api_key_str.split('.')
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key format")

    query = select(APIKey).where(APIKey.public_id == public_id)
    result = await db.execute(query)
    db_key = result.scalars().one_or_none()

    if not db_key or not db_key.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    if db_key.expires_at and db_key.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key has expired")

    if not verify_secret(plain_secret, db_key.hashed_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    return db_key