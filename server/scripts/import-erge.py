"""儿歌去重分类导入脚本(从 E:\\儿歌 批量导入)。

流程:
  1. 扫描 E:\\儿歌,清理文件名,按歌名去重(mp3 优先 > wma > mp4)
  2. 跳过与本地库现有歌名重复的 65 首
  3. 按来源目录映射到目标子类(童谣 children-tongyao 新建)
  4. 分配 id(cn151 起 / en080 起)
  5. ffmpeg 批量转 wma/mp4 为 mp3,落地到 server/storage/library/
  6. 直接写本地 SQLite 库(避免 570 次 HTTP)
  7. 重建 data/songs.json(仓库根的曲库源数据)

用法: python server/scripts/import-erge.py
"""
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# 强制 UTF-8 输出(避免 Windows GBK 乱码)
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# ---- 配置 ----
# 本脚本位于 server/scripts/,上溯两级才是仓库根(脚本所有路径都以仓库根为基准,
# 因此与运行时的工作目录无关)。
SOURCE_ROOT = Path(r"E:\儿歌")
PROJECT_DIR = Path(__file__).resolve().parents[2]
SERVER_DIR = PROJECT_DIR / "server"
DB_PATH = SERVER_DIR / "data" / "music.db"
STORAGE_ROOT = SERVER_DIR / "storage" / "library"
SONGS_JSON = PROJECT_DIR / "data" / "songs.json"

# 分类映射:来源目录名 → (子类 id, 子类中文名, 子类描述)
# 童年歌谣特辑 + 经典儿歌打包 + 少儿歌曲 → 童谣(children-tongyao,新建)
# 中华儿歌珍藏 + 巧虎 + 贝瓦 → 经典儿歌(children-classic,已有)
# 英文儿歌 → 英文儿歌(children-english,已有)
DIR_TO_SUB = {
    "中华儿歌珍藏 160首": ("children-classic", "经典儿歌", "传唱多年的经典"),
    "少儿歌曲 50首": ("children-tongyao", "童谣", "校园歌曲与少年童谣"),
    "巧虎儿歌170首": ("children-classic", "经典儿歌", "传唱多年的经典"),
    "童年歌谣特辑01": ("children-tongyao", "童谣", "校园歌曲与少年童谣"),
    "童年歌谣特辑02": ("children-tongyao", "童谣", "校园歌曲与少年童谣"),
    "童年歌谣特辑03": ("children-tongyao", "童谣", "校园歌曲与少年童谣"),
    "经典儿歌打包": ("children-tongyao", "童谣", "校园歌曲与少年童谣"),
    "贝瓦儿歌 196首": ("children-classic", "经典儿歌", "传唱多年的经典"),
    "英文儿歌": ("children-english", "英文儿歌", "英文启蒙儿歌"),
}

# 新建子类(库中尚不存在)
NEW_SUBS = {
    "children-tongyao": {"name": "童谣", "icon": "🎈", "desc": "校园歌曲与少年童谣"},
}

EXT_PRIORITY = {"mp3": 0, "wma": 1, "mp4": 2}


def clean_name(filename: str) -> str:
    """清理文件名得到标准歌名。

    顺序:去扩展名 → 去序号前缀 → 去来源前缀 → 去括号注释 → strip。
    """
    base = re.sub(r"\.(mp3|wma|mp4)$", "", filename, flags=re.I)
    # 去序号前缀:01. / 02 / 46 等(数字+点或空格)
    base = re.sub(r"^\d+[.\s]*", "", base)
    # 去来源前缀
    base = re.sub(r"^4399儿歌-", "", base)
    base = re.sub(r"^亲宝儿歌-", "", base)
    base = re.sub(r"^贝瓦儿歌-", "", base)
    # 去括号注释(中英文括号)
    base = re.sub(r"[\(（].*?[\)）]", "", base)
    return base.strip()


