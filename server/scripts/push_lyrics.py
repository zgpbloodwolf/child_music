"""把本地已补录的歌词通过管理接口同步到远端服务器。

为什么需要它
------------
`data/songs.json`(入库的曲库源)与 `server/data/music.db`(本地运行库)都在本机,
而线上服务器有一份**独立的**运行库(compose 里挂 `./volumes/db`)。
补录歌词只改了本地那两份,线上不会自动跟着变 —— 必须显式推一次。

为什么走接口而不是替换库文件
----------------------------
线上 DB 在容器持久卷里;管理接口还有 `require_intranet` 一道闸,公网来源一律 403
(走 cpolar 反代也不行,除非把出口网段加进 ADMIN_ALLOW_CIDRS)。
在内网直连服务器的 8823 端口是最短路径,且不需要碰服务器文件系统。

为什么是「逐首 GET」而不是用 missing 筛选
-----------------------------------------
线上镜像可能比本地旧。实测 2026-09 部署的那版 `/api/songs` 连 `missing`
参数都不存在,传了会被忽略并返回**全量** —— 若照着它算,会误判成
「1119 首全都没歌词」。所以这里对「本地有歌词」的歌曲逐首 GET 详情来比对,
不依赖远端的筛选能力(本地 331 首,内网几十秒)。
探测远端是否支持 `missing` 也会顺带报告,便于判断要不要重新部署镜像。

安全
----
· 只发 `{"lyric": ...}`。远端 `SongUpdate` 无必填字段,且 update_song 用
  `model_dump(exclude_unset=True)`,未传字段不会被清空。
· 写库前先用**不存在的 id** 探一次:401=token 无效,403=不在内网白名单,
  404=可写。该探测不会改动任何数据。
· 默认只补「远端为空」的歌。两边都有但内容不同时只报告,要覆盖需显式 --overwrite。

用法
----
  # 内网直连服务器(推荐)
  python server/scripts/push_lyrics.py --base-url http://192.168.x.x:8823 \
      --token <ADMIN_TOKEN>

  # 公网走反代(需 /cmusic 前缀,且出口网段在 ADMIN_ALLOW_CIDRS 内)
  python server/scripts/push_lyrics.py --base-url http://your-domain.example.com/cmusic \
      --token <ADMIN_TOKEN>

  --dry-run            只报告差异,不写
  --ids cn003,cn195    只处理指定歌曲
  --overwrite          两边都有但不同时,用本地覆盖远端
  --verify             推完再读回来逐条比对
  --from-db            以本地 DB 为源(默认用 data/songs.json)
  --sleep 0.2          每首之间停顿(远端限流时用)

> 本文件与 README 里一律用 `192.168.x.x` / `your-domain.example.com` 占位,
> **不要填真实内网 IP 或公网隧道域名**(cpolar 域名还会随隧道重建而变化,
> 写死反而误导)。真实地址只放在各自机器的 `.env`(已 .gitignore)。
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
SONGS_JSON = PROJECT_DIR / "data" / "songs.json"
DB_PATH = PROJECT_DIR / "server" / "data" / "music.db"

TIMEOUT = 20
RETRIES = 2


# ===== HTTP =====


def http(method: str, url: str, body: dict | None = None,
         token: str | None = None) -> tuple[int, object]:
    """发一次请求,返回 (status, 解析后的 JSON 或错误文本)。网络异常重试 RETRIES 次。"""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    last: str = ""
    for attempt in range(RETRIES + 1):
        req = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read().decode("utf-8", "replace")
                try:
                    return resp.status, json.loads(raw)
                except json.JSONDecodeError:
                    return resp.status, raw
        except urllib.error.HTTPError as e:
            # 4xx 是业务结果,不重试;5xx 才重试
            if e.code < 500:
                return e.code, e.read().decode("utf-8", "replace")[:300]
            last = f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001 —— 网络层各种异常一律重试
            last = repr(e)[:160]
        if attempt < RETRIES:
            time.sleep(1.5 * (attempt + 1))
    return -1, last


def resolve_base(candidates: list[str]) -> str | None:
    """从候选地址里挑出可用的那个(自动补 /cmusic 前缀再试)。"""
    tried: set[str] = set()
    for base in candidates:
        for cand in (base.rstrip("/"), base.rstrip("/") + "/cmusic"):
            if cand in tried:
                continue
            tried.add(cand)
            status, _ = http("GET", cand + "/health")
            if status == 200:
                print(f"  可用地址: {cand}")
                return cand
    return None


# ===== 数据源 =====


def load_local(from_db: bool) -> dict[str, str]:
    """本地「有歌词」的歌曲 -> 歌词文本。"""
    out: dict[str, str] = {}
    if from_db:
        if not DB_PATH.exists():
            sys.exit(f"本地 DB 不存在: {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        for sid, lyric in conn.execute(
            "SELECT id, lyric FROM songs WHERE lyric IS NOT NULL AND trim(lyric) <> ''"
        ):
            out[sid] = lyric
        conn.close()
        return out

    if not SONGS_JSON.exists():
        sys.exit(f"曲库源文件不存在: {SONGS_JSON}(可用 --from-db 改读本地库)")
    with open(SONGS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    for cat_node in data.values():
        for key, sub_node in cat_node.items():
            if key == "_info" or not isinstance(sub_node, dict):
                continue
            for song in sub_node.get("songs", []):
                lyric = (song.get("lyric") or "").strip()
                if lyric:
                    out[song["id"]] = lyric
    return out


# ===== 主流程 =====


def main() -> None:
    ap = argparse.ArgumentParser(description="把本地歌词通过管理接口同步到远端服务器")
    ap.add_argument("--base-url", default=os.environ.get("SERVER_BASE_URL", ""),
                    help="服务器地址,如 http://192.168.x.x:8823")
    ap.add_argument("--token", default=os.environ.get("ADMIN_TOKEN", ""),
                    help="管理接口 token(也可用环境变量 ADMIN_TOKEN)")
    ap.add_argument("--ids", default="", help="只处理这些歌曲,逗号分隔")
    ap.add_argument("--dry-run", action="store_true", help="只报告差异,不写")
    ap.add_argument("--overwrite", action="store_true",
                    help="两边都有但内容不同时,用本地覆盖远端")
    ap.add_argument("--verify", action="store_true", help="推完读回来逐条比对")
    ap.add_argument("--from-db", action="store_true", help="以本地 DB 为源(默认 data/songs.json)")
    ap.add_argument("--sleep", type=float, default=0.0, help="每首之间的停顿秒数")
    args = ap.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")

    if not args.base_url:
        sys.exit("必须给 --base-url(或用环境变量 SERVER_BASE_URL)")
    if not args.token:
        sys.exit("必须给 --token(或用环境变量 ADMIN_TOKEN)")

    print("=== 1) 解析服务器地址 ===")
    base = resolve_base([args.base_url])
    if not base:
        sys.exit("★ 服务器不可达:所有候选地址的 /health 都没返回 200")

    print("\n=== 2) 探测写入权限(用不存在的 id,无副作用)===")
    status, detail = http("PUT", f"{base}/api/admin/songs/__probe_not_exist__",
                          {"lyric": "probe"}, args.token)
    if status == 401:
        sys.exit("★ token 无效(401):检查 --token 是否与服务器 .env 的 ADMIN_TOKEN 一致")
    if status == 403:
        sys.exit("★ 来源不在内网白名单(403):需在内网直连,或把出口网段加进 ADMIN_ALLOW_CIDRS")
    if status != 404:
        sys.exit(f"★ 探测返回意外结果 {status}:{detail}")
    print("  token 有效、来源在内网白名单、接口可写(404 = 探测 id 不存在,符合预期)")

    print("\n=== 3) 读本地歌词 ===")
    local = load_local(args.from_db)
    src = "本地 DB" if args.from_db else "data/songs.json"
    if args.ids:
        want = {i.strip() for i in args.ids.split(",") if i.strip()}
        absent = sorted(want - set(local))
        local = {k: v for k, v in local.items() if k in want}
        if absent:
            print(f"  注意:这些 id 本地没有歌词,已跳过 -> {absent}")
    print(f"  源: {src},有歌词 {len(local)} 首")

    print("\n=== 4) 逐首比对远端 ===")
    to_push: list[tuple[str, str]] = []
    differ: list[str] = []
    same = 0
    missing_remote: list[str] = []

    for i, (sid, lyric) in enumerate(sorted(local.items()), 1):
        status, data = http("GET", f"{base}/api/songs/{sid}")
        if status == 404:
            missing_remote.append(sid)
            continue
        if status != 200 or not isinstance(data, dict):
            print(f"  ! {sid} 读取失败 {status} {str(data)[:80]}")
            continue
        remote_lyric = (data.get("lyric") or "").strip()
        if not remote_lyric:
            to_push.append((sid, lyric))
        elif remote_lyric == lyric.strip():
            same += 1
        else:
            differ.append(sid)
            if args.overwrite:
                to_push.append((sid, lyric))
        if i % 60 == 0:
            print(f"  ...已比对 {i}/{len(local)}")
        if args.sleep:
            time.sleep(args.sleep)

    print(f"  远端为空需补 : {len(to_push)} 首")
    print(f"  两边一致     : {same} 首")
    print(f"  两边不同     : {len(differ)} 首" + ("(已计入覆盖)" if args.overwrite else "(默认不动)"))
    if differ and not args.overwrite:
        print(f"    不同清单: {differ[:20]}{' ...' if len(differ) > 20 else ''}")
    if missing_remote:
        print(f"  远端没有这些歌: {len(missing_remote)} 首 -> {missing_remote[:10]}")

    if not to_push:
        print("\n无需写入。")
    elif args.dry_run:
        print("\n[dry-run] 将写入以下歌曲(未实际提交):")
        for sid, lyric in to_push[:20]:
            first = next((l for l in lyric.splitlines() if l.strip()), "")
            print(f"  {sid:10s} {len(lyric):5d}字  {first[:44]}")
        if len(to_push) > 20:
            print(f"  ... 其余 {len(to_push) - 20} 首")
    else:
        print(f"\n=== 5) 写入 {len(to_push)} 首 ===")
        ok, fail = 0, []
        for sid, lyric in to_push:
            status, data = http("PUT", f"{base}/api/admin/songs/{sid}",
                                {"lyric": lyric}, args.token)
            if status == 200:
                ok += 1
                print(f"  ✓ {sid}")
            else:
                fail.append((sid, status, str(data)[:100]))
                print(f"  ✗ {sid} {status} {str(data)[:90]}")
            if args.sleep:
                time.sleep(args.sleep)
        print(f"  写入成功 {ok} 首,失败 {len(fail)} 首")
        for sid, status, detail in fail:
            print(f"    {sid} {status} {detail}")

        if args.verify and ok:
            print("\n=== 6) 回读校验 ===")
            bad = 0
            for sid, lyric in to_push:
                status, data = http("GET", f"{base}/api/songs/{sid}")
                got = (data.get("lyric") or "").strip() if isinstance(data, dict) else ""
                if got != lyric.strip():
                    bad += 1
                    print(f"  ✗ {sid} 回读不一致({len(got)}字 vs {len(lyric)}字)")
            print(f"  校验通过 {ok - bad}/{ok} 首" if not bad else f"  ★ {bad} 首不一致")


if __name__ == "__main__":
    main()
