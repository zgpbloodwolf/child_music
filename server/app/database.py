"""SQLAlchemy 引擎、会话工厂、ORM 基类与 get_db 依赖。

SQLite 单文件,check_same_thread=False 让 FastAPI 线程池可共享连接;
写并发有限,故生产以单 worker 部署(见 run.py / 部署文档)。
"""
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .config import settings

engine = create_engine(
    settings.sqlite_url,
    # timeout:写锁等待上限(秒),默认 5s 并发写易报 database is locked
    connect_args={"check_same_thread": False, "timeout": 30},
)


@event.listens_for(engine, "connect")
def _sqlite_pragma(dbapi_conn, _record) -> None:
    """每个连接建立时执行的 PRAGMA:

    - journal_mode=WAL:读写不再全库互斥,管理写入与并发查询相遇不易锁库
    - foreign_keys=ON:SQLite 默认不强制外键,开启后模型声明的
      ondelete=CASCADE 等约束才真正生效(否则只是声明)
    """
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖:每请求一个会话,请求结束自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """根据 ORM 模型建表(已存在的表不动)。应用启动与迁移脚本调用。"""
    # 确保模型已导入,Base.metadata 才有表定义
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
