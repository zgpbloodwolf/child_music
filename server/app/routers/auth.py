"""登录认证路由:登录 / 当前账号。

- 登录(POST /api/auth/login)**公开**:拿账号密码换令牌;账号一律由
  后台管理(POST /api/admin/members)或已登录用户创建,登录页不开放注册;
- 当前账号(GET /api/auth/me)需登录态,客户端启动时用它校验令牌是否仍有效。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_db, require_member
from ..models import Member
from ..schemas import LoginIn, LoginOut, MemberOut
from ..security import make_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=LoginOut, summary="账号密码登录")
def login(payload: LoginIn, db: Session = Depends(get_db)) -> LoginOut:
    """校验用户名 + 密码,签发无状态会话令牌(HMAC,见 app/security.py)。"""
    username = payload.username.strip().lower()
    member = db.scalar(select(Member).where(Member.username == username))
    if (
        not member
        or not member.password_hash
        or not verify_password(payload.password, member.password_hash)
    ):
        # 不区分「账号不存在/密码错误」,避免账号枚举
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号或密码错误")
    return LoginOut(
        token=make_token(member.id),
        member=MemberOut(
            id=member.id,
            name=member.name,
            username=member.username or "",
            avatar=member.avatar,
            created_at=member.created_at,
        ),
    )


@router.get("/me", response_model=MemberOut, summary="当前登录账号")
def me(member: Member = Depends(require_member)) -> MemberOut:
    """客户端启动时校验令牌并回读最新账号信息(改名/被删后据此处理)。"""
    return MemberOut(
        id=member.id,
        name=member.name,
        username=member.username or "",
        avatar=member.avatar,
        created_at=member.created_at,
    )
