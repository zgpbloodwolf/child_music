"""一次性迁移:data/songs.json → SQLite + 拷贝音频文件到 storage。

关键(已踩坑验证):子类 key(如 children-classic)与文件目录名(children/classic)
不一致,且字段路径里子类段去掉了重复的大类前缀。故**必须从每条记录的 src/cover
字段提取真实相对路径**,绝不能用子类 key 拼路径。

幂等:每次清空三表全量重建。文件拷贝优先硬链接(零拷贝),失败回退拷贝。

用法:在 server/ 目录执行  python scripts/migrate_from_json.py
"""
import json
import os
import sys
from pathlib import Path

# 让脚本能 import app 包(脚本在 server/scripts/,app 在 server/app/)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402
from app.models import Category, Song, SubCategory  # noqa: E402
from app.services import storage  # noqa: E402

SERVER_DIR = Path(__file__).resolve().parent.parent
# 源数据路径:本地开发默认指向项目 src/static;Docker 容器内通过环境变量
# SOURCE_SONGS_JSON / SOURCE_LIBRARY_ROOT 指向挂载目录(/source)。
SONGS_JSON = Path(
    os.environ.get("SOURCE_SONGS_JSON")
    or (SERVER_DIR.parent / "data" / "songs.json")
)
SRC_STATIC = Path(
    os.environ.get("SOURCE_LIBRARY_ROOT") or (SERVER_DIR.parent / "src" / "static")
)
DST_STORAGE_ROOT = settings.library_dir.parent              # server/storage(容器内为持久卷)


def strip_static(p: str) -> str:
    """/static/library/... → library/...(相对 storage 根)。"""
    if not p:
        return ""
    s = p.lstrip("/")
    return s[len("static/"):] if s.startswith("static/") else s


def main() -> None:
    if not SONGS_JSON.exists():
        sys.exit(f"找不到 songs.json:{SONGS_JSON}")
    raw = json.loads(SONGS_JSON.read_text(encoding="utf-8"))

    init_db()

    cat_n = sub_n = song_n = 0
    dur_n = 0
    missing: list[str] = []
    ops = {"link": 0, "copy": 0, "skip": 0}

    with SessionLocal() as db:
        # 幂等:清空三表全量重建。
        # 这里**不能 commit**:三个 delete 必须与后面的 insert 同事务。否则一旦重建
        # 中途失败(见下方 flush 处的 FK 顺序说明),就会留下一个「已清空但没建回」
        # 的空库 —— 一次运行把曲库清掉,而调用方只看到一个报错。
        db.query(Song).delete()
        db.query(SubCategory).delete()
        db.query(Category).delete()
        db.flush()  # 显式按 Song→SubCategory→Category 顺序执行删除,不依赖 UoW 自行重排

        for cat_order, (cat_id, cat_node) in enumerate(raw.items()):
            info = (cat_node or {}).get("_info", {}) or {}
            db.add(
                Category(
                    id=cat_id,
                    name=info.get("name") or cat_id,
                    icon=info.get("icon", ""),
                    desc=info.get("desc", ""),
                    # 大类合集封面(可选):与歌曲封面同格式,存相对 storage 根的路径
                    cover_path=strip_static(info.get("cover", "")) or None,
                    sort_order=cat_order,
                )
            )
            cat_n += 1
            for sub_order, (sub_id, sub_node) in enumerate(cat_node.items()):
                if sub_id == "_info" or not isinstance(sub_node, dict):
                    continue
                sinfo = sub_node.get("_info", {}) or {}
                db.add(
                    SubCategory(
                        id=sub_id,
                        category_id=cat_id,
                        name=sinfo.get("name") or sub_id,
                        icon=sinfo.get("icon"),
                        desc=sinfo.get("desc"),
                        sort_order=sub_order,
                    )
                )
                # 必须显式 flush:Category / SubCategory / Song 之间只有裸外键列、没有
                # relationship 关联,SQLAlchemy 的 unit-of-work 推不出「songs 要排在
                # sub_categories 之后」,实际会把 songs 先批量插入 → 命中 FK 约束。
                # 空库首次导入必炸(旧版本即如此,且因上面那个 commit 会留下空库)。
                db.flush()
                sub_n += 1
                for song_order, entry in enumerate(sub_node.get("songs", []) or []):
                    audio_rel = strip_static(entry.get("src", ""))
                    cover_rel = strip_static(entry.get("cover", ""))
                    duration: float | None = None
                    if audio_rel:
                        src_abs = SRC_STATIC / audio_rel
                        dst_abs = DST_STORAGE_ROOT / audio_rel
                        if src_abs.exists():
                            mode = storage.link_or_copy(src_abs, dst_abs)
                            ops[mode] += 1
                            duration = storage.read_duration(dst_abs)
                            if duration is not None:
                                dur_n += 1
                        else:
                            missing.append(audio_rel)
                            ops["skip"] += 1
                    db.add(
                        Song(
                            id=entry["id"],
                            name=entry.get("name", entry["id"]),
                            artist=entry.get("artist", ""),
                            album=entry.get("album"),
                            category_id=cat_id,
                            sub_category_id=sub_id,
                            duration=duration,
                            lyric=entry.get("lyric"),
                            audio_path=audio_rel,
                            cover_path=cover_rel or None,
                            original_path=entry.get("originalPath"),
                            sort_order=song_order,
                        )
                    )
                    song_n += 1
        db.commit()

    print("迁移完成:")
    print(f"  分类: {cat_n}")
    print(f"  子类: {sub_n}")
    print(f"  歌曲: {song_n}")
    print(f"  时长补全: {dur_n}/{song_n}")
    print(f"  文件操作: 硬链接 {ops['link']}, 拷贝 {ops['copy']}, 跳过 {ops['skip']}")
    if missing:
        print(f"  缺失音频文件: {len(missing)}(示例: {missing[:5]})")
    else:
        print("  缺失音频文件: 0")


if __name__ == "__main__":
    main()
