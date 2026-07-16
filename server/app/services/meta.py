"""元数据业务:ORM → 响应模型转换、相对路径→完整公网 URL、分类树组装。

纯转换,不含 HTTP;路由层调用本模块产出 schemas。查询(过滤/搜索/分页)直接
在路由层用 ORM 表达,本模块只提供「拿到 ORM 后如何变成响应」。
"""
from sqlalchemy import select
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


def sub_to_out(sub: SubCategory) -> SubCategoryOut:
    return SubCategoryOut(id=sub.id, name=sub.name, icon=sub.icon, desc=sub.desc)


def build_category_tree(db: Session) -> list[CategoryOut]:
    """组装完整分类树:大类 + 其下子类(含空大类)。"""
    cats = db.scalars(select(Category).order_by(Category.sort_order, Category.id)).all()
    result: list[CategoryOut] = []
    for c in cats:
        subs = db.scalars(
            select(SubCategory)
            .where(SubCategory.category_id == c.id)
            .order_by(SubCategory.sort_order, SubCategory.id)
        ).all()
        result.append(
            CategoryOut(
                id=c.id,
                name=c.name,
                icon=c.icon,
                desc=c.desc,
                subs=[sub_to_out(s) for s in subs],
            )
        )
    return result
