"""ORM 模型:categories(大类)/ sub_categories(子类)/ songs(歌曲)
+ members(成员)/ favorites(收藏)/ play_history(播放历史)。

字段对齐前端 types/song.ts、types/category.ts;audio_path/cover_path 仅存
相对 storage 根的路径,返回时由 services/meta.py 拼成完整公网 URL。
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class Category(Base):
    """大类:children / poetry / classics / story。"""

    __tablename__ = "categories"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    icon = Column(String(32), default="", nullable=False)
    desc = Column(Text, default="", nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    # 大类合集封面(如古诗 tab 的大图),相对 storage 根;文件可能不存在。
    # 与歌曲封面同规矩:只能经 POST /api/admin/categories/{id}/cover 写入。
    cover_path = Column(String(512), nullable=True)

    subs = relationship(
        "SubCategory",
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="SubCategory.sort_order",
    )


class SubCategory(Base):
    """子类:children-classic / poetry-tang 等。"""

    __tablename__ = "sub_categories"

    id = Column(String(64), primary_key=True)
    category_id = Column(
        String(64),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(128), nullable=False)
    icon = Column(String(32), nullable=True)
    desc = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)

    category = relationship("Category", back_populates="subs")


class Song(Base):
    """歌曲:id 为主键;category_id/sub_category_id 冗余存储便于免 JOIN 查询。"""

    __tablename__ = "songs"

    id = Column(String(64), primary_key=True)
    name = Column(String(256), nullable=False, index=True)
    artist = Column(String(256), nullable=False)
    album = Column(String(256), nullable=True)
    category_id = Column(
        String(64),
        ForeignKey("categories.id"),
        nullable=False,
        index=True,
    )
    sub_category_id = Column(
        String(64),
        ForeignKey("sub_categories.id"),
        nullable=False,
        index=True,
    )
    duration = Column(Float, nullable=True)  # 秒;迁移时用 mutagen 补全
    lyric = Column(Text, nullable=True)
    audio_path = Column(String(512), nullable=False)  # 相对 storage 根
    cover_path = Column(String(512), nullable=True)  # 相对 storage 根;文件可能不存在
    original_path = Column(Text, nullable=True)  # 原始来源路径(溯源用)
    sort_order = Column(Integer, default=0, nullable=False)


class Member(Base):
    """成员账号:用户名 + 密码(PBKDF2 散列),登录后才能访问 /api 与曲库。

    - username 全局唯一(大小写不敏感,统一存小写);password_hash 为空表示
      旧版「无密码成员」(历史数据),不能登录,由管理端补设或删除;
    - 数据隔离(收藏/播放历史)仍按 member_id,即登录账号本身;
    - 媒体文件(/library)另有共享资源令牌 ACCESS_TOKEN 分层保护。
    """

    __tablename__ = "members"

    id = Column(String(32), primary_key=True)  # uuid4().hex
    name = Column(String(64), nullable=False)
    # 登录账号(小写;None = 未设置密码的旧成员)
    username = Column(String(64), nullable=True, unique=True, index=True)
    # 格式:pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>(见 app/security.py)
    password_hash = Column(String(256), nullable=True)
    # 头像两种形态:预设 emoji 字符 / 上传文件相对路径(library/avatars/xxx.png,
    # 由 POST /api/auth/avatar 落盘;SQLite 不强制列宽,老库 String(16) 无需迁移)
    avatar = Column(String(255), default="", nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class AdminUser(Base):
    """管理员账号:管理页(/admin)账号密码登录用,独立于 Member。

    - username 唯一且小写,校验规则复用 members.py 的 check_username;
    - pwd_version 是令牌世代:改密 +1,使改密前签发的所有会话令牌立即失效
      (无状态令牌无法吊销,用世代比对实现「改密即踢全部旧会话」);
    - 令牌主体用 id(uuid4().hex,恒为 ASCII)而非 username——username 允许中文,
      非 ASCII 字符进 Authorization 头浏览器会直接拒绝发送。
    """

    __tablename__ = "admin_users"

    id = Column(String(32), primary_key=True)  # uuid4().hex
    username = Column(String(64), nullable=False, unique=True, index=True)  # 小写
    # 格式:pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>(见 app/security.py)
    password_hash = Column(String(256), nullable=False)
    # 令牌世代,改密 +1 → 旧会话全部失效
    pwd_version = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class Favorite(Base):
    """收藏:member_id + song_id 联合主键;position 保留客户端提交的顺序。

    同步策略是「客户端全量、服务端照单全收」的 PUT 替换(见 routers/members.py),
    服务端不做增量事件,position 即客户端列表顺序。
    """

    __tablename__ = "favorites"

    member_id = Column(
        String(32), ForeignKey("members.id", ondelete="CASCADE"), primary_key=True
    )
    song_id = Column(
        String(64), ForeignKey("songs.id", ondelete="CASCADE"), primary_key=True
    )
    position = Column(Integer, default=0, nullable=False)


class PlayHistory(Base):
    """播放历史:按 played_at 倒序;条数上限由服务端截断(客户端本就只留 20 条)。"""

    __tablename__ = "play_history"

    member_id = Column(
        String(32), ForeignKey("members.id", ondelete="CASCADE"), primary_key=True
    )
    song_id = Column(
        String(64), ForeignKey("songs.id", ondelete="CASCADE"), primary_key=True
    )
    played_at = Column(DateTime, default=datetime.now, nullable=False)
