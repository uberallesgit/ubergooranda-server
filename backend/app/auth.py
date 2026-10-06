import os
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, Header

pwd = CryptContext(schemes=["bcrypt"])
SECRET = os.getenv("JWT_SECRET")
ALGO = "HS256"


def make_token(user_id: int, role: str) -> str:
    return jwt.encode(
        {"sub": str(user_id), "role": role,
         "exp": datetime.utcnow() + timedelta(days=30)},
        SECRET, algorithm=ALGO,
    )


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET, algorithms=[ALGO])


async def current_user(authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        return decode_token(token)
    except JWTError:
        raise HTTPException(401, "invalid token")


def require_admin(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "admin only")
    return user
