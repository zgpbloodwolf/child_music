"""FastAPI 依赖:数据库会话(get_db)与管理接口鉴权(verify_admin_token)。"""
import secrets

from fastapi import Header, HTTPException, status

from .config import settings

# 复用 database.get_db 作为公开依赖(避免循环,直接 re-export)
from .database import get_db  # noqa: F401


def verify_admin_token(authorization: str = Header(default="", description="Bearer <ADMIN_TOKEN>")) -> None:
    """管理接口鉴权:校验 Authorization: Bearer <token>。

    用 secrets.compare_digest 防时序攻击;token 存 .env,传输加密由 cpolar HTTPS 保障。
    未配置默认 token(change-me)时拒绝,避免误上线裸奔。
    """
    expected = f"Bearer {settings.admin_token}"
    if settings.admin_token.startswith("change-me") or not secrets.compare_digest(
        authorization or "", expected
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未授权:token 无效")