def scan_source() -> dict[str, tuple[str, str, str]]:
    """扫描源目录,按清理后歌名分组去重。

    返回 {歌名: (ext, 文件完整路径, 来源目录名)}。
    每组保留格式优先级最高的文件(mp3 > wma > mp4)。
    """
    all_files: list[tuple[str, str, str, str]] = []  # (clean, ext, path, parent_dir)

    for root, _, files in os.walk(SOURCE_ROOT):
        # 跳过 rar 等非音频
        for fn in files:
            m = re.search(r"\.(mp3|wma|mp4)$", fn, re.I)
            if not m:
                continue
            ext = m.group(1).lower()
            cn = clean_name(fn)
            if not cn:
                continue
            # 来源目录名:第一层子目录(用于映射分类)
            rel = os.path.relpath(root, SOURCE_ROOT)
            parent = rel.split(os.sep)[0] if rel != "." else ""
            all_files.append((cn, ext, os.path.join(root, fn), parent))

    # 按歌名分组,每组选最优文件
    by_name: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for cn, ext, path, parent in all_files:
        by_name[cn].append((ext, path, parent))

    unique: dict[str, tuple[str, str, str]] = {}
    for name, entries in by_name.items():
        # 按 ext 优先级排序取第一个
        entries.sort(key=lambda e: EXT_PRIORITY.get(e[0], 99))
        best = entries[0]
        unique[name] = best

    return unique


def load_existing_names() -> set[str]:
    """从本地库读取 children 大类下所有歌名(用于跳过重复)。"""
    if not DB_PATH.exists():
        return set()
    db = sqlite3.connect(str(DB_PATH))
    c = db.cursor()
    c.execute("SELECT name FROM songs WHERE category_id='children'")
    names = set(r[0] for r in c.fetchall())
    db.close()
    return names


def load_existing_max_ids() -> tuple[int, int]:
    """读取现有库中 cn / en 系 id 的最大序号。

    返回 (cn_max, en_max)。cn001~cn150 → 150;en001~en079 → 79。
    """
    db = sqlite3.connect(str(DB_PATH))
    c = db.cursor()
    c.execute("SELECT id FROM songs WHERE id LIKE 'cn%'")
    cn_max = 0
    for (sid,) in c.fetchall():
        m = re.match(r"^cn(\d+)$", sid)
        if m:
            cn_max = max(cn_max, int(m.group(1)))
    c.execute("SELECT id FROM songs WHERE id LIKE 'en%'")
    en_max = 0
    for (sid,) in c.fetchall():
        m = re.match(r"^en(\d+)$", sid)
        if m:
            en_max = max(en_max, int(m.group(1)))
    db.close()
    return cn_max, en_max


def build_plan(unique: dict, existing: set[str]) -> list[dict]:
    """生成导入映射表。

    跳过与现有库歌名相同的歌曲。分配 id。
    返回 [{name, artist, src_file, src_ext, category_id, sub_category_id, id}, ...]
    """
    cn_max, en_max = load_existing_max_ids()
    cn_seq = cn_max  # 从 cn_max+1 开始
    en_seq = en_max

    plan: list[dict] = []
    skipped = 0

    # 按来源目录分组,稳定排序(同目录的排一起)
    items = sorted(unique.items(), key=lambda x: x[1][2])  # 按 parent 排序

    for name, (ext, path, parent) in items:
        if name in existing:
            skipped += 1
            continue
        sub_info = DIR_TO_SUB.get(parent)
        if not sub_info:
            # 未知来源目录,归经典儿歌
            sub_info = ("children-classic", "经典儿歌", "传唱多年的经典")
        sub_id, _, _ = sub_info

        # 分配 id:英文儿歌用 en 前缀,其余用 cn
        if parent == "英文儿歌":
            en_seq += 1
            sid = f"en{en_seq:03d}"
        else:
            cn_seq += 1
            sid = f"cn{cn_seq:03d}"

        plan.append({
            "id": sid,
            "name": name,
            "artist": parent,  # 来源目录名当 artist
            "src_file": path,
            "src_ext": ext,
            "category_id": "children",
            "sub_category_id": sub_id,
            "original_path": path,
        })

    print(f"扫描完成: 去重后 {len(unique)} 首, 跳过现有库重复 {skipped} 首, 待导入 {len(plan)} 首")
    return plan


def sub_dir_for(sub_category_id: str) -> str:
    """子类 id → 存储目录名(去掉 children- 前缀)。"""
    if sub_category_id.startswith("children-"):
        return sub_category_id[len("children-"):]
    return sub_category_id


