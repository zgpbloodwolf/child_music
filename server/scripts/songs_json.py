"""从本地 SQLite 库全量重建曲库源数据 data/songs.json。

曲库有两个副本:仓库根 data/songs.json(源数据,入库) 与 server/data/music.db
(运行时,被 API 读取)。凡直接改库的脚本(import-erge.py、enrich_lyrics.py)
改完都要调本模块把 JSON 同步回来,否则两者会漂移。

输出结构(与历史版本保持字节级一致,消费方是 migrate_from_json.py):
  {大类: {"_info": {name,icon,desc,count},
          "子类 key": {"_info": {...,count}, "songs": [{id,name,artist,src,cover[,lyric][,originalPath]}]}}}
"""
import json
import sqlite3
from pathlib import Path

# 本模块位于 server/scripts/,上溯两级是仓库根
PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB = PROJECT_DIR / "server" / "data" / "music.db"
DEFAULT_OUT = PROJECT_DIR / "data" / "songs.json"


def rebuild(db_path: Path = DEFAULT_DB, out_path: Path = DEFAULT_OUT) -> tuple[int, int]:
    """读库重建 JSON。返回 (大类数, 歌曲总数)。"""
    db = sqlite3.connect(str(db_path))
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
        info = {"name": cat["name"], "icon": cat["icon"] or "", "desc": cat["desc"] or ""}
        # 大类封面只在「已设置」时输出:若空值也写(空串或 null),4 个大类的 _info
        # 都会多出一个键,给每次导出都添上无意义 diff。
        # 用 .get 而非 cat["cover_path"]:老库尚未补列时本函数仍可运行。
        if cat.get("cover_path"):
            info["cover"] = "/static/" + cat["cover_path"]
        out[cat_id] = {"_info": info}
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

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    total_songs = sum(node["_info"]["count"] for node in out.values())
    return len(out), total_songs


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    n_cat, n_song = rebuild()
    print(f"已重建 {DEFAULT_OUT}: {n_cat} 大类, {n_song} 首")
