"""成员维度的云端收藏/播放历史路由。

设计取舍:
- 账号管理(列表/创建/删除)**只在管理后台**:POST /api/admin/members 等
  (内网 + 管理员 token)。App 登录用户互相不可见、不可开号删号,本路由
  不提供任何账号管理接口 —— 曾经的 GET/POST /api/members 与
  DELETE /api/members/{id} 会把全部账号暴露给任意登录用户,已移除;
- 数据隔离:收藏/播放历史只能读写**登录者本人**的(路径 member_id 必须
  等于令牌里的账号),其他账号 403;
- 收藏与播放历史采用「客户端全量、服务端照单全收」的 PUT 替换 —— 客户端
  本就以完整 id 列表为数据源(src/store/library.ts、history.ts),每次变更
  整表回写即可,无需逐条事件接口;冲突为「最后写入者胜出」,家庭场景可忽略;
- 提交的 id 若在曲库中已不存在(如歌曲被删)会被静默忽略,不会因外键报 500。

member_out / check_username / check_password 供管理路由(admin.py)复用。
"""
import re
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..deps import get_db, require_member
from ..models import Favorite, Member, PlayHistory, Song
from ..schemas import MemberOut, SongIdsIn

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
