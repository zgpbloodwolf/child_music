"""ORM 模型:categories(大类)/ sub_categories(子类)/ songs(歌曲)。

字段对齐前端 types/song.ts、types/category.ts;audio_path/cover_path 仅存
相对 storage 根的路径,返回时由 services/meta.py 拼成完整公网 URL。
"""
from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
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
