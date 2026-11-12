"""管理路由(写操作),全部依赖 verify_admin_token。

涵盖:歌曲上传/编辑/删除/替换音频/替换与清除封面,大类与子类的新建/编辑/删除,
大类合集封面。删除分类前校验「无歌曲」才允许(避免歌曲 category_id 悬空)。
封面与音频文件只能经各自的 /cover、/audio 上传接口写入 —— 上传名不采信、
目录由后端推导。
"""
from pathlib import Path
from typing import BinaryIO
import secrets
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_db, require_intranet, verify_admin_token
from ..models import Category, Favorite, Member, PlayHistory, Song, SubCategory
from ..schemas import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    MemberAdminCreate,
    MemberAdminOut,
    MemberOut,
    MemberPasswordReset,
    SongOut,
    SongUpdate,
    SubCategoryCreate,
    SubCategoryOut,
)
from ..security import hash_password
from ..services import storage
from ..services.meta import build_url, counts_by_node, song_to_out, sub_to_out
from .members import check_password, check_username, member_out

router = APIRouter(
    prefix="/api/admin",
    tags=["管理(需 token)"],
    # 顺序:先 IP 后 token —— 公网来源直接 403,不暴露 token 校验细节
    dependencies=[Depends(require_intranet), Depends(verify_admin_token)],
)


def _abs(rel_path: str) -> Path:
    """存储相对路径 → 绝对路径(用于文件读写)。"""
    return settings.library_dir.parent / rel_path


# 上传扩展名白名单:白名单外一律 400。
# 落盘目录经 StaticFiles 公开分发,放行 .html/.svg 等会构成存储型 XSS / 任意内容分发。
AUDIO_EXTS = {".mp3", ".m4a", ".flac", ".ogg", ".wav", ".aac"}
COVER_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
# 上传大小上限(流式写盘边写边计,超限拒绝),防超大请求打爆容器内存
MAX_AUDIO_BYTES = 100 * 1024 * 1024
MAX_COVER_BYTES = 5 * 1024 * 1024

# 大类封面的文件名主干。歌曲文件在 library/{category}/{sub_dir}/ 下,大类封面在
# 上一层的 library/{category}/ 下,层级不同故不会与任何 song_id 冲突。
CATEGORY_COVER_STEM = "_cover"

# ===== 成员账号管理 =====

# 自动生成密码的长度与字符集(去掉易混淆的 0/o/1/i/l,便于口口相传)
GEN_PASSWORD_LEN = 8
_GEN_ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz"


def _gen_password(n: int = GEN_PASSWORD_LEN) -> str:
    """生成可读随机密码(cryptographically secure,无易混淆字符)。"""
    return "".join(secrets.choice(_GEN_ALPHABET) for _ in range(n))


def _member_admin_out(member: Member, password: str) -> MemberAdminOut:
    base = member_out(member)
    return MemberAdminOut(
        id=base.id,
        name=base.name,
        username=base.username,
        avatar=base.avatar,
        created_at=base.created_at,
        password=password,
    )


@router.get("/members", response_model=list[MemberOut], summary="成员账号列表")
def admin_list_members(db: Session = Depends(get_db)) -> list[MemberOut]:
    rows = db.scalars(select(Member).order_by(Member.created_at, Member.id)).all()
    return [member_out(m) for m in rows]


@router.post(
    "/members",
    response_model=MemberAdminOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建成员账号(密码缺省时自动生成)",
)
def admin_create_member(body: MemberAdminCreate, db: Session = Depends(get_db)) -> MemberAdminOut:
    """开账号并下发凭证:响应里的明文密码只出现这一次,服务端只存散列。

    password 不传时自动生成 8 位无易混淆字符的密码,由管理员转交给使用者;
    name(昵称)不传时取登录账号,用户可在 App 内「账号管理」自行修改。
    """
    username = check_username(body.username)
    if db.scalar(select(Member).where(Member.username == username)):
        raise HTTPException(status.HTTP_409_CONFLICT, "该账号已被使用")
    # 昵称缺省取登录账号:后台只管开号,起名交给使用者本人
    name = (body.name or "").strip() or username
    password = check_password(body.password) if body.password is not None else _gen_password()

    member = Member(
        id=uuid.uuid4().hex,
        name=name[:64],
        username=username,
        password_hash=hash_password(password),
        avatar=body.avatar.strip()[:16],
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return _member_admin_out(member, password)


@router.put(
    "/members/{member_id}/password",
    response_model=MemberAdminOut,
    summary="重置账号密码(缺省时自动生成)",
)
def admin_reset_password(
    member_id: str, body: MemberPasswordReset, db: Session = Depends(get_db)
) -> MemberAdminOut:
    """重置后旧密码立即失效;新明文密码随本响应下发一次。"""
    member = db.get(Member, member_id)
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "成员不存在")
    password = check_password(body.password) if body.password is not None else _gen_password()
    member.password_hash = hash_password(password)
    db.commit()
    db.refresh(member)
    return _member_admin_out(member, password)


