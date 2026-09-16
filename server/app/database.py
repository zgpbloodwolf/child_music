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


def _ensure_columns() -> None:
    """向前补列:给已存在的表补上模型新增的列。

    create_all 只建「缺失的表」,不会改动已存在的表 —— 新增字段(如
    categories.cover_path)若不补这一步,老库上查询会直接 no such column。
    SQLite 的 ADD COLUMN 是纯元数据操作,不重写已有的行。

    只处理可空列或带默认值的列:SQLite 不允许给「非空且无默认值」的列补
    ALTER,遇到这类(需重建表)跳过并提示,不静默失败。
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    # 先把缺失列全部算出来再开写事务:Inspector 会另取连接读 schema,
    # 边读边写容易与写锁互相等待。
    pending = []  # [(表名, 列对象)]
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue  # 交给 create_all 建
        have = {c["name"] for c in inspector.get_columns(table.name)}
        for col in table.columns:
            if col.name not in have:
                pending.append((table.name, col))

    if not pending:
        return

    added: list[str] = []
    skipped: list[str] = []
    with engine.begin() as conn:
        for table_name, col in pending:
            if not col.nullable and col.default is None and col.server_default is None:
                skipped.append(f"{table_name}.{col.name}")
                continue
            ddl = (
                f'ALTER TABLE "{table_name}" '
                f'ADD COLUMN "{col.name}" {col.type.compile(engine.dialect)}'
            )
            if col.server_default is not None:
                ddl += f" DEFAULT {col.server_default.arg}"
            conn.execute(text(ddl))
            added.append(f"{table_name}.{col.name}")

    if added:
        print(f"[db] 向前迁移补列: {', '.join(added)}")
    if skipped:
        print(f"[db] 警告:非空且无默认值,需重建表才能补:{', '.join(skipped)}")


def init_db() -> None:
    """建表 + 补齐已存在表上缺失的列。应用启动与迁移脚本调用。"""
    # 确保模型已导入,Base.metadata 才有表定义
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_columns()
