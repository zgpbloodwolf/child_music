"""Pydantic 请求/响应模型。

响应字段用 snake_case 属性 + camelCase alias(对齐前端 TS 契约 SongMeta/Song/
Category/SubCategory);FastAPI 默认按 alias 输出 JSON。管理请求模型仅后端内部
使用,保留 snake_case 属性名。
"""
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class CamelModel(BaseModel):
    """响应基类:snake_case 属性 ↔ camelCase JSON。

    populate_by_name:允许同时用属性名与 alias 构造;
    from_attributes:支持从 ORM 对象构造(本服务多用 dict 构造,留作扩展)。
    """

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


# ===== 响应模型(对齐前端契约)=====


class VersionOut(CamelModel):
    """App 版本信息(对齐前端 VersionInfo 契约)。

    供客户端比对版本并下载整包 APK;字段经 CamelModel 自动转 camelCase 输出。
    """

    version: str  # 展示版本(versionName,如 1.0.1)
    version_code: int  # 数值版本(派生,用于比对) → versionCode
    download_url: str = ""  # APK 完整 URL → downloadUrl
    release_notes: str = ""  # 更新说明 → releaseNotes
    force_update: bool = False  # 强制更新 → forceUpdate


class SongMetaOut(CamelModel):
    """列表/搜索用的轻量元数据(不含 src/lyric)。"""

    id: str
    name: str
    artist: str
    album: str | None = None
    cover: str  # 完整公网 URL(可能为空字符串,前端兜底色块)
    duration: float | None = None
    category: str
    sub_category: str | None = None


class SongOut(SongMetaOut):
    """完整歌曲信息(含 src/lyric),供播放使用。"""

    src: str  # 完整公网 URL
    lyric: str | None = None


class SubCategoryOut(CamelModel):
    id: str
    name: str
    icon: str | None = None
    desc: str | None = None


class CategoryOut(CamelModel):
    id: str
    name: str
    icon: str
    desc: str
    subs: list[SubCategoryOut] = []


class PageResult(CamelModel, Generic[T]):
    """分页结果,对齐前端 PageResult<T>(items/total/page/pageSize)。"""

    items: list[T]
    total: int
    page: int
    page_size: int  # alias -> pageSize


# ===== 管理接口请求模型(后端内部用,保留 snake_case)=====


class SongUpdate(BaseModel):
    """编辑歌曲元数据(全部可选)。"""

    name: str | None = None
    artist: str | None = None
    album: str | None = None
    category_id: str | None = None
    sub_category_id: str | None = None
    lyric: str | None = None


class CategoryCreate(BaseModel):
    id: str
    name: str
    icon: str = ""
    desc: str = ""


class CategoryUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    desc: str | None = None


class SubCategoryCreate(BaseModel):
    id: str
    category_id: str
    name: str
    icon: str | None = None
    desc: str | None = None
