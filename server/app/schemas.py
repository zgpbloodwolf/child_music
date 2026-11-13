"""Pydantic 请求/响应模型。

响应字段用 snake_case 属性 + camelCase alias(对齐前端 TS 契约 SongMeta/Song/
Category/SubCategory);FastAPI 默认按 alias 输出 JSON。管理请求模型仅后端内部
使用,保留 snake_case 属性名。
"""
from typing import Generic, TypeVar
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
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
    # 以下两字段主要供管理页编辑回填(App 端契约未含,多余字段前端自动忽略)
    sort_order: int = 0  # 同类内排序(小的在前) → sortOrder
    original_path: str | None = None  # 原始来源路径(溯源用) → originalPath


class SubCategoryOut(CamelModel):
    id: str
    name: str
    icon: str | None = None
    desc: str | None = None
    # 该子类下歌曲数 → songCount。
    # 计数随分类树一起下发,前端展示「N 首」无需再请求歌曲列表。
    song_count: int = 0


class CategoryOut(CamelModel):
    id: str
    name: str
    icon: str
    desc: str
    # 大类合集封面完整公网 URL(未设置为空字符串,前端回落色块/首曲封面)。
    # 由 services/meta.build_url 拼出,与歌曲 cover 同口径。
    cover: str = ""
    # 该大类下歌曲数(含各子类,由子类计数求和)→ songCount
    song_count: int = 0
    subs: list[SubCategoryOut] = []


class AuthorOut(CamelModel):
    """按作者聚合的统计(古诗作者面板用)。

    只返回聚合结果(name/count/subs),不含作品列表——作者面板只需要一个数字,
    原先客户端为此拉全量歌曲列表再内存聚合。
    """

    name: str  # 作者名(对应 Song.artist)
    count: int  # 作品数
    subs: list[str] = []  # 作品涉及的子类 id(供前端推断朝代,无需作品明细)


class PageResult(CamelModel, Generic[T]):
    """分页结果,对齐前端 PageResult<T>(items/total/page/pageSize)。"""

    items: list[T]
    total: int
    page: int
    page_size: int  # alias -> pageSize


# ===== 管理接口请求模型(后端内部用,保留 snake_case)=====


class SongUpdate(BaseModel):
    """编辑歌曲元数据(全部可选;文件类字段走各自的 /audio、/cover 接口)。"""

    name: str | None = None
    artist: str | None = None
    album: str | None = None
    category_id: str | None = None
    sub_category_id: str | None = None
    lyric: str | None = None
    sort_order: int | None = None
    original_path: str | None = None


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


# ===== 成员 / 收藏 / 播放历史 =====


class MemberOut(CamelModel):
    """成员/账号信息(对齐前端 MemberInfo 契约)。不含密码散列。"""

    id: str
    name: str
    username: str = ""  # 登录账号(小写;旧成员可能为空串)
    avatar: str = ""
    created_at: datetime  # → createdAt


class MemberCreate(BaseModel):
    """创建成员账号(内部模型;username 统一小写,密码明文仅出现在请求里)。"""

    username: str
    password: str
    name: str
    avatar: str = ""


class MemberAdminCreate(BaseModel):
    """后台创建账号(密码缺省时由后端自动生成,并随响应明文返回一次)。

    name(昵称)缺省时自动取登录账号,用户可在 App 内自行修改。
    """

    username: str
    name: str | None = None
    password: str | None = None
    avatar: str = ""


class MemberPasswordReset(BaseModel):
    """后台重置密码(缺省时自动生成)。"""

    password: str | None = None


class MemberAdminOut(CamelModel):
    """后台账号创建/重置响应:在 MemberOut 字段上附本次下发的明文密码。

    明文密码只在此响应里出现一次(服务端只存散列),由管理员转交给使用者。
    """

    id: str
    name: str
    username: str = ""
    avatar: str = ""
    created_at: datetime  # → createdAt
    password: str


class LoginIn(BaseModel):
    """登录请求。"""

    username: str
    password: str


class LoginOut(CamelModel):
    """登录响应:会话令牌 + 账号信息。"""

    token: str
    member: MemberOut


class ProfileUpdate(CamelModel):
    """App 端自助修改资料(昵称/头像按需传,至少一项;登录账号不开放自改)。

    App 请求体,故用 CamelModel 接受 camelCase(populate_by_name 同时兼容 snake_case)。
    - name/avatar 均可选:仅传谁改谁 —— 头像即时生效、昵称走保存按钮两种交互共用
      本接口;旧版 App 同时传双字段,行为不变,天然兼容;
    - avatar 两种合法值:预设 emoji(≤16 字符)或上传文件的相对路径
      (library/avatars/...,≤255,由 POST /api/auth/avatar 生成);其余拒绝入库。
    """

    name: str | None = None
    avatar: str | None = None

    @model_validator(mode="after")
    def _at_least_one(self) -> "ProfileUpdate":
        if not (self.name or "").strip() and not (self.avatar or "").strip():
            raise ValueError("至少修改昵称或头像中的一项")
        return self

    @field_validator("avatar")
    @classmethod
    def _check_avatar(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None  # 空串视为「不改」
        v = v.strip()
        if len(v) <= 16:
            return v  # 预设 emoji(短文本透传,入库无害,前端按文字渲染)
        if v.startswith("library/avatars/") and len(v) <= 255:
            return v
        raise ValueError("头像不合法")


class PasswordChange(CamelModel):
    """App 端自助修改密码:需携带旧密码验证身份。→ oldPassword / newPassword"""

    old_password: str
    new_password: str


class AdminLoginIn(BaseModel):
    """管理员登录请求(管理页 /admin 用,账号密码配置在 .env)。"""

    username: str
    password: str


class AdminSessionOut(CamelModel):
    """管理员会话状态探测响应(前端据此决定进管理页还是回登录页)。

    initialized:管理员账号是否已从 .env 同步(否 = .env 未配置,登录页提示不可用);
    authed:本次携带的会话令牌是否有效;
    username:authed 时的回显账号名。
    """

    initialized: bool
    authed: bool = False
    username: str = ""


class AdminLoginOut(CamelModel):
    """管理员登录响应:7 天会话令牌 + 账号名。"""

    token: str
    username: str


class SongIdsIn(CamelModel):
    """收藏/历史全量同步请求体:客户端以完整 id 列表为数据源,整表回写。"""

    song_ids: list[str] = Field(default_factory=list)  # → songIds