@router.delete(
    "/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除成员账号(其收藏/历史级联删除)",
)
def admin_delete_member(member_id: str, db: Session = Depends(get_db)) -> None:
    member = db.get(Member, member_id)
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "成员不存在")
    # 级联由数据库外键 ON DELETE CASCADE 完成(foreign_keys=ON),此处显式删兜底
    db.execute(delete(Favorite).where(Favorite.member_id == member_id))
    db.execute(delete(PlayHistory).where(PlayHistory.member_id == member_id))
    db.delete(member)
    db.commit()


def _save_upload(file_obj: BinaryIO, dest: Path, max_bytes: int, kind: str) -> None:
    """流式保存上传文件,大小/类型超限时 400(半成品文件由 write_upload 清理)。"""
    try:
        storage.write_upload(file_obj, dest, max_bytes, kind)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e


def _checked_ext(filename: str | None, whitelist: set[str], kind: str) -> str:
    """校验上传文件扩展名在白名单内,返回小写扩展名(含点)。"""
    ext = Path(filename or "").suffix.lower()
    if ext not in whitelist:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"{kind}文件类型不允许({ext or '无扩展名'}),仅支持:{'、'.join(sorted(whitelist))}",
        )
    return ext


def _song_count_in_sub(db: Session, sub_id: str) -> int:
    return db.scalar(select(func.count()).where(Song.sub_category_id == sub_id)) or 0


def _song_count_in_cat(db: Session, cat_id: str) -> int:
    return db.scalar(select(func.count()).where(Song.category_id == cat_id)) or 0


def _cat_out(db: Session, c: Category) -> CategoryOut:
    """单个大类的响应(含其子类与各级计数)。

    create / update / cover 三个写接口共用,避免各写一份组装逻辑而漂移。
    """
    subs = db.scalars(
        select(SubCategory)
        .where(SubCategory.category_id == c.id)
        .order_by(SubCategory.sort_order, SubCategory.id)
    ).all()
    # 计数一次 GROUP BY 取全量后按需取用,避免逐个子类 COUNT(N+1)
    sub_counts, _ = counts_by_node(db)
    return CategoryOut(
        id=c.id,
        name=c.name,
        icon=c.icon,
        desc=c.desc,
        cover=build_url(c.cover_path),
        song_count=sum(sub_counts.get(s.id, 0) for s in subs),
        subs=[sub_to_out(s, sub_counts.get(s.id, 0)) for s in subs],
    )


# ===== 歌曲 =====


@router.post("/songs", response_model=SongOut, summary="上传新歌曲")
def upload_song(
    db: Session = Depends(get_db),
    audio: UploadFile = File(..., description="音频文件"),
    cover: UploadFile | None = File(None, description="封面图(可选)"),
    id: str = Form(..., description="歌曲 id"),
    name: str = Form(...),
    artist: str = Form(...),
    album: str | None = Form(None),
    category_id: str = Form(..., description="大类 id"),
    sub_category_id: str = Form(..., description="子类 id"),
    lyric: str | None = Form(None, description="lrc 歌词文本"),
) -> SongOut:
    """multipart 上传:音频(必填)+ 可选封面 + 元数据字段。duration 自动读取。"""
    if not storage.valid_id(id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "id 非法:仅允许字母数字下划线短横")
    if db.get(Song, id):
        raise HTTPException(status.HTTP_409_CONFLICT, f"id 已存在:{id}")
    if not db.get(Category, category_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"大类不存在:{category_id}")
    if not db.get(SubCategory, sub_category_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"子类不存在:{sub_category_id}")

    dest_dir = storage.song_dir(category_id, sub_category_id)
    ext = _checked_ext(audio.filename, AUDIO_EXTS, "音频")
    audio_path = dest_dir / f"{id}{ext}"
    _save_upload(audio.file, audio_path, MAX_AUDIO_BYTES, "音频")

    cover_abs: Path | None = None
    if cover and cover.filename:
        cext = _checked_ext(cover.filename, COVER_EXTS, "封面")
        cover_abs = dest_dir / f"{id}{cext}"
        _save_upload(cover.file, cover_abs, MAX_COVER_BYTES, "封面")

    song = Song(
        id=id,
        name=name,
        artist=artist,
        album=album,
        category_id=category_id,
        sub_category_id=sub_category_id,
        duration=storage.read_duration(audio_path),
        lyric=lyric,
        audio_path=storage.to_rel(audio_path),
        cover_path=storage.to_rel(cover_abs) if cover_abs else None,
    )
    db.add(song)
    db.commit()
    db.refresh(song)
    return song_to_out(song)


