"""用 lrclib 为缺歌词的歌曲补录歌词(接口见 https://lrclib.net/docs)。

为什么不用 /api/get
-------------------
本库 songs.artist 存的是「来源目录名」(如 "巧虎儿歌170首"、"贝瓦儿歌 196首"),
不是真实歌手;songs.album 全为空。lrclib 的 GET /api/get 强制要求真实 artist_name
且强制 duration 校验,对本库直接不可用。
只能走 GET /api/search?track_name=<歌名>,再靠 **duration 门限** 排除同名不同歌。
这一步不是可选的:实测仅按歌名取首条会灌进完全不同的歌 ——
  · "不倒翁" 首条是吴克群的 297s 版本(本库 106s)
  · "牵牛花" 首条是阿牛的 215s 版本(本库 104s)
  · "小星星" 会命中苏打绿的同名创作曲(时长接近,仅 duration 挡不住)
故按 |本库 duration - lrclib duration| 分档:
  strong  <= --tol-strong(默认 3s)  同一录音/母带,默认写入
  loose   <= --tol-loose (默认 8s)  大概率同一首歌的不同录音,默认只进待复核清单
  超出    丢弃
loose 档默认不写,是因为已实测出 cn134「小星星」这类**错配**:时长能对上但
根本不是同一首歌。要批量采纳请显式 --apply-loose,并先看 review 清单。

歌词格式
--------
优先取 lrclib 的 syncedLyrics(LRC 带时间戳)。播放器 src/utils/lyric.ts 的
parseLyric() 只认 [mm:ss] 时间标签,无标签的行会被整行丢弃并退回「暂无歌词」,
所以纯文本歌词写进库虽然数据正确,当前 UI 仍显示不出来。仅在没有 syncedLyrics
时回退 plainLyrics(等前端支持纯文本展示即可生效)。

繁体转简体
----------
lrclib 的中文歌词多为繁体,而本库现有歌词(唐诗三百首 320 首)与新导入歌名
都是简体,直接写入会造成同一 App 内字形不一致,故默认用 opencc 做 t2s 转换。
转换只作用于汉字,不碰 LRC 的 [mm:ss] 标签(已实测)。
opencc 只是本脚本的开发期依赖,运行服务不需要,故**不写进 requirements.txt**:
  server/.venv/Scripts/python.exe -m pip install opencc-python-reimplemented
缺这个库时脚本会告警并保留繁体原文,不中断。

只补不改
--------
只写 lyric 为 NULL/纯空白的歌,绝不覆盖已有歌词(唐诗三百首那 320 首带同步
时间轴的歌词不会被碰)。

用法(在仓库根执行;需用装了 fastapi 的那个 venv 只为读库,不依赖 Web 服务)
----
  server/.venv/Scripts/python.exe server/scripts/enrich_lyrics.py --dry-run
  server/.venv/Scripts/python.exe server/scripts/enrich_lyrics.py
  server/.venv/Scripts/python.exe server/scripts/enrich_lyrics.py --apply-loose --rebuild-json
  # 复用旧缓存、不重新请求 lrclib:
  server/.venv/Scripts/python.exe server/scripts/enrich_lyrics.py --cache server/data/lrclib-cache.json

改完记得同步源数据:--rebuild-json(等价于单跑 server/scripts/songs_json.py),
否则 server/data/music.db 与仓库根 data/songs.json 会漂移。
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# 本脚本位于 server/scripts/,上溯两级是仓库根
PROJECT_DIR = Path(__file__).resolve().parents[2]
SERVER_DIR = PROJECT_DIR / "server"
DB_PATH = SERVER_DIR / "data" / "music.db"
DEFAULT_CACHE = SERVER_DIR / "data" / "lrclib-cache.json"
# 复核清单落在 docs/ 而不是 server/data/ —— 后者被 .gitignore 排除,团队看不到;
# 这份清单本来就是给人看的,要能随代码一起被 review。
REVIEW_PATH = PROJECT_DIR / "docs" / "lyrics-review.md"

# lrclib 要求用 User-Agent 标明客户端身份(名称 + 版本 + 主页/邮箱)。
# ★ 这里还缺一个可回访的联系方式,上线前建议补成项目仓库地址。
USER_AGENT = "cmusic-app v1.0.0 (lyrics enrichment script)"
API_BASE = "https://lrclib.net/api"

# 请求节流:lrclib 是免费无 key 服务,务必串行 + 间隔(文档建议 200~500ms)
REQUEST_DELAY = 0.35
MAX_RETRY = 5

TOL_STRONG = 3.0
TOL_LOOSE = 8.0

_PUNCT = re.compile(r"[\s\u3000·・、,，。.！!？?;；:：\"'“”‘’《》〈〉()（）\[\]【】{}<>—\-_~|/\\+&]+")
_PAREN = re.compile(r"[（(][^)）]*[)）]")


# ===== 歌名匹配 =====


def norm_name(s: str | None) -> str:
    """规范化歌名:去括号注释与标点空白,再小写。"""
    s = _PAREN.sub("", s or "")
    s = _PUNCT.sub("", s)
    return s.strip().lower()


def has_cjk(s: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def name_matches(ours: str, theirs: str | None) -> bool:
    """歌名是否算匹配。

    中文允许「包含」:中文没有词边界,且 lrclib 常写 "黑猫警长 (主题曲)"、
    "赵英俊 - 大王叫我来巡山" 这类带副标题/前缀的写法,全等会漏掉。
    拉丁文**只认全等**:短标题是长标题的子串太容易误命中 —— 实测
    "a good friend" 会匹配上 "she was a good friend"(完全不同的歌)。
    """
    a, b = norm_name(ours), norm_name(theirs)
    if not a or not b:
        return False
    if a == b:
        return True
    if not (has_cjk(a) or has_cjk(b)):
        return False
    return a in b or b in a


# 人工复核确认「lrclib 结果里根本没有本曲的正主」的歌曲。按我们自己的歌曲 id 整首排除:
# 这类曲子的候选**标题全等、时长也落在 loose 门限内**,但命中的全是同名的别首歌,
# 上面三道机器护栏(歌名全等/包含、duration 门限、内容表头)都挡不住。
# 逐条依据见 docs/lyrics-review.md 的复核记录。
NO_VALID_MATCH = {
    "cn134": "命中全是同名流行曲(苏打绿/杨千嬅/张震岳/万芳/王心凌),没有儿歌《小星星》",
    "en003": "本曲属 children-english(早教英语),命中全是同名的中文/日文流行曲",
}

# lrclib 存在「歌词内容是另一首歌」的错标记录,且同一错误会随专辑重复出现 ——
# 实测 cn591《小小粉刷匠》的两条记录(3980171 / 31227945,不同专辑、不同时长)
# 内容都是《妈妈的吻》。按记录 id 拉黑名单治不了根,改为按内容识别:
# 这类脏数据的首行是别人家的「歌名-歌手」表头,如 "妈妈的吻-小蓓蕾组合"。
_HEADER = re.compile(r"^(.{2,20}?)\s*[-–—]\s*(.{1,20})$")


def has_foreign_header(our_name: str, text: str) -> bool:
    """歌词首行是否像「另一首歌的名字-歌手」表头(即内容被塞错了)。

    要求同时满足:首行有 `-` 分隔、左段是不含空格的短标题、且整段歌词里
    压根没出现本歌名。三个条件叠加,避免误伤 —— 例如《健康歌》首行
    "男声：杨峻荣" 没有分隔符,不会触发。
    """
    body = re.sub(r"\[\d{1,2}:\d{1,2}(?:[.:]\d{1,3})?\]", "", text)
    first = next((ln.strip() for ln in body.splitlines() if ln.strip()), "")
    m = _HEADER.match(first)
    if not m:
        return False
    if " " in m.group(1) or "\u3000" in m.group(1):
        return False
    ours = norm_name(our_name)
    if ours and ours in norm_name(body):
        return False
    return True


# ===== lrclib 请求 =====


def search_track(name: str) -> tuple[object, str]:
    """按歌名搜索。返回 (结果列表 | None, 状态)。

    404 归一化为空列表(视为「查无此歌」);429 遵守 Retry-After;
    503/连接中断等退避重试。
    """
    url = f"{API_BASE}/search?" + urllib.parse.urlencode({"track_name": name})
    last = "unknown"
    for attempt in range(MAX_RETRY):
        req = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8")), "ok"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return [], "ok"
            if e.code == 429:
                # 文档明确要求遵守 Retry-After,忽略可能被临时封禁
                wait = float(e.headers.get("Retry-After") or 5)
                last = "429"
                time.sleep(min(wait, 60))
                continue
            last = f"http{e.code}"
            time.sleep(1.5 * (attempt + 1))
        except Exception as e:  # noqa: BLE001 网络类异常一律重试
            last = repr(e)[:80]
            time.sleep(1.5 * (attempt + 1))
    return None, last


# ===== 候选挑选 =====


def pick_candidate(our_name: str, our_dur: float | None, results: list[dict],
                   tol_strong: float, tol_loose: float):
    """在搜索结果里挑最佳候选。

    返回 (record, diff, tier)。tier ∈ strong / loose / unknown-dur,
    或 (None, None, 原因) 表示丢弃。
    """
    pairs: list[tuple[dict, float | None]] = []
    for rec in results:
        if not name_matches(our_name, rec.get("trackName")):
            continue
        # 内容被塞错的记录直接跳过(而不是整首放弃),好让后面的候选有机会顶上
        text, _src = lyrics_of(rec)
        if text is None or has_foreign_header(our_name, text):
            continue
        rd = rec.get("duration")
        if our_dur is not None and rd is not None:
            pairs.append((rec, abs(float(our_dur) - float(rd))))
        else:
            pairs.append((rec, None))

    if not pairs:
        return None, None, "no-name-match"

    # 有时长的按接近程度升序;缺时长的垫底(宁可要能校验的)
    with_dur = sorted([p for p in pairs if p[1] is not None], key=lambda p: p[1])
    for rec, diff in with_dur + [p for p in pairs if p[1] is None]:
        if diff is None:
            return rec, None, "unknown-dur"
        if diff <= tol_strong:
            return rec, diff, "strong"
        if diff <= tol_loose:
            return rec, diff, "loose"
    return None, None, "dur-mismatch"


def lyrics_of(rec: dict) -> tuple[str | None, str]:
    """取歌词文本。返回 (文本, 来源标记 synced|plain|none)。

    同步歌词优先:播放器只认 LRC 时间标签(见模块 docstring)。
    """
    synced = (rec.get("syncedLyrics") or "").strip()
    if synced:
        return synced, "synced"
    plain = (rec.get("plainLyrics") or "").strip()
    if plain:
        return plain, "plain"
    return None, "none"


# ===== 繁简转换 =====

try:
    from opencc import OpenCC

    _T2S = OpenCC("t2s")
except Exception:  # noqa: BLE001 缺库不该让整批补录失败
    _T2S = None


def to_simplified(text: str) -> tuple[str, bool]:
    """繁体转简体。返回 (文本, 是否真的转换了)。缺 opencc 时原样返回。"""
    if _T2S is None:
        return text, False
    return _T2S.convert(text), True


# ===== 复核清单 =====

_TS_ANY = re.compile(r"\[\d{1,2}:\d{1,2}(?:[.:]\d{1,3})?\]")


def first_line(text: str, limit: int = 40) -> str:
    """取歌词第一行有效文本(去 LRC 时间标签),给复核清单作肉眼判据。"""
    for ln in _TS_ANY.sub("", text).splitlines():
        ln = ln.strip()
        if ln:
            return ln[:limit]
    return ""


def write_review_md(review: list[dict], path: Path, tol_loose: float,
                    no_valid: dict[str, str]) -> None:
    """把待复核项写成 Markdown(给人看,所以入库到 docs/)。"""
    def cell(s, n: int = 30) -> str:
        return str(s or "").replace("|", "\\|")[:n]

    source_cn = {"synced": "带时间轴", "plain": "纯文本"}

    out = [
        "# lrclib 歌词补录 · 待复核清单",
        "",
        "> 本文件由 `server/scripts/enrich_lyrics.py` 生成,请勿手工编辑;"
        "重新运行脚本会覆盖它。",
        "",
        "## 这份清单是什么",
        "",
        "给缺歌词的歌补录时,按 `|本库时长 − lrclib 时长|` 分档:",
        "",
        f"- **strong(≤ {TOL_STRONG:.0f}s)**:同一录音/母带,已自动写入。",
        f"- **loose(≤ {tol_loose:.0f}s)**:大概率是同一首歌的不同录音,"
        "即本清单。**默认不写入** —— 因为已实测出时长能对上、其实是另一首歌的情况:"
        "`cn134 小星星` 命中的是苏打绿的同名创作曲,歌词内容与儿歌毫无关系。",
        "",
        "每条都附了 lrclib 的歌词首行,用它就能判断是不是同一首歌。",
        "",
        "## 确认后怎么采纳",
        "",
        "逐条过目、确认是同一首歌之后,一次性全部写入(不重新请求 lrclib):",
        "",
        "```bash",
        "server/.venv/Scripts/python.exe server/scripts/enrich_lyrics.py \\",
        "    --no-fetch --apply-loose --rebuild-json",
        "```",
        "",
        "已确认**不是**本曲的,请把歌曲 id 加进 `server/scripts/enrich_lyrics.py` 的",
        "`NO_VALID_MATCH`,脚本会把该曲整首排除,不再出现在本清单里。",
        "",
    ]

    if no_valid:
        out += [
            "## 已确认 lrclib 无正主、已排除的歌曲",
            "",
            "| 歌曲 id | 原因 |",
            "|---------|------|",
        ]
        out += [f"| `{k}` | {v} |" for k, v in sorted(no_valid.items())]
        out.append("")

    out += [
        f"## 待复核({len(review)} 首)",
        "",
        "| # | 歌曲 | 本库时长 | lrclib 命中 | lrclib 歌手 | 时长差 | 歌词 | 首行 |",
        "|---|------|---------|-------------|-------------|--------|------|------|",
    ]
    for i, r in enumerate(review, 1):
        out.append(
            f"| {i} | `{r['id']}` {cell(r['name'], 20)} "
            f"| {r['duration']:.1f}s "
            f"| {cell(r['lrclibTrack'])} "
            f"| {cell(r['lrclibArtist'], 16)} "
            f"| {r['durationDiff']:+.2f}s "
            f"| {source_cn.get(r['source'], r['source'])} "
            f"| {cell(r['firstLine'], 34)} |"
        )
    out.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out), encoding="utf-8")


# ===== 主流程 =====


def load_cache(path: Path) -> dict:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(path: Path, cache: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


def collect(targets: list[tuple[str, str]], cache: dict, cache_path: Path) -> None:
    """把所有目标歌曲的搜索结果灌进 cache(已有成功记录则跳过)。"""
    total = len(targets)
    ok = empty = failed = 0
    for i, (sid, name) in enumerate(targets, 1):
        cached = cache.get(sid)
        if cached and cached.get("_status") == "ok":
            ok += 1
            continue

        data, status = search_track(name)
        if status == "ok":
            cache[sid] = {"name": name, "_status": "ok", "results": data}
            ok += 1
            if not data:
                empty += 1
        else:
            cache[sid] = {"name": name, "_status": status, "results": None}
            failed += 1
            print(f"  [{i}/{total}] 请求失败 {sid} {name} -> {status}", flush=True)

        if i % 25 == 0:
            save_cache(cache_path, cache)
            print(f"  [{i}/{total}] 有结果 {ok - empty} / 空 {empty} / 失败 {failed}", flush=True)
        time.sleep(REQUEST_DELAY)

    save_cache(cache_path, cache)
    print(f"采集完成: 有结果 {ok - empty}, 查无此歌 {empty}, 请求失败 {failed}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="用 lrclib 为缺歌词的歌曲补录歌词")
    ap.add_argument("--db", default=str(DB_PATH), help="SQLite 库路径")
    ap.add_argument("--cache", default=str(DEFAULT_CACHE), help="搜索结果缓存路径")
    ap.add_argument("--dry-run", action="store_true", help="只报告,不写库")
    ap.add_argument("--no-fetch", action="store_true",
                    help="只用缓存做匹配,不请求 lrclib(离线调门限/复查时用)")
    ap.add_argument("--apply-loose", action="store_true",
                    help="把 loose 档(时长差 <= tol-loose)也写入;默认只进复核清单")
    ap.add_argument("--tol-strong", type=float, default=TOL_STRONG, help="strong 档时长差上限(秒)")
    ap.add_argument("--tol-loose", type=float, default=TOL_LOOSE, help="loose 档时长差上限(秒)")
    ap.add_argument("--no-t2s", action="store_true",
                    help="不做繁体转简体(lrclib 的中文歌词多为繁体)")
    ap.add_argument("--rebuild-json", action="store_true",
                    help="写库后同步重建仓库根 data/songs.json")
    args = ap.parse_args()

    if not args.no_t2s and _T2S is None:
        print("! 未安装 opencc,歌词将保留繁体原文(本库其余歌词是简体)。安装方式:")
        print("  server/.venv/Scripts/python.exe -m pip install opencc-python-reimplemented\n")

    db_path = Path(args.db)
    cache_path = Path(args.cache)

    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    targets = [
        (r["id"], r["name"], r["duration"])
        for r in db.execute(
            "SELECT id, name, duration FROM songs "
            "WHERE lyric IS NULL OR trim(lyric) = '' ORDER BY id"
        )
    ]
    print(f"缺歌词歌曲: {len(targets)} 首")

    cache = load_cache(cache_path)
    print(f"已有缓存: {len(cache)} 条 -> {cache_path}")
    if args.no_fetch:
        print("--no-fetch:跳过采集,仅用缓存匹配\n")
    else:
        print("\n=== 采集 lrclib ===")
        collect([(sid, name) for sid, name, _ in targets], cache, cache_path)

    # 匹配
    print(f"\n=== 匹配(strong <= {args.tol_strong}s, loose <= {args.tol_loose}s)===")
    accepted: list[tuple] = []   # (id, name, lyric, source, diff, rec)
    review: list[dict] = []
    stats = {"strong": 0, "loose": 0, "no-name-match": 0, "dur-mismatch": 0,
             "unknown-dur": 0, "no-result": 0, "fetch-failed": 0, "no-lyric": 0,
             "no-valid-match": 0}

    for sid, name, dur in targets:
        entry = cache.get(sid) or {}
        if entry.get("_status") != "ok" or entry.get("results") is None:
            stats["fetch-failed"] += 1
            continue
        results = entry["results"]
        if not results:
            stats["no-result"] += 1
            continue
        # 已人工确认 lrclib 里没有正主的歌:整首排除,不写也不进复核清单
        if sid in NO_VALID_MATCH:
            stats["no-valid-match"] += 1
            continue

        rec, diff, tier = pick_candidate(name, dur, results,
                                        args.tol_strong, args.tol_loose)
        if rec is None:
            stats[tier] = stats.get(tier, 0) + 1
            continue

        text, source = lyrics_of(rec)
        if text is None:
            stats["no-lyric"] += 1
            continue

        if not args.no_t2s:
            text = to_simplified(text)[0]

        stats[tier] += 1
        info = {
            "id": sid, "name": name, "duration": dur,
            "lrclibId": rec.get("id"), "lrclibTrack": rec.get("trackName"),
            "lrclibArtist": rec.get("artistName"), "lrclibAlbum": rec.get("albumName"),
            "lrclibDuration": rec.get("duration"), "durationDiff": diff,
            "tier": tier, "source": source, "lyricChars": len(text),
            "firstLine": first_line(text),
        }
        if tier == "strong" or args.apply_loose:
            accepted.append((sid, name, text, source, diff, rec))
        else:
            review.append(info)

    print("--- 分层结果 ---")
    for k, v in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {k:14s} {v}")

    synced = sum(1 for a in accepted if a[3] == "synced")
    print(f"\n准备写入 {len(accepted)} 首(带时间轴 {synced}, 仅纯文本 {len(accepted) - synced})")
    if review:
        print(f"进复核清单 {len(review)} 首(未写入)")

    if review:
        review_path = Path(str(REVIEW_PATH))
        write_review_md(review, review_path, args.tol_loose, NO_VALID_MATCH)
        print(f"复核清单已写入: {review_path}")
        print("抽样(需人工确认是否同一首歌):")
        for r in review[:15]:
            print(f"  {r['id']} {r['name']} our={r['duration']:.1f}s | "
                  f"{r['lrclibTrack']!r}/{r['lrclibArtist']!r} "
                  f"dur={r['lrclibDuration']} diff={r['durationDiff']:.2f} "
                  f"{r['source']} {r['lyricChars']}字 | 首行 {r['firstLine']}")

    if args.dry_run:
        print("\n[dry-run] 未写库。抽样预览:")
        for sid, name, text, source, diff, rec in accepted[:5]:
            print(f"\n--- {sid} {name} ({source}, diff={diff:.2f}, "
                  f"{rec.get('trackName')!r}/{rec.get('artistName')!r})")
            print("\n".join(text.splitlines()[:6]))
        return

    if not accepted:
        print("\n无可写入内容,退出。")
        return

    # 只补不改:再次确认目标仍是空歌词,避免覆盖期间被别的流程写过的数据
    cur = db.cursor()
    written = 0
    for sid, name, text, source, diff, rec in accepted:
        row = cur.execute("SELECT lyric FROM songs WHERE id = ?", (sid,)).fetchone()
        if row is None:
            continue
        if row["lyric"] and row["lyric"].strip():
            print(f"  跳过(已有歌词): {sid} {name}")
            continue
        cur.execute("UPDATE songs SET lyric = ? WHERE id = ?", (text, sid))
        written += 1
    db.commit()

    left = db.execute(
        "SELECT COUNT(*) FROM songs WHERE lyric IS NULL OR trim(lyric) = ''"
    ).fetchone()[0]
    db.close()
    print(f"\n写库完成: 成功 {written} 首;剩余仍缺歌词 {left} 首")

    if args.rebuild_json:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from songs_json import rebuild

        n_cat, n_song = rebuild(db_path, PROJECT_DIR / "data" / "songs.json")
        print(f"已同步 data/songs.json: {n_cat} 大类, {n_song} 首")


if __name__ == "__main__":
    main()
