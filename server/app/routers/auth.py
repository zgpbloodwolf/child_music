"""登录认证路由:登录 / 当前账号 / 自助修改资料与密码 / 自定义头像上传。

- 登录(POST /api/auth/login)**公开**:拿账号密码换令牌;账号一律由
  后台管理(POST /api/admin/members)或已登录用户创建,登录页不开放注册;
- 当前账号(GET /api/auth/me)需登录态,客户端启动时用它校验令牌是否仍有效;
- 自助修改(PUT /api/auth/profile、PUT /api/auth/password)只能改自己:
  昵称/头像/密码可改,登录账号(username)不开放自改(仍由管理员管理);
- 头像上传(POST /api/auth/avatar)落盘 storage/library/avatars/ 并即时生效。
"""
import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_db, require_member
from ..models import Member
from ..schemas import LoginIn, LoginOut, MemberOut, PasswordChange, ProfileUpdate
from ..security import hash_password, make_token, verify_password
from ..services import storage
from .members import check_password, member_out

router = APIRouter(prefix="/api/auth", tags=["认证"])

# 头像图约束:仅图片格式;2MB 对方形小图绰绰有余(前端选图时已取压缩档)
AVATAR_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
AVATAR_MAX_BYTES = 2 * 1024 * 1024


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


@router.put("/profile", response_model=MemberOut, summary="修改自己的资料(昵称/头像按需)")
def update_profile(
    body: ProfileUpdate,
    member: Member = Depends(require_member),
    db: Session = Depends(get_db),
) -> MemberOut:
    """App「账号管理」页自助修改;仅传谁改谁(头像即时生效、昵称走保存按钮)。

    合法性见 ProfileUpdate:昵称≤64、头像为预设 emoji(≤16)或 avatars 路径(≤255)。
    """
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "昵称不能为空")
        member.name = name[:64]
    if body.avatar is not None:
        member.avatar = body.avatar
    db.commit()
    db.refresh(member)
    return member_out(member)


@router.post("/avatar", response_model=MemberOut, summary="上传自定义头像(即时生效)")
def upload_avatar(
    file: UploadFile = File(..., description="头像图片(jpg/png/webp,≤2MB)"),
    member: Member = Depends(require_member),
    db: Session = Depends(get_db),
) -> MemberOut:
    """落盘 storage/library/avatars/ 并即时写入 member.avatar,随响应回读最新账号。

    - 文件名 {member_id}_{内容哈希前8}{ext}:换图即换名,天然破各端图片缓存;
    - 上传前清掉本账号旧头像,目录不随换头像次数增长(同图重传同名覆盖,幂等);
    - 经 /library 静态挂载公开分发(与歌曲封面同策略,头像不属敏感资源),
      白名单仅图片扩展名,杜绝 html/svg 等存储型 XSS 载体(见 admin.py 同款约束);
    - 2MB 上限内整读入内存再落盘(歌曲上传走流式是因其体积大,头像无需);
    - 极端情况:落盘成功但写库失败会留下未引用文件,无碍(下次上传同号清理)。
    """
    ext = Path(file.filename or "").suffix.lower()
    if ext not in AVATAR_EXTS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"头像格式不支持({ext or '无扩展名'}),仅支持 jpg/png/webp",
        )
    data = file.file.read(AVATAR_MAX_BYTES + 1)
    if len(data) > AVATAR_MAX_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "头像图片超过 2MB 上限")

    dest_dir = settings.library_dir / "avatars"
    dest = dest_dir / f"{member.id}_{hashlib.sha256(data).hexdigest()[:8]}{ext}"
    for old in dest_dir.glob(f"{member.id}_*"):
        if old != dest:
            storage.safe_remove(old)
    storage.write_bytes(data, dest)

    member.avatar = storage.to_rel(dest)
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
