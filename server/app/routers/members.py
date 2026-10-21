"""成员账号与云端收藏/播放历史路由。

设计取舍:
- 成员即账号:创建成员 = 开账号(用户名唯一 + PBKDF2 密码散列);
  **开号入口有二**:后台管理 POST /api/admin/members(无需登录态,走内网
  + 管理员 token,用于生成初始账号密码),以及已登录用户在 App 内互相开号
  (POST /api/members 必须携带登录态;登录页不再开放注册);
- 数据隔离:收藏/播放历史只能读写**登录者本人**的(路径 member_id 必须
  等于令牌里的账号),其他账号 403;
- 收藏与播放历史采用「客户端全量、服务端照单全收」的 PUT 替换 —— 客户端
  本就以完整 id 列表为数据源(src/store/library.ts、history.ts),每次变更
  整表回写即可,无需逐条事件接口;冲突为「最后写入者胜出」,家庭场景可忽略;
- 提交的 id 若在曲库中已不存在(如歌曲被删)会被静默忽略,不会因外键报 500。

⚠️ 路由顺序:静态前缀本体(GET/POST /api/members)必须声明在
/{member_id} 参数路由之前,否则 "members" 之外的段被误当参数。
"""
import re
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..deps import get_db, require_member
from ..models import Favorite, Member, PlayHistory, Song
from ..schemas import MemberCreate, MemberOut, SongIdsIn
from ..security import hash_password

router = APIRouter(prefix="/api/members", tags=["成员"])

# 播放历史服务端保留上限(客户端本就截断到 20,此处兜底防误传大数组)
HISTORY_MAX = 50
# 账号/密码约束:账号 2-24 位(字母/数字/下划线/连字符/中文),密码 4-64 位
USERNAME_RE = re.compile(r"^[\w\u4e00-\u9fff-]{2,24}$", re.UNICODE)
PASSWORD_MIN, PASSWORD_MAX = 4, 64


def member_out(m: Member) -> MemberOut:
    return MemberOut(
        id=m.id, name=m.name, username=m.username or "", avatar=m.avatar,
        created_at=m.created_at,
    )


def check_username(username: str) -> str:
    """校验并归一(小写)登录账号;不合法 400。后台创建与本路由共用。"""
    username = username.strip().lower()
    if not USERNAME_RE.fullmatch(username):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "账号需为 2-24 位字母/数字/下划线/连字符/中文",
        )
    return username


def check_password(password: str) -> str:
    """校验密码长度;不合法 400。后台创建/重置与本路由共用。"""
    if not (PASSWORD_MIN <= len(password) <= PASSWORD_MAX):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"密码长度需为 {PASSWORD_MIN}-{PASSWORD_MAX} 位"
        )
    return password


def _require_own(member_id: str, current: Member) -> None:
    """数据归属校验:只能操作自己的收藏/历史。"""
    if member_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "只能访问自己的数据")


def _existing_ids(db: Session, ids: list[str]) -> list[str]:
    """过滤掉曲库中已不存在的 id,保持客户端提交顺序(不去重亦可,客户端已去重)。"""
    if not ids:
        return []
    have = set(db.scalars(select(Song.id).where(Song.id.in_(ids))).all())
    return [i for i in ids if i in have]


@router.get("", response_model=list[MemberOut], summary="成员账号列表")
def list_members(
    db: Session = Depends(get_db), _current: Member = Depends(require_member)
) -> list[MemberOut]:
    """按创建时间返回全部成员账号(登录后的账号管理页用)。"""
    rows = db.scalars(select(Member).order_by(Member.created_at, Member.id)).all()
    return [member_out(m) for m in rows]


