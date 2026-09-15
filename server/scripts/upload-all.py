"""用管理接口批量导入全部歌曲(逐首 multipart 上传)。

标准库实现(urllib),不依赖 requests。
中文字段经 multipart 编码为 UTF-8,绕开 bash 命令行转义导致的乱码。

用法:
  ADMIN_BASE=http://<服务器>:8823/cmusic/api/admin  (目标管理接口,不设默认本机)
  set ADMIN_TOKEN=xxx   (Windows cmd)
  $env:ADMIN_TOKEN=xxx (PowerShell)
  ADMIN_TOKEN=xxx python server/scripts/upload-all.py (bash)
"""
import json
import os
import sys
import time
import urllib.request
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError

BASE = os.environ.get("ADMIN_BASE", "http://127.0.0.1:8823/cmusic/api/admin")
TOKEN = os.environ.get("ADMIN_TOKEN", "")
if not TOKEN:
    sys.exit("请先设置环境变量 ADMIN_TOKEN")

# 本脚本位于 server/scripts/,上溯两级是仓库根(与运行时工作目录无关)
STATIC_DIR = Path(__file__).resolve().parents[2] / "dist/build/h5/static"
SONGS_JSON = STATIC_DIR / "data/songs.json"
# audio_rel 经 strip_static 后为 "library/children/classic/cn002.mp3"(含 library 前缀),
# 故文件根就是 STATIC_DIR,不要再拼 library
LIBRARY = STATIC_DIR

if not SONGS_JSON.exists():
    sys.exit(f"找不到 songs.json: {SONGS_JSON}")


def auth_header() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


def post_json(path: str, data: dict) -> tuple[int, str]:
    """发 JSON POST,返回 (状态码, 响应体)。"""
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
    """构造 multipart/form-data 请求体。fields 值为 str,files 值为 (filename, bytes)。"""
    boundary = uuid.uuid4().hex
    lines: list[bytes] = []
    for key, val in fields.items():
        lines.append(f"--{boundary}".encode())
        lines.append(
            f'Content-Disposition: form-data; name="{key}"'.encode()
        )
        lines.append(b"")
        lines.append(val.encode("utf-8"))
    for key, (fname, data) in files.items():
        lines.append(f"--{boundary}".encode())
        lines.append(
            f'Content-Disposition: form-data; name="{key}"; filename="{fname}"'.encode()
        )
        lines.append(b"Content-Type: application/octet-stream")
        lines.append(b"")
        lines.append(data)
    lines.append(f"--{boundary}--".encode())
    lines.append(b"")
    body = b"\r\n".join(lines)
    return body, f"multipart/form-data; boundary={boundary}"


def upload_song(song: dict, cat_id: str, sub_id: str) -> tuple[int, str]:
    """上传单首歌曲。"""
    audio_rel = song.get("src", "").lstrip("/")
    if audio_rel.startswith("static/"):
        audio_rel = audio_rel[len("static/"):]
    cover_rel = song.get("cover", "").lstrip("/")
    if cover_rel.startswith("static/"):
        cover_rel = cover_rel[len("static/"):]

    audio_path = LIBRARY / audio_rel
    if not audio_path.exists():
        return 0, f"缺音频文件: {audio_path}"

    fields = {
        "id": song.get("id", ""),
        "name": song.get("name", song.get("id", "")),
        "artist": song.get("artist", ""),
        "category_id": cat_id,
        "sub_category_id": sub_id,
    }
    album = song.get("album")
    if album:
        fields["album"] = album
    lyric = song.get("lyric")
    if lyric:
        fields["lyric"] = lyric

    files = {"audio": (audio_path.name, audio_path.read_bytes())}
    cover_path = LIBRARY / cover_rel if cover_rel else None
    if cover_path and cover_path.exists():
        files["cover"] = (cover_path.name, cover_path.read_bytes())

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
    raw = json.loads(SONGS_JSON.read_text(encoding="utf-8"))

    # ---- 第一步:建大类和子类(幂等,409 跳过) ----
    print("=== 建分类(幂等) ===")
    for cat_id, cat_node in raw.items():
        info = (cat_node or {}).get("_info", {}) or {}
        code, _ = post_json(
            "/categories",
            {
                "id": cat_id,
                "name": info.get("name", cat_id),
                "icon": info.get("icon", ""),
                "desc": info.get("desc", ""),
            },
        )
        if code == 200:
            print(f"  建大类: {cat_id} ({info.get('name', cat_id)})")
        elif code == 409:
            print(f"  大类已存在: {cat_id}")
        else:
            print(f"  建大类失败({code}): {cat_id}")

        for sub_id, sub_node in cat_node.items():
            if sub_id == "_info" or not isinstance(sub_node, dict):
                continue
            sinfo = sub_node.get("_info", {}) or {}
            code, _ = post_json(
                "/subs",
                {
                    "id": sub_id,
                    "category_id": cat_id,
                    "name": sinfo.get("name", sub_id),
                    "icon": sinfo.get("icon", ""),
                    "desc": sinfo.get("desc", ""),
                },
            )
            if code == 200:
                print(f"  建子类: {sub_id} ({sinfo.get('name', sub_id)})")
            elif code == 409:
                pass  # 已存在,静默
            else:
                print(f"  建子类失败({code}): {sub_id}")

    # ---- 第二步:逐首上传 ----
    print("\n=== 开始逐首上传 ===")
    total = sum(
        len(sn.get("songs", []) or [])
        for cn in raw.values()
        for sn in cn.values()
        if isinstance(sn, dict)
    )
    ok = fail = skip = 0
    i = 0
    for cat_id, cat_node in raw.items():
        for sub_id, sub_node in cat_node.items():
            if sub_id == "_info" or not isinstance(sub_node, dict):
                continue
            for song in sub_node.get("songs", []) or []:
                i += 1
                sid = song.get("id", f"未知{i}")
                code, msg = upload_song(song, cat_id, sub_id)
                if code == 200:
                    ok += 1
                    if i % 50 == 0:
                        print(f"[{i}/{total}] 已上传 {ok} 首...")
                elif code == 409:
                    skip += 1
                    print(f"[{i}/{total}] 已存在,跳过: {sid}")
                else:
                    fail += 1
                    print(f"[{i}/{total}] 上传失败({code}): {sid} {msg[:120]}")
                    time.sleep(0.5)  # 失败稍作停顿避免连续冲击

    print(f"\n=== 导入完成 ===")
    print(f"  成功: {ok}")
    print(f"  跳过(已存在): {skip}")
    print(f"  失败: {fail}")
    print(f"  总计: {total}")


if __name__ == "__main__":
    main()
