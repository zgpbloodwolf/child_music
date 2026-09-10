"""从本机旧数据库 + 本机 mp3 文件,上传 320 首唐诗到服务器。

数据源:
  - 本机旧库 server/data/music.db(唐诗元数据:歌名/作者/时长/歌词/音频路径)
  - 本机 server/storage/library/poetry/tang300/*.mp3(音频文件)

上传到服务器管理接口(经 multipart),中文字段 UTF-8 编码。

用法:
  ADMIN_TOKEN=xxx python upload-tang300.py
"""
import json
import os
import sqlite3
import sys
import time
import urllib.request
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError

BASE = "http://192.168.50.88:8823/cmusic/api/admin"
TOKEN = os.environ.get("ADMIN_TOKEN", "")
if not TOKEN:
    sys.exit("请先设置环境变量 ADMIN_TOKEN")

SERVER_DIR = Path(__file__).parent / "server"
OLD_DB = SERVER_DIR / "data" / "music.db"
STORAGE = SERVER_DIR / "storage" / "library"  # audio_path 相对此处的根

if not OLD_DB.exists():
    sys.exit(f"找不到旧数据库: {OLD_DB}")


def auth_header() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


def post_json(path: str, data: dict) -> tuple[int, str]:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=body,
        headers={**auth_header(), "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except URLError as e:
        return 0, str(e)


def build_multipart(fields: dict, files: dict) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    lines: list[bytes] = []
    for key, val in fields.items():
        lines.append(f"--{boundary}".encode())
        lines.append(f'Content-Disposition: form-data; name="{key}"'.encode())
        lines.append(b"")
        lines.append(val.encode("utf-8"))
    for key, (fname, data) in files.items():
        lines.append(f"--{boundary}".encode())
        lines.append(
            f'Content-Disposition: form-data; name="{key}"; filename="{fname}"'.encode()
        )
        lines.append(b"Content-Type: audio/mpeg")
        lines.append(b"")
        lines.append(data)
    lines.append(f"--{boundary}--".encode())
    lines.append(b"")
    body = b"\r\n".join(lines)
    return body, f"multipart/form-data; boundary={boundary}"


def upload_song(song: sqlite3.Row) -> tuple[int, str]:
    """上传单首唐诗。song 字段: id,name,artist,lyric,audio_path。"""
    audio_rel = song["audio_path"]  # 如 library/poetry/tang300/tang300_xxx.mp3
    audio_path = STORAGE.parent / audio_rel
    if not audio_path.exists():
        return 0, f"缺音频文件: {audio_path}"

    fields = {
        "id": song["id"],
        "name": song["name"],
        "artist": song["artist"] or "",
        "category_id": "poetry",
        "sub_category_id": "tang300",
    }
    if song["album"]:
        fields["album"] = song["album"]
    if song["lyric"]:
        fields["lyric"] = song["lyric"]

    files = {"audio": (audio_path.name, audio_path.read_bytes())}

    body, ctype = build_multipart(fields, files)
    req = urllib.request.Request(
        f"{BASE}/songs",
        data=body,
        headers={**auth_header(), "Content-Type": ctype},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except URLError as e:
        return 0, str(e)


def main() -> None:
    db = sqlite3.connect(str(OLD_DB))
    db.row_factory = sqlite3.Row
    c = db.cursor()
    c.execute("SELECT * FROM songs WHERE category_id='poetry' AND sub_category_id='tang300' ORDER BY sort_order, id")
    songs = c.fetchall()
    db.close()
    total = len(songs)
    print(f"从旧库读取唐诗: {total} 首")
    if total == 0:
        sys.exit("旧库无唐诗数据")

    # ---- 清掉 poetry 下空的子类(poetry-tang 等,songs.json 建的),建 tang300 ----
    print("=== 调整子类 ===")
    for sub_id in ("poetry-tang", "poetry-song", "poetry-five", "poetry-seven"):
        code, _ = _delete_sub(sub_id)
        if code == 200:
            print(f"  删除空子类: {sub_id}")

    code, _ = post_json(
        "/subs",
        {"id": "tang300", "category_id": "poetry", "name": "唐诗三百首",
         "icon": "🎵", "desc": "唐诗三百首选集"},
    )
    if code == 200:
        print("  建子类: tang300 (唐诗三百首)")
    elif code == 409:
        print("  子类已存在: tang300")
    else:
        print(f"  建子类失败({code}): tang300")

    # ---- 逐首上传 ----
    print(f"\n=== 开始上传 {total} 首唐诗 ===")
    ok = fail = skip = 0
    for i, song in enumerate(songs, 1):
        code, msg = upload_song(song)
        if code == 200:
            ok += 1
            if i % 30 == 0:
                print(f"[{i}/{total}] 已上传 {ok} 首...")
        elif code == 409:
            skip += 1
        else:
            fail += 1
            print(f"[{i}/{total}] 失败({code}): {song['id']} {song['name']} {msg[:100]}")
            time.sleep(0.3)

    print(f"\n=== 唐诗导入完成 ===")
    print(f"  成功: {ok}")
    print(f"  跳过(已存在): {skip}")
    print(f"  失败: {fail}")
    print(f"  总计: {total}")


def _delete_sub(sub_id: str) -> tuple[int, str]:
    req = urllib.request.Request(
        f"{BASE}/subs/{sub_id}",
        headers=auth_header(),
        method="DELETE",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except URLError as e:
        return 0, str(e)


if __name__ == "__main__":
    main()