@router.post(
    "",
    response_model=MemberOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建成员账号(需已登录)",
)
def create_member(
    payload: MemberCreate,
    db: Session = Depends(get_db),
    _current: Member = Depends(require_member),
) -> MemberOut:
    """开新账号。必须携带有效登录态(初始账号由后台管理创建,见 POST /api/admin/members)。"""
    username = check_username(payload.username)
    password = check_password(payload.password)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "昵称不能为空")
    if db.scalar(select(Member).where(Member.username == username)):
        raise HTTPException(status.HTTP_409_CONFLICT, "该账号已被使用")

    member = Member(
        id=uuid.uuid4().hex,
        name=name[:64],
        username=username,
        password_hash=hash_password(password),
        avatar=payload.avatar.strip()[:16],
    )
    db.add(member)
    db.commit()
    return member_out(member)


@router.delete(
    "/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除成员账号(其收藏/历史级联删除)",
)
def delete_member(
    member_id: str,
    db: Session = Depends(get_db),
    current: Member = Depends(require_member),
) -> None:
    member = db.get(Member, member_id)
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "成员不存在")
    if member_id == current.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能删除当前登录的账号")
    # 未声明 ORM relationship,级联由数据库外键 ON DELETE CASCADE 完成(foreign_keys=ON)
    db.execute(delete(Favorite).where(Favorite.member_id == member_id))
    db.execute(delete(PlayHistory).where(PlayHistory.member_id == member_id))
    db.delete(member)
    db.commit()


@router.get("/{member_id}/favorites", response_model=list[str], summary="某成员的收藏 id 列表")
def get_favorites(
    member_id: str,
    db: Session = Depends(get_db),
    current: Member = Depends(require_member),
) -> list[str]:
    """返回收藏 id(按客户端收藏顺序)。对应前端 library store 的 likedIds。"""
    _require_own(member_id, current)
    rows = db.execute(
        select(Favorite.song_id)
        .where(Favorite.member_id == member_id)
        .order_by(Favorite.position)
    ).scalars().all()
    return list(rows)


@router.put("/{member_id}/favorites", response_model=list[str], summary="全量覆盖收藏")
def put_favorites(
    member_id: str,
    payload: SongIdsIn,
    db: Session = Depends(get_db),
    current: Member = Depends(require_member),
) -> list[str]:
    """以客户端提交的 songIds 全量替换该成员收藏(顺序即提交顺序)。"""
    _require_own(member_id, current)
    ids = _existing_ids(db, payload.song_ids)
    db.execute(delete(Favorite).where(Favorite.member_id == member_id))
    db.add_all(
        Favorite(member_id=member_id, song_id=sid, position=i)
        for i, sid in enumerate(ids)
    )
    db.commit()
    return ids


@router.get("/{member_id}/history", response_model=list[str], summary="某成员的播放历史 id 列表")
def get_history(
    member_id: str,
    db: Session = Depends(get_db),
    current: Member = Depends(require_member),
) -> list[str]:
    """返回播放历史 id(最新在前,最多 HISTORY_MAX 条)。对应前端 history store 的 ids。"""
    _require_own(member_id, current)
    rows = db.execute(
        select(PlayHistory.song_id)
        .where(PlayHistory.member_id == member_id)
        .order_by(PlayHistory.played_at.desc())
        .limit(HISTORY_MAX)
    ).scalars().all()
    return list(rows)


@router.put("/{member_id}/history", response_model=list[str], summary="全量覆盖播放历史")
def put_history(
    member_id: str,
    payload: SongIdsIn,
    db: Session = Depends(get_db),
    current: Member = Depends(require_member),
) -> list[str]:
    """以客户端提交的 songIds 全量替换该成员历史(提交顺序即「最新在前」)。"""
    _require_own(member_id, current)
    ids = _existing_ids(db, payload.song_ids)[:HISTORY_MAX]
    base = datetime.now()
    db.execute(delete(PlayHistory).where(PlayHistory.member_id == member_id))
    # played_at 依提交顺序递减,保证回读顺序与客户端一致(最新在前)
    db.add_all(
        PlayHistory(member_id=member_id, song_id=sid, played_at=base - timedelta(seconds=i))
        for i, sid in enumerate(ids)
    )
    db.commit()
    return ids
