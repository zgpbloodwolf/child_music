"""把本地 560 首新儿歌经管理接口同步到服务器。

服务器 DB 已有 1119 条记录(含元数据),但缺音频文件。
策略:先删 560 首新歌曲记录,再用上传接口逐首创建(带音频)。

新歌曲 id 范围: cn161~cn674 + en080~en125(从 import-plan.json 读取)。

用法: ADMIN_TOKEN=xxx python sync-erge-to-server.py
"""
import json
import os
import sys
import time
import urllib.request
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://192.168.50.88:8823/cmusic/api/admin"
TOKEN = os.environ.get("ADMIN_TOKEN", "")
if not TOKEN:
    sys.exit("请先设置环境变量 ADMIN_TOKEN")

PROJECT_DIR = Path(__file__).parent
PLAN_PATH = PROJECT_DIR / "import-plan.json"
STORAGE = PROJECT_DIR / "server" / "storage" / "library"


def auth_header() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


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


def delete_song(sid: str) -> int:
    req = urllib.request.Request(
        f"{BASE}/songs/{sid}", headers=auth_header(), method="DELETE"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status
    except HTTPError as e:
        return e.code
    except URLError:
        return 0


def upload_song(item: dict) -> tuple[int, str]:
    """上传单首歌曲(含音频文件)。"""
    sub_id = item["sub_category_id"]
    sub_dir = sub_id[len("children-"):] if sub_id.startswith("children-") else sub_id
    audio_path = STORAGE / "children" / sub_dir / f"{item['id']}.mp3"
    if not audio_path.exists():
        return 0, f"缺音频文件: {audio_path}"

    fields = {
        "id": item["id"],
        "name": item["name"],
        "artist": item["artist"],
        "category_id": "children",
        "sub_category_id": sub_id,
    }
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
    if not PLAN_PATH.exists():
        sys.exit(f"找不到映射表: {PLAN_PATH}")
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    total = len(plan)
    print(f"映射表: {total} 首待同步")

    # ---- Phase 1: 先删 560 首新歌曲(服务器 DB 已有记录但缺音频) ----
    print(f"\n=== Phase 1: 删除服务器上 {total} 首新歌曲记录 ===")
    del_ok = del_fail = 0
    for i, item in enumerate(plan, 1):
        code = delete_song(item["id"])
        if code in (200, 404):
            del_ok += 1
        else:
            del_fail += 1
            print(f"[{i}/{total}] 删除失败({code}): {item['id']}")
        if i % 100 == 0:
            print(f"[{i}/{total}] 已删除 {del_ok} 首...")
    print(f"删除完成: 成功 {del_ok}, 失败 {del_fail}")

    # 确保子类存在(children-tongyao)
    print("\n=== 确保子类存在 ===")
    sub_body = json.dumps(
        {"id": "children-tongyao", "category_id": "children",
         "name": "童谣", "icon": "🎈", "desc": "校园歌曲与少年童谣"},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/subs",
        data=sub_body,
        headers={**auth_header(), "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print("  建子类 children-tongyao: 200")
    except HTTPError as e:
        if e.code == 409:
            print("  子类 children-tongyao 已存在")
        else:
            print(f"  建子类失败: {e.code}")

    # ---- Phase 2: 逐首上传(带音频) ----
    print(f"\n=== Phase 2: 逐首上传 {total} 首(含音频) ===")
    ok = fail = skip = 0
    for i, item in enumerate(plan, 1):
        code, msg = upload_song(item)
        if code == 200:
            ok += 1
            if i % 50 == 0:
                print(f"[{i}/{total}] 已上传 {ok} 首...")
        elif code == 409:
            skip += 1
        else:
            fail += 1
            print(f"[{i}/{total}] 上传失败({code}): {item['id']} {item['name']} {msg[:100]}")
            time.sleep(0.5)

    print(f"\n=== 同步完成 ===")
    print(f"  成功: {ok}")
    print(f"  跳过(已存在): {skip}")
    print(f"  失败: {fail}")
    print(f"  总计: {total}")


if __name__ == "__main__":
    main()