@router.put("/songs/{song_id}", response_model=SongOut, summary="编辑歌曲元数据")
def update_song(song_id: str, body: SongUpdate, db: Session = Depends(get_db)) -> SongOut:
    """仅改元数据(不改文件);若换了分类/子类,文件保留原位。"""
    song = db.get(Song, song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "歌曲不存在")
    data = body.model_dump(exclude_unset=True)
    if "category_id" in data and data["category_id"] and not db.get(Category, data["category_id"]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "大类不存在")
    if "sub_category_id" in data and data["sub_category_id"] and not db.get(SubCategory, data["sub_category_id"]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "子类不存在")
    for key, value in data.items():
        setattr(song, key, value)
    db.commit()
    db.refresh(song)
    return song_to_out(song)


@router.post("/songs/{song_id}/audio", response_model=SongOut, summary="替换音频")
def replace_audio(
    song_id: str,
    audio: UploadFile = File(..., description="新音频文件"),
    db: Session = Depends(get_db),
) -> SongOut:
    """替换音频文件:落盘新文件、重读时长、删除旧文件。

    文件名策略:优先 {id}{ext};若恰好是当前音频路径(同扩展名替换,最常见
    情形)或已被占用,则改用 {id}-2{ext}、{id}-3{ext}… 找一个未占用的名字。
    之所以不原地覆盖:音频响应带 immutable 长缓存(见 main.py),同 URL 换
    内容会让老客户端最长 7 天拿不到新音频;换文件名即换 URL,缓存自然失效。
    旧文件名释放后,下次替换可复用(与 -2 交替),不会无限增长。

    注:App 端 detail 有会话级 LRU 缓存,正在使用的客户端可能仍指向已删旧文件
    (与删除歌曲的行为一致),重启后恢复。
    """
    song = db.get(Song, song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "歌曲不存在")
    dest_dir = storage.song_dir(song.category_id, song.sub_category_id)
    ext = _checked_ext(audio.filename, AUDIO_EXTS, "音频")
    old_abs = _abs(song.audio_path)
    cand = dest_dir / f"{song_id}{ext}"
    n = 2
    while cand == old_abs or cand.exists():
        cand = dest_dir / f"{song_id}-{n}{ext}"
        n += 1
    _save_upload(audio.file, cand, MAX_AUDIO_BYTES, "音频")
    song.audio_path = storage.to_rel(cand)
    song.duration = storage.read_duration(cand)
    db.commit()
    # 先提交 DB 再删旧文件:commit 失败时仅多一个孤儿新文件(可接受);
    # 反过来会出现 DB 指向已删文件、客户端 404 的更糟状态
    if old_abs and old_abs != cand:
        storage.safe_remove(old_abs)
    db.refresh(song)
    return song_to_out(song)


@router.delete("/songs/{song_id}/cover", response_model=SongOut, summary="清除封面")
def clear_cover(song_id: str, db: Session = Depends(get_db)) -> SongOut:
    """删除封面文件并清空 cover_path(无封面时为空操作)。"""
    song = db.get(Song, song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "歌曲不存在")
    if song.cover_path:
        storage.safe_remove(_abs(song.cover_path))
        song.cover_path = None
        db.commit()
    db.refresh(song)
    return song_to_out(song)


