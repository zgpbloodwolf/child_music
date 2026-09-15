"""元数据业务:ORM → 响应模型转换、相对路径→完整公网 URL、分类树组装。

纯转换,不含 HTTP;路由层调用本模块产出 schemas。查询(过滤/搜索/分页)直接
在路由层用 ORM 表达,本模块只提供「拿到 ORM 后如何变成响应」。
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Category, Song, SubCategory
from ..schemas import CategoryOut, SongMetaOut, SongOut, SubCategoryOut


def build_url(rel_path: str | None) -> str:
    """相对 storage 根的路径(如 library/.../cn002.mp3)→ 完整公网 URL。

    空路径返回空串(封面文件可能不存在,前端用色块兜底)。
    """
    if not rel_path:
        return ""
    return f"{settings.public_base}/{rel_path.lstrip('/')}"


def song_to_meta(s: Song) -> SongMetaOut:
    """ORM Song → SongMetaOut(列表用,不含 src/lyric)。"""
    return SongMetaOut(
        id=s.id,
        name=s.name,
        artist=s.artist,
        album=s.album,
        cover=build_url(s.cover_path),
        duration=s.duration,
        category=s.category_id,
        sub_category=s.sub_category_id,
    )


def song_to_out(s: Song) -> SongOut:
    """ORM Song → SongOut(详情用,含完整 src/lyric)。"""
    return SongOut(
        id=s.id,
        name=s.name,
        artist=s.artist,
        album=s.album,
        cover=build_url(s.cover_path),
        duration=s.duration,
        category=s.category_id,
        sub_category=s.sub_category_id,
        src=build_url(s.audio_path),
        lyric=s.lyric,
    )


def sub_to_out(sub: SubCategory, song_count: int = 0) -> SubCategoryOut:
    return SubCategoryOut(
        id=sub.id, name=sub.name, icon=sub.icon, desc=sub.desc, song_count=song_count
    )


def count_songs(db: Session, category: str | None = None, sub: str | None = None) -> int:
    """按条件计数(单条 SELECT COUNT,走索引)。

    供「只需要一个数字」的场景使用,避免调用方为了计数把整张列表拉下来。
    """
    stmt = select(func.count()).select_from(Song)
    if category:
        stmt = stmt.where(Song.category_id == category)
    if sub:
        stmt = stmt.where(Song.sub_category_id == sub)
    return db.scalar(stmt) or 0


def counts_by_node(db: Session) -> tuple[dict[str, int], dict[str, int]]:
    """一次 GROUP BY 得到「子类→歌曲数」与「大类→歌曲数」。

    返回 (子类计数, 大类计数)。大类计数由子类计数求和得出,不需要第二趟查询。
    """
    rows = db.execute(
        select(Song.category_id, Song.sub_category_id, func.count()).group_by(
            Song.category_id, Song.sub_category_id
        )
    ).all()
    sub_counts: dict[str, int] = {}
    cat_counts: dict[str, int] = {}
    for cat_id, sub_id, n in rows:
        sub_counts[sub_id] = sub_counts.get(sub_id, 0) + n
        cat_counts[cat_id] = cat_counts.get(cat_id, 0) + n
    return sub_counts, cat_counts


def build_category_tree(db: Session) -> list[CategoryOut]:
    """组装完整分类树:大类 + 其下子类(含空大类) + 各级歌曲数。

    三次查询(大类、全部子类、一次计数聚合)后内存分组,避免逐个大类/子类
    单独查询(N+1)。songCount 随树下发后,前端统计条数不再需要请求歌曲列表。
    """
    cats = db.scalars(select(Category).order_by(Category.sort_order, Category.id)).all()
    all_subs = db.scalars(
        select(SubCategory).order_by(SubCategory.sort_order, SubCategory.id)
    ).all()
    sub_counts, cat_counts = counts_by_node(db)
    subs_by_cat: dict[str, list[SubCategory]] = {}
    for s in all_subs:
        subs_by_cat.setdefault(s.category_id, []).append(s)
    return [
        CategoryOut(
            id=c.id,
            name=c.name,
            icon=c.icon,
            desc=c.desc,
            song_count=cat_counts.get(c.id, 0),
            subs=[
                sub_to_out(s, sub_counts.get(s.id, 0))
                for s in subs_by_cat.get(c.id, [])
            ],
        )
        for c in cats
    ]