def convert_audio(plan: list[dict]) -> None:
    """Phase 2: ffmpeg 批量转 wma/mp4 为 mp3,mp3 直接拷贝。

    落地到 server/storage/library/children/{sub_dir}/{id}.mp3。
    """
    ok = fail = 0
    total = len(plan)
    for i, item in enumerate(plan, 1):
        sub_dir = sub_dir_for(item["sub_category_id"])
        dst_dir = STORAGE_ROOT / "children" / sub_dir
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / f"{item['id']}.mp3"

        if dst.exists():
            ok += 1
            continue  # 已转换过,跳过

        src = item["src_file"]
        if item["src_ext"] == "mp3":
            # mp3 直接拷贝(优先硬链接)
            try:
                os.link(src, dst)
            except OSError:
                shutil.copy2(src, dst)
            ok += 1
        else:
            # wma/mp4 用 ffmpeg 转 mp3;mp4 加 -vn 去视频
            vn_flag = ["-vn"] if item["src_ext"] == "mp4" else []
            cmd = ["ffmpeg", "-y", "-i", src, *vn_flag,
                   "-codec:a", "libmp3lame", "-qscale:a", "2", str(dst)]
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode != 0:
                print(f"[{i}/{total}] 转换失败: {item['id']} {item['name']} - {result.stderr.decode('utf-8','replace')[-200:]}")
                fail += 1
                continue
            ok += 1

        if i % 50 == 0:
            print(f"[{i}/{total}] 已处理 {ok} 首...")

    print(f"音频转换完成: 成功 {ok}, 失败 {fail}, 总计 {total}")


def read_duration(mp3_path: Path) -> float | None:
    """用 mutagen 读音频时长(秒)。"""
    try:
        from mutagen import File as MutagenFile
        audio = MutagenFile(str(mp3_path))
        if audio is not None and audio.info is not None:
            length = getattr(audio.info, "length", None)
            return float(length) if length is not None else None
    except Exception:
        return None
    return None


