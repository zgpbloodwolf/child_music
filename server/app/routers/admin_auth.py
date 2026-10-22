"""管理员账号密码登录(管理页 /admin 用)。

账号密码配置在 .env(ADMIN_NAME/ADMIN_PASSWORD),应用启动时由
sync_admin_from_env 同步进 admin_users 表(散列存储);改密码 = 改 .env 重启,
换账号/换密码会重建记录(新 id)使所有旧会话立即失效。

与 admin.py 的关系:那边是业务管理接口,router 级挂「内网 + token」双依赖;
这边是登录前就要能调的认证接口,router 级只挂 require_intranet(先 IP 后
凭证的防线次序与 admin.py 保持一致),凭证校验在各端点内做。

端点:
- GET  /api/admin/session  会话状态探测(前端启动时调用,永不 401)
- POST /api/admin/login    账号密码登录,签发 7 天会话令牌

静态 ADMIN_TOKEN 通道不受影响:运维脚本继续用它调 /api/admin/*(deps.verify_admin_token)。
"""
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_db, require_intranet
from ..models import AdminUser
from ..schemas import AdminLoginIn, AdminLoginOut, AdminSessionOut
from ..security import (
    hash_password,
    make_admin_token,
    parse_admin_token,
    secret_ready,
    verify_password,
)

router = APIRouter(
    prefix="/api/admin",
    tags=["管理登录"],
    # 只挂内网白名单不挂 token:登录接口本身不可能要求「已登录」
    dependencies=[Depends(require_intranet)],
)

# 管理员密码强度:比会员(4 位)严——管理员握着全库写权限
ADMIN_PASSWORD_MIN = 8


def sync_admin_from_env(db: Session) -> None:
    """把 .env 的 ADMIN_NAME/ADMIN_PASSWORD 同步进 admin_users 表(启动时调用)。

    规则(单管理员,表里最多一行,.env 是唯一事实来源):
    - 表中账号与 .env 一致(用户名相同且密码校验通过)→ 不动,保 id 保会话;
    - 表空 / 换账号 / 换密码 → 清表重建(新 id → 所有旧会话立即失效);
    - .env 未配全 → 不动表,打印警告(账号密码登录不可用,静态 token 通道不受影响)。
    """
    name = settings.admin_name.strip().lower()
    password = settings.admin_password
    if not name or not password:
        print("[admin] 警告:未配置 ADMIN_NAME/ADMIN_PASSWORD,管理页账号密码登录不可用")
        return
    if len(password) < ADMIN_PASSWORD_MIN:
        print(f"[admin] 警告:ADMIN_PASSWORD 少于 {ADMIN_PASSWORD_MIN} 位,建议加强")
    row = db.scalar(select(AdminUser).limit(1))
    if row is not None and row.username == name and verify_password(password, row.password_hash):
        return  # 与 .env 一致,无需重建
    db.query(AdminUser).delete()
    db.add(
        AdminUser(
            id=uuid.uuid4().hex,
            username=name,
            password_hash=hash_password(password),
            pwd_version=0,
        )
    )
    db.commit()
    print(f"[admin] 已从 .env 同步管理员账号「{name}」(旧登录会话已全部失效)")


@router.get("/session", response_model=AdminSessionOut, summary="管理员会话状态探测")
def admin_session(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> AdminSessionOut:
    """前端启动时探测:管理员是否已配置、当前携带的凭证是否有效。

    永不 401(未携带/无效凭证就是 authed=false),避免前端启动探测
    触发 401 统一拦截又弹回登录页的死循环。
    """
    initialized = db.scalar(select(AdminUser).limit(1)) is not None
    out = AdminSessionOut(initialized=initialized)
    if authorization.startswith("Bearer ") and initialized:
        parsed = parse_admin_token(authorization[len("Bearer "):])
        if parsed:
            row = db.get(AdminUser, parsed[0])
            if row is not None and row.pwd_version == parsed[1]:
                out.authed, out.username = True, row.username
    return out


@router.post("/login", response_model=AdminLoginOut, summary="管理员账号密码登录")
def admin_login(body: AdminLoginIn, db: Session = Depends(get_db)) -> AdminLoginOut:
    """校验账号密码,签发 7 天会话令牌(账号由启动同步保证与 .env 一致)。"""
    if not secret_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="服务端未配置 AUTH_SECRET(或仍在使用默认 ADMIN_TOKEN),无法签发管理员会话",
        )
    row = db.scalar(select(AdminUser).limit(1))
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="服务端未配置 ADMIN_NAME/ADMIN_PASSWORD,账号密码登录不可用",
        )
    username = body.username.strip().lower()
    # 不区分账号不存在/密码错误,防账号枚举(与会员登录一致)
    if username != row.username or not verify_password(body.password, row.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号或密码错误")
    return AdminLoginOut(token=make_admin_token(row.id, row.pwd_version), username=row.username)