@router.delete("/songs/{song_id}", summary="删除歌曲(含文件)")
def delete_song(song_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    song = db.get(Song, song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "歌曲不存在")
    storage.safe_remove(_abs(song.audio_path))
    if song.cover_path:
        storage.safe_remove(_abs(song.cover_path))
    db.delete(song)
    db.commit()
    return {"deleted": song_id}


@router.post("/songs/{song_id}/cover", response_model=SongOut, summary="替换封面")
def replace_cover(
    song_id: str,
    cover: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> SongOut:
    song = db.get(Song, song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "歌曲不存在")
    dest_dir = storage.song_dir(song.category_id, song.sub_category_id)
    cext = _checked_ext(cover.filename, COVER_EXTS, "封面")
    cover_abs = dest_dir / f"{song_id}{cext}"
    old_abs = _abs(song.cover_path) if song.cover_path else None
    _save_upload(cover.file, cover_abs, MAX_COVER_BYTES, "封面")
    # 仅当扩展名变了才需要删旧文件。新旧路径相同时,旧文件已被本次写入覆盖,
    # 再删就会把刚上传的封面删掉 —— 而「同扩展名替换」恰恰是最常见的用法,
    # 会留下一个指向空文件的 cover_path(前端 404,且 missing=cover 查不出来)。
    if old_abs and old_abs != cover_abs:
        storage.safe_remove(old_abs)
    song.cover_path = storage.to_rel(cover_abs)
    db.commit()
    db.refresh(song)
    return song_to_out(song)


# ===== 大类 =====


@router.post("/categories", response_model=CategoryOut, summary="新增大类")
def create_category(body: CategoryCreate, db: Session = Depends(get_db)) -> CategoryOut:
    if db.get(Category, body.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "大类 id 已存在")
    c = Category(id=body.id, name=body.name, icon=body.icon, desc=body.desc)
    db.add(c)
    db.commit()
    db.refresh(c)
    return _cat_out(db, c)


@router.put("/categories/{cat_id}", response_model=CategoryOut, summary="编辑大类")
def update_category(cat_id: str, body: CategoryUpdate, db: Session = Depends(get_db)) -> CategoryOut:
    """仅改元数据。封面不在 CategoryUpdate 里,只能经 /cover 接口写。"""
    c = db.get(Category, cat_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "大类不存在")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(c, key, value)
    db.commit()
    db.refresh(c)
    return _cat_out(db, c)


@router.post("/categories/{cat_id}/cover", response_model=CategoryOut, summary="替换大类封面")
def replace_category_cover(
    cat_id: str,
    cover: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> CategoryOut:
    """设置/替换大类合集封面(如古诗 tab / 大类歌单头的大图)。

    与歌曲封面同规矩:落盘目录由后端按 cat_id 推导、文件名由后端生成(不采信
    上传名,防路径穿越),cover_path 只存相对路径。CategoryUpdate 不含 cover
    字段 —— 封面只能经本接口写入,手工改库会绕过扩展名与体积校验。
    """
    c = db.get(Category, cat_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "大类不存在")
    if not storage.valid_id(cat_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "大类 id 含非法字符,无法用于文件路径")
    cext = _checked_ext(cover.filename, COVER_EXTS, "封面")
    cover_abs = storage.category_dir(cat_id) / f"{CATEGORY_COVER_STEM}{cext}"
    old_abs = _abs(c.cover_path) if c.cover_path else None
    _save_upload(cover.file, cover_abs, MAX_COVER_BYTES, "封面")
    # 同扩展名时新旧路径相同,旧文件已被覆盖,删了会把刚传的封面删掉
    if old_abs and old_abs != cover_abs:
        storage.safe_remove(old_abs)
    c.cover_path = storage.to_rel(cover_abs)
    db.commit()
    db.refresh(c)
    return _cat_out(db, c)


@router.delete("/categories/{cat_id}", summary="删除大类(须无歌曲与子类)")
def delete_category(cat_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    c = db.get(Category, cat_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "大类不存在")
    if _song_count_in_cat(db, cat_id) > 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "该大类下仍有歌曲,请先迁移或删除")
    if db.scalar(select(func.count()).where(SubCategory.category_id == cat_id)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "该大类下仍有子类,请先删除子类")
    if c.cover_path:  # 大类封面文件不在子类目录下,不随 CASCADE 清理
        storage.safe_remove(_abs(c.cover_path))
    db.delete(c)
    db.commit()
    return {"deleted": cat_id}


# ===== 子类 =====


@router.post("/subs", response_model=SubCategoryOut, summary="新增子类")
def create_sub(body: SubCategoryCreate, db: Session = Depends(get_db)) -> SubCategoryOut:
    if not db.get(Category, body.category_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "大类不存在")
    if db.get(SubCategory, body.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "子类 id 已存在")
    s = SubCategory(
        id=body.id,
        category_id=body.category_id,
        name=body.name,
        icon=body.icon,
        desc=body.desc,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return sub_to_out(s)


@router.delete("/subs/{sub_id}", summary="删除子类(须无歌曲)")
def delete_sub(sub_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    s = db.get(SubCategory, sub_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "子类不存在")
    if _song_count_in_sub(db, sub_id) > 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "该子类下仍有歌曲,请先迁移或删除")
    db.delete(s)
    db.commit()
    return {"deleted": sub_id}
