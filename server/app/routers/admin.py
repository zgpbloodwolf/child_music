"""管理路由(写操作),全部依赖 verify_admin_token。

涵盖:歌曲上传/编辑/删除/替换封面,大类与子类的新建/编辑/删除。
删除分类前校验「无歌曲」才允许(避免歌曲 category_id 悬空)。
"""
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_db, verify_admin_token
from ..models import Category, Song, SubCategory
from ..schemas import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    SongOut,
    SongUpdate,
    SubCategoryCreate,
    SubCategoryOut,
)
from ..services import storage
from ..services.meta import song_to_out, sub_to_out

router = APIRouter(
    prefix="/api/admin",
    tags=["管理(需 token)"],
    dependencies=[Depends(verify_admin_token)],
)


def _abs(rel_path: str) -> Path:
    """存储相对路径 → 绝对路径(用于文件读写)。"""
    return settings.library_dir.parent / rel_path


def _song_count_in_sub(db: Session, sub_id: str) -> int:
    return db.scalar(select(func.count()).where(Song.sub_category_id == sub_id)) or 0


def _song_count_in_cat(db: Session, cat_id: str) -> int:
    return db.scalar(select(func.count()).where(Song.category_id == cat_id)) or 0


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
    ext = Path(audio.filename or "x.mp3").suffix.lower() or ".mp3"
    audio_path = dest_dir / f"{id}{ext}"
    storage.write_bytes(audio.file.read(), audio_path)

    cover_abs: Path | None = None
    if cover and cover.filename:
        cext = Path(cover.filename).suffix.lower() or ".jpg"
        cover_abs = dest_dir / f"{id}{cext}"
        storage.write_bytes(cover.file.read(), cover_abs)

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
    cext = Path(cover.filename or "x.jpg").suffix.lower() or ".jpg"
    cover_abs = dest_dir / f"{song_id}{cext}"
    storage.write_bytes(cover.file.read(), cover_abs)
    if song.cover_path:  # 旧封面扩展名可能不同,一并删
        storage.safe_remove(_abs(song.cover_path))
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
    return CategoryOut(id=c.id, name=c.name, icon=c.icon, desc=c.desc, subs=[])


@router.put("/categories/{cat_id}", response_model=CategoryOut, summary="编辑大类")
def update_category(cat_id: str, body: CategoryUpdate, db: Session = Depends(get_db)) -> CategoryOut:
    c = db.get(Category, cat_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "大类不存在")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(c, key, value)
    db.commit()
    db.refresh(c)
    subs = db.scalars(
        select(SubCategory).where(SubCategory.category_id == c.id).order_by(SubCategory.sort_order, SubCategory.id)
    ).all()
    return CategoryOut(id=c.id, name=c.name, icon=c.icon, desc=c.desc, subs=[sub_to_out(s) for s in subs])


@router.delete("/categories/{cat_id}", summary="删除大类(须无歌曲与子类)")
def delete_category(cat_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    c = db.get(Category, cat_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "大类不存在")
    if _song_count_in_cat(db, cat_id) > 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "该大类下仍有歌曲,请先迁移或删除")
    if db.scalar(select(func.count()).where(SubCategory.category_id == cat_id)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "该大类下仍有子类,请先删除子类")
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
