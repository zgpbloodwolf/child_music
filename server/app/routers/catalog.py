"""元数据查询路由(只读),对齐前端 SongRepository 全部方法。

列表/搜索类返回 SongMetaOut(不含 src/lyric);get_detail 返回完整 SongOut。
统一的 /api/songs 用查询参数覆盖 listAll/listByCategory/listBySub/search/listByIds。

统计类数据(分类各级歌曲数、按作者聚合作品数)直接挂在对应接口的响应里
(songCount / /api/authors),调用方无需为了算一个数字把整张列表拉下来。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import Song, SubCategory
from ..schemas import (
    AuthorOut,
    CategoryOut,
    PageResult,
    SongMetaOut,
    SongOut,
    SubCategoryOut,
)
from ..services.meta import (
    build_category_tree,
    count_songs,
    song_to_meta,
    song_to_out,
    sub_to_out,
)

router = APIRouter(prefix="/api", tags=["曲库查询"])


@router.get("/categories", response_model=list[CategoryOut], summary="完整分类树")
def get_categories(db: Session = Depends(get_db)) -> list[CategoryOut]:
    """对应 Repository.getCategories():大类 + 其下子类(含空大类) + 各级 songCount。"""
    return build_category_tree(db)


@router.get("/authors", response_model=list[AuthorOut], summary="按作者聚合统计")
def list_authors(
    db: Session = Depends(get_db),
    category: str | None = Query(None, description="限定大类 id"),
    sub: str | None = Query(None, description="限定子类 id"),
) -> list[AuthorOut]:
    """对应 Repository.listAuthors():按 artist 分组返回作品数与涉及子类。

    一次 GROUP BY(artist, sub_category_id):组内条数求和即作者作品数,组本身即
    该作者涉及的子类集合(前端据此推断朝代),一趟查询同时满足两个用途。
    按作品数倒序、同名按名称排序,与前端原内存聚合口径一致。
    """
    stmt = select(
        Song.artist, Song.sub_category_id, func.count(), func.min(Song.sort_order)
    ).group_by(Song.artist, Song.sub_category_id)
    stmt = _apply_filters(stmt, category, sub, None)
    # 排序:先按作者、再按最早录入位置,保证每个作者的 subs 顺序稳定
    stmt = stmt.order_by(Song.artist, func.min(Song.sort_order), Song.sub_category_id)

    agg: dict[str, AuthorOut] = {}
    for artist, sub_id, n, _ in db.execute(stmt).all():
        entry = agg.get(artist)
        if entry is None:
            agg[artist] = AuthorOut(name=artist, count=n, subs=[sub_id])
        else:
            entry.count += n
            if sub_id not in entry.subs:
                entry.subs.append(sub_id)
    return sorted(agg.values(), key=lambda a: (-a.count, a.name))


@router.get("/subs/{sub_id}", response_model=SubCategoryOut | None, summary="按 id 查子类")
def find_sub(sub_id: str, db: Session = Depends(get_db)) -> SubCategoryOut | None:
    """对应 Repository.findSub():不存在返回 null。附带该子类歌曲数。"""
    sub = db.get(SubCategory, sub_id)
    if not sub:
        return None
    return sub_to_out(sub, count_songs(db, sub=sub_id))


@router.get("/subs/{sub_id}/category", summary="子类所属大类 id")
def category_id_of_sub(sub_id: str, db: Session = Depends(get_db)) -> dict[str, str | None]:
    """对应 Repository.categoryIdOfSub():返回 {categoryId},无匹配为 null。"""
    sub = db.get(SubCategory, sub_id)
    return {"categoryId": sub.category_id if sub else None}


@router.get("/songs/ids", response_model=list[str], summary="歌曲 id 列表(仅 id)")
def list_song_ids(
    db: Session = Depends(get_db),
    category: str | None = Query(None, description="大类 id"),
    sub: str | None = Query(None, description="子类 id"),
    keyword: str | None = Query(None, description="搜索关键词"),
    author: str | None = Query(None, description="作者(精确匹配)"),
) -> list[str]:
    """只返回 id 数组(不带元数据),对应 Repository.listIds()。

    调用方需要的是「完整且有序的 id 队列」(播放入队、总数展示),而列表内容另有
    分页接口负责。只取 id 时响应体约为带元数据的 1/10,且不必在客户端解析成对象。

    ⚠️ 路由顺序:/songs/ids 必须声明在 /songs/{song_id} 之前,否则会被后者
    当作 song_id="ids" 抢先匹配(返回 404)。
    """
    stmt = _apply_filters(select(Song.id), category, sub, keyword, author)
    return list(db.scalars(stmt.order_by(Song.sort_order, Song.id)).all())


@router.get("/songs/{song_id}", response_model=SongOut, summary="歌曲详情")
def get_song(song_id: str, db: Session = Depends(get_db)) -> SongOut:
    """对应 Repository.getDetail():返回完整 Song(含 src/lyric)。"""
    song = db.get(Song, song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "歌曲不存在")
    return song_to_out(song)


def _apply_filters(
    stmt,
    category: str | None,
    sub: str | None,
    keyword: str | None,
    author: str | None = None,
):
    """叠加 category/sub/author 过滤与 keyword 搜索(name/artist/album 包含)。"""
    if category:
        stmt = stmt.where(Song.category_id == category)
    if sub:
        stmt = stmt.where(Song.sub_category_id == sub)
    if author:
        stmt = stmt.where(Song.artist == author)
    if keyword:
        kw = f"%{keyword}%"
        # SQLite 的 LIKE 默认大小写不敏感(ASCII),中文无大小写问题
        stmt = stmt.where(
            Song.name.like(kw) | Song.artist.like(kw) | Song.album.like(kw)
        )
    return stmt


@router.get(
    "/songs",
    summary="歌曲列表/搜索/分页(统一查询)",
    response_model=list[SongMetaOut] | PageResult[SongMetaOut],
)
def list_songs(
    db: Session = Depends(get_db),
    category: str | None = Query(None, description="大类 id"),
    sub: str | None = Query(None, description="子类 id"),
    keyword: str | None = Query(None, description="搜索关键词"),
    author: str | None = Query(None, description="作者(精确匹配)"),
    ids: str | None = Query(None, description="逗号分隔的 id 列表"),
    page: int | None = Query(None, ge=1, description="页码(与 size 同时传则分页)"),
    size: int | None = Query(None, ge=1, le=500, description="每页条数"),
) -> list[SongMetaOut] | PageResult[SongMetaOut]:
    """对应 listAll/listByCategory/listBySub/listByAuthor/search/listByIds/listPage。

    优先级:ids > (keyword/author/category/sub 组合) > 全部。
    带 page+size 返回 PageResult(items/total/page/pageSize),否则返回裸数组。
    ids 模式按传入顺序排序(对齐 Repository.listByIds 的顺序敏感场景)。
    只要条数时用 page=1&size=1 读 total,不必拉列表。
    """
    if ids:
        id_list = [i.strip() for i in ids.split(",") if i.strip()]
        base = select(Song).where(Song.id.in_(id_list))
    else:
        base = _apply_filters(select(Song), category, sub, keyword, author)

    # 分页
    if page is not None and size is not None:
        total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
        rows = db.scalars(
            base.order_by(Song.sort_order, Song.id).offset((page - 1) * size).limit(size)
        ).all()
        return PageResult[SongMetaOut](
            items=[song_to_meta(s) for s in rows],
            total=total,
            page=page,
            page_size=size,
        )

    # 非分页
    rows = list(db.scalars(base.order_by(Song.sort_order, Song.id)).all())
    if ids:
        # 保持 ids 传入顺序(listByIds 语义)
        order = {sid: i for i, sid in enumerate(id_list)}
        rows.sort(key=lambda s: order.get(s.id, len(id_list)))
    return [song_to_meta(s) for s in rows]