def write_db(plan: list[dict]) -> None:
    """Phase 3: 写入本地 SQLite 库。

    先建新子类(children-tongyao),再插入歌曲记录。
    幂等:已存在的 id 跳过。
    """
    db = sqlite3.connect(str(DB_PATH))
    c = db.cursor()

    # 建新子类
    for sub_id, info in NEW_SUBS.items():
        # 查大类是否存在
        c.execute("SELECT id FROM categories WHERE id='children'")
        if not c.fetchone():
            print("警告: children 大类不存在,先建大类")
            c.execute(
                "INSERT INTO categories (id, name, icon, desc, sort_order) VALUES (?,?,?,?,?,?)",
                ("children", "儿歌", "🎵", "欢快活泼,朗朗上口", 0),
            )
        # 查子类是否存在
        c.execute("SELECT id FROM sub_categories WHERE id=?", (sub_id,))
        if not c.fetchone():
            c.execute(
                "INSERT INTO sub_categories (id, category_id, name, icon, desc, sort_order) VALUES (?,?,?,?,?,?)",
                (sub_id, "children", info["name"], info["icon"], info["desc"], 0),
            )
            print(f"  建子类: {sub_id} ({info['name']})")

    # 插入歌曲
    ok = skip = fail = 0
    for item in plan:
        # 检查是否已存在(幂等)
        c.execute("SELECT id FROM songs WHERE id=?", (item["id"],))
        if c.fetchone():
            skip += 1
            continue

        sub_dir = sub_dir_for(item["sub_category_id"])
        audio_rel = f"library/children/{sub_dir}/{item['id']}.mp3"
        mp3_path = STORAGE_ROOT / "children" / sub_dir / f"{item['id']}.mp3"

        duration = read_duration(mp3_path) if mp3_path.exists() else None

        try:
            c.execute(
                """INSERT INTO songs (id, name, artist, album, category_id, sub_category_id,
                   duration, lyric, audio_path, cover_path, original_path, sort_order)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    item["id"], item["name"], item["artist"], None,
                    item["category_id"], item["sub_category_id"],
                    duration, None, audio_rel, None, item["original_path"], 0,
                ),
            )
            ok += 1
        except sqlite3.IntegrityError as e:
            print(f"  插入失败: {item['id']} - {e}")
            fail += 1

    db.commit()
    db.close()
    print(f"入库完成: 成功 {ok}, 跳过(已存在) {skip}, 失败 {fail}")


def rebuild_songs_json() -> None:
    """Phase 4: 从本地 DB 全量重建 songs.json。"""
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    c = db.cursor()
    c.execute("SELECT * FROM categories ORDER BY sort_order, id")
    cats = [dict(r) for r in c.fetchall()]
    c.execute("SELECT * FROM sub_categories ORDER BY sort_order, id")
    subs = [dict(r) for r in c.fetchall()]
    c.execute("SELECT * FROM songs ORDER BY category_id, sub_category_id, sort_order, id")
    songs = [dict(r) for r in c.fetchall()]
    db.close()

    out: dict = {}
    for cat in cats:
        cat_id = cat["id"]
        out[cat_id] = {"_info": {"name": cat["name"], "icon": cat["icon"] or "",
                                 "desc": cat["desc"] or ""}}
        for sub in [s for s in subs if s["category_id"] == cat_id]:
            sub_id = sub["id"]
            out[cat_id][sub_id] = {
                "_info": {"name": sub["name"], "icon": sub["icon"] or "",
                          "desc": sub["desc"] or ""},
                "songs": [],
            }
        for song in [s for s in songs if s["category_id"] == cat_id]:
            sub_id = song["sub_category_id"]
            if sub_id not in out[cat_id]:
                out[cat_id][sub_id] = {"_info": {"name": sub_id, "icon": "",
                                                  "desc": ""}, "songs": []}
            entry = {
                "id": song["id"],
                "name": song["name"],
                "artist": song["artist"],
                "src": "/static/" + song["audio_path"],
                "cover": "/static/" + song["cover_path"] if song["cover_path"] else "",
            }
            if song.get("lyric"):
                entry["lyric"] = song["lyric"]
            if song.get("original_path"):
                entry["originalPath"] = song["original_path"]
            out[cat_id][sub_id]["songs"].append(entry)

    # 回填 count
    for cat_id, node in out.items():
        total = 0
        for sub_id, sub_node in node.items():
            if sub_id == "_info":
                continue
            cnt = len(sub_node["songs"])
            sub_node["_info"]["count"] = cnt
            total += cnt
        node["_info"]["count"] = total

    SONGS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(SONGS_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    total_songs = sum(node["_info"]["count"] for node in out.values())
    print(f"已重建 songs.json: {len(out)} 大类, {total_songs} 首")


def main() -> None:
    print("=== Phase 1: 扫描去重 ===")
    unique = scan_source()
    print(f"  去重后唯一歌曲: {len(unique)}")

    existing = load_existing_names()
    print(f"  现有库 children 歌名: {len(existing)}")

    plan = build_plan(unique, existing)
    if not plan:
        print("无新歌曲可导入"); return

    # 保存映射表(中间产物,便于排查;仓库根,已 gitignore)
    with open(PROJECT_DIR / "import-plan.json", "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print(f"  映射表已保存: import-plan.json")

    print("\n=== Phase 2: ffmpeg 批量转换 ===")
    convert_audio(plan)

    print("\n=== Phase 3: 写入本地库 ===")
    write_db(plan)

    print("\n=== Phase 4: 重建 songs.json ===")
    rebuild_songs_json()

    # 最终统计
    db = sqlite3.connect(str(DB_PATH))
    c = db.cursor()
    c.execute("SELECT COUNT(*) FROM songs")
    total = c.fetchone()[0]
    c.execute("SELECT sub_category_id, COUNT(*) FROM songs WHERE category_id='children' GROUP BY sub_category_id ORDER BY sub_category_id")
    print(f"\n=== 导入完成 ===")
    print(f"  全库歌曲总数: {total}")
    print("  children 各子类:")
    for sub_id, cnt in c.fetchall():
        print(f"    {sub_id}: {cnt} 首")
    db.close()


if __name__ == "__main__":
    main()
