"""登录认证路由:登录 / 当前账号 / 自助修改资料与密码。

- 登录(POST /api/auth/login)**公开**:拿账号密码换令牌;账号一律由
  后台管理(POST /api/admin/members)或已登录用户创建,登录页不开放注册;
- 当前账号(GET /api/auth/me)需登录态,客户端启动时用它校验令牌是否仍有效;
- 自助修改(PUT /api/auth/profile、PUT /api/auth/password)只能改自己:
  昵称/头像/密码可改,登录账号(username)不开放自改(仍由管理员管理)。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_db, require_member
from ..models import Member
from ..schemas import LoginIn, LoginOut, MemberOut, PasswordChange, ProfileUpdate
from ..security import hash_password, make_token, verify_password
from .members import check_password, member_out

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
    return member_out(member)


@router.put("/profile", response_model=MemberOut, summary="修改自己的资料(昵称/头像)")
def update_profile(
    body: ProfileUpdate,
    member: Member = Depends(require_member),
    db: Session = Depends(get_db),
) -> MemberOut:
    """App「账号管理」页自助修改;约束与后台创建一致(昵称≤64、头像≤16)。"""
    name = body.name.strip()
    if not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "昵称不能为空")
    member.name = name[:64]
    member.avatar = body.avatar.strip()[:16]
    db.commit()
    db.refresh(member)
    return member_out(member)


@router.put("/password", summary="修改自己的密码(需旧密码验证)")
def change_password(
    body: PasswordChange,
    member: Member = Depends(require_member),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    """旧密码验证失败返回 400(不用 401:客户端会把 401 当会话失效踢回登录页)。"""
    if not member.password_hash or not verify_password(
        body.old_password, member.password_hash
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "旧密码不正确")
    member.password_hash = hash_password(check_password(body.new_password))
    db.commit()
    return {"ok": True}
