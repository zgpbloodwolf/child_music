"""元数据查询路由(只读),对齐前端 SongRepository 全部方法。

列表/搜索类返回 SongMetaOut(不含 src/lyric);get_detail 返回完整 SongOut。
统一的 /api/songs 用查询参数覆盖 listAll/listByCategory/listBySub/search/listByIds。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import Song, SubCategory
from ..schemas import CategoryOut, PageResult, SongMetaOut, SongOut, SubCategoryOut
from ..services.meta import build_category_tree, song_to_meta, song_to_out, sub_to_out

router = APIRouter(prefix="/api", tags=["曲库查询"])


@router.get("/categories", response_model=list[CategoryOut], summary="完整分类树")
def get_categories(db: Session = Depends(get_db)) -> list[CategoryOut]:
    """对应 Repository.getCategories():大类 + 其下子类(含空大类)。"""
    return build_category_tree(db)


@router.get("/subs/{sub_id}", response_model=SubCategoryOut | None, summary="按 id 查子类")
def find_sub(sub_id: str, db: Session = Depends(get_db)) -> SubCategoryOut | None:
    """对应 Repository.findSub():不存在返回 null。"""
    sub = db.get(SubCategory, sub_id)
    return sub_to_out(sub) if sub else None


@router.get("/subs/{sub_id}/category", summary="子类所属大类 id")
def category_id_of_sub(sub_id: str, db: Session = Depends(get_db)) -> dict[str, str | None]:
    """对应 Repository.categoryIdOfSub():返回 {categoryId},无匹配为 null。"""
    sub = db.get(SubCategory, sub_id)
    return {"categoryId": sub.category_id if sub else None}


@router.get("/songs/{song_id}", response_model=SongOut, summary="歌曲详情")
def get_song(song_id: str, db: Session = Depends(get_db)) -> SongOut:
    """对应 Repository.getDetail():返回完整 Song(含 src/lyric)。"""
    song = db.get(Song, song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "歌曲不存在")
    return song_to_out(song)


def _apply_filters(
    stmt, category: str | None, sub: str | None, keyword: str | None
):
    """叠加 category/sub 过滤与 keyword 搜索(name/artist/album 包含)。"""
    if category:
        stmt = stmt.where(Song.category_id == category)
    if sub:
        stmt = stmt.where(Song.sub_category_id == sub)
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
    ids: str | None = Query(None, description="逗号分隔的 id 列表"),
    page: int | None = Query(None, ge=1, description="页码(与 size 同时传则分页)"),
    size: int | None = Query(None, ge=1, le=500, description="每页条数"),
) -> list[SongMetaOut] | PageResult[SongMetaOut]:
    """对应 listAll/listByCategory/listBySub/search/listByIds。

    优先级:ids > keyword(+category/sub 组合) > sub > category > 全部。
    带 page+size 返回 PageResult(items/total/page/pageSize),否则返回裸数组。
    ids 模式按传入顺序排序(对齐 Repository.listByIds 的顺序敏感场景)。
    """
    if ids:
        id_list = [i.strip() for i in ids.split(",") if i.strip()]
        base = select(Song).where(Song.id.in_(id_list))
    else:
        base = _apply_filters(select(Song), category, sub, keyword)

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
