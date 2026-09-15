"""用 stable-ts 强制对齐,给只有纯文本歌词的歌补出时间轴。

背景
----
lrclib 对很多歌只提供 plainLyrics(无时间戳,见 enrich_lyrics.py)。播放器
src/utils/lyric.ts 的 parseLyric() 只认 [mm:ss] 标签,纯文本会整行丢弃并退回
「暂无歌词」。本脚本把已知歌词当作已知脚本,让 Whisper 只求每条歌词的起止
时间(forced alignment),不重新识别文本。

⚠ 现状:能跑通,但输出需要清理,未接入曲库数据(默认只出预览,不写库)
--------------------------------------------------------------------
实测(torch 2.14 CPU + faster-whisper small int8):
- 速度 0.05~0.06x 实时,205s / 274s 的歌各约 12~14s,模型加载后再跑只要 2~3s。
- 必须传 original_split=True。否则 stable-ts 会把整段文本按**标点**重切,
  而歌词换行处通常没有标点,结果是好几行并成一段、还会出现
  "[0.80-1.46] 你" 这种碎片。开了之后行与段能 1:1 对上。
- **质量不稳**:对齐在「歌词与音频一致」的前段很准(如 cn195《小白菜》前 18 行
  每行约 3s、整齐递进),但一进副歌/重复段就崩 —— 实测 cn003 有 3/18 段、
  cn195 有 6/30 段对齐失败,塌成 0 时长(如 [60.32-60.32])。
  原因是 lrclib 的纯文本歌词往往**省略了重复段**,文本与音频对不上,
  对齐器丢了位置。
因此本脚本做了一轮清理(--clean,默认开):把连续退化的段落按
「上一正常段结束 → 下一正常段结束」的区间均分,让每一行都有可见时长。
这是**近似时间轴**,不是真实演唱时刻,只在没有更好来源时使用。

要正式启用,建议先用 --limit 抽查若干首再决定是否 --write。

环境准备(与 server/.venv 无关,需单独一套;torch 约 1GB)
--------------------------------------------------------
  python -m venv .workbuddy/venv-align
  .workbuddy/venv-align/Scripts/python.exe -m pip install \
      --index-url https://download.pytorch.org/whl/cpu torch torchaudio
  .workbuddy/venv-align/Scripts/python.exe -m pip install stable-ts faster-whisper
注意 stable-ts 默认**不含** faster-whisper(它是可选 extra),必须单独装,
否则 load_faster_whisper 用不了。

模型下载:本机 huggingface.co DNS 不通,需走镜像;且新版 huggingface_hub 默认
走 Xet 协议,hf-mirror 不代理它的 CAS 端点(会返 401),必须关掉 Xet:
  HF_ENDPOINT=https://hf-mirror.com HF_HOME=<repo>/.workbuddy/hf HF_HUB_DISABLE_XET=1

用法
----
  # 单首预览(默认不写库)
  .workbuddy/venv-align/Scripts/python.exe server/scripts/align_lyrics.py --ids cn003
  # 抽查前 5 首纯文本歌词的歌
  .workbuddy/venv-align/Scripts/python.exe server/scripts/align_lyrics.py --limit 5
  # 确认可用后写库并同步 data/songs.json
  .workbuddy/venv-align/Scripts/python.exe server/scripts/align_lyrics.py --limit 5 --write --rebuild-json
"""
import argparse
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_DIR = Path(__file__).resolve().parents[2]
SERVER_DIR = PROJECT_DIR / "server"
DB_PATH = SERVER_DIR / "data" / "music.db"
STORAGE_ROOT = SERVER_DIR / "storage"

# 模型从 hf-mirror 拉,缓存放 F 盘(默认落 C 盘容易撑爆)
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HOME", str(PROJECT_DIR / ".workbuddy" / "hf"))
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

MODEL = os.environ.get("ALIGN_MODEL", "small")
COMPUTE = os.environ.get("ALIGN_COMPUTE", "int8")
LANG = os.environ.get("ALIGN_LANG", "zh")

_TS = re.compile(r"\[\d{1,2}:\d{1,2}(?:[.:]\d{1,3})?\]")
# 低于这个时长视为「对齐失败」的退化段
MIN_DUR = 0.2


def is_plain(lyric: str) -> bool:
    """是否是无时间戳的纯文本歌词。"""
    return bool(lyric and lyric.strip()) and not _TS.search(lyric)


def clean_segments(segs: list[tuple[float, float, str]]) -> tuple[list, int]:
    """把连续的退化段(时长过短)均分到可用的区间里。

    做法:找到一段「退化段 + 紧随其后的首个正常段」,用
    [上一正常段结束, 该正常段结束] 这段区间在它们之间均分。
    返回 (清理后的段, 被修正的行数)。
    """
    out = [list(s) for s in segs]
    fixed = 0
    i = 0
    n = len(out)
    while i < n:
        if out[i][1] - out[i][0] >= MIN_DUR:
            i += 1
            continue
        # 退化段的起点 i,向后找到第一个正常段 j
        j = i
        while j < n and out[j][1] - out[j][0] < MIN_DUR:
            j += 1
        if j >= n:
            # 尾部全是退化段:从上一正常段结束均分到音频末尾附近
            prev_end = out[i - 1][1] if i > 0 else 0.0
            span = max(prev_end + 1.0, prev_end * 1.05) - prev_end
            share = span / max(n - i, 1)
            for k in range(i, n):
                out[k][0] = prev_end + share * (k - i)
                out[k][1] = prev_end + share * (k - i + 1)
                fixed += 1
            break
        prev_end = out[i - 1][1] if i > 0 else out[i][0]
        end = out[j][1]
        share = max(end - prev_end, 0.0) / (j - i + 1)
        if share < MIN_DUR:  # 区间太窄,退化为均匀给一个最小可见时长
            share = MIN_DUR
        for k in range(i, j + 1):
            out[k][0] = prev_end + share * (k - i)
            out[k][1] = prev_end + share * (k - i + 1)
            fixed += 1
        i = j + 1
    return out, fixed


def to_lrc(segs: list) -> str:
    lines = []
    for start, _end, text in segs:
        text = (text or "").strip()
        if not text:
            continue
        m, s = divmod(start, 60)
        lines.append(f"[{int(m):02d}:{s:05.2f}] {text}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="用 stable-ts 给纯文本歌词补时间轴")
    ap.add_argument("--db", default=str(DB_PATH))
    ap.add_argument("--ids", help="逗号分隔的歌曲 id;不给则按库顺序取")
    ap.add_argument("--limit", type=int, default=1, help="最多处理几首(默认 1,便于先抽查)")
    ap.add_argument("--write", action="store_true", help="写库(默认只出预览)")
    ap.add_argument("--no-clean", action="store_true", help="不做退化段清理")
    ap.add_argument("--rebuild-json", action="store_true", help="写库后同步 data/songs.json")
    args = ap.parse_args()

    db = sqlite3.connect(args.db)
    db.row_factory = sqlite3.Row
    if args.ids:
        ids = [i.strip() for i in args.ids.split(",") if i.strip()]
        rows = [db.execute("SELECT * FROM songs WHERE id=?", (i,)).fetchone() for i in ids]
        rows = [r for r in rows if r]
        # 显式给了 id 就不再被 --limit 截断(limit 只用于「按库顺序取几首抽查」)
    else:
        rows = db.execute(
            "SELECT * FROM songs WHERE lyric IS NOT NULL AND trim(lyric) <> '' ORDER BY id"
        ).fetchall()
        rows = [r for r in rows if is_plain(r["lyric"])]
        rows = rows[: args.limit]
    rows = [r for r in rows if is_plain(r["lyric"])]
    if not rows:
        print("没有需要对齐的纯文本歌词歌曲"); return
    print(f"待对齐 {len(rows)} 首\n")

    import stable_whisper

    print(f"加载模型 {MODEL} ({COMPUTE}, cpu)...")
    t0 = time.time()
    model = stable_whisper.load_faster_whisper(MODEL, device="cpu", compute_type=COMPUTE)
    print(f"  就绪 {time.time() - t0:.1f}s\n")

    results = []
    for i, row in enumerate(rows, 1):
        sid = row["id"]
        audio = STORAGE_ROOT / row["audio_path"]
        if not audio.exists():
            print(f"[{i}/{len(rows)}] {sid} 音频缺失,跳过: {audio}"); continue
        lines = [l.strip() for l in row["lyric"].splitlines() if l.strip()]
        print(f"[{i}/{len(rows)}] {sid} {row['name']} / {row['artist']} / "
              f"{row['duration']:.0f}s / {len(lines)} 行")
        t0 = time.time()
        try:
            res = model.align(str(audio), row["lyric"], language=LANG, original_split=True)
        except Exception as e:  # noqa: BLE001
            print(f"  对齐异常: {repr(e)[:120]}"); continue
        elapsed = time.time() - t0
        segs = [(s.start, s.end, (s.text or "").strip()) for s in res.segments]
        degenerate = sum(1 for s in segs if s[1] - s[0] < MIN_DUR)
        print(f"  对齐 {elapsed:.1f}s ({elapsed / max(row['duration'], 1):.2f}x)  "
              f"段 {len(segs)} / 行 {len(lines)}  退化段 {degenerate}")

        if not args.no_clean:
            segs, fixed = clean_segments(segs)
            if fixed:
                print(f"  清理:修正 {fixed} 行(均分近似时间轴,非真实演唱时刻)")

        lrc = to_lrc(segs)
        out = PROJECT_DIR / ".workbuddy" / f"_align_{sid}.lrc"
        out.write_text(lrc, encoding="utf-8")
        print(f"  预览 -> {out}")
        results.append((sid, lrc, len(segs), len(lines)))

    if not args.write:
        print(f"\n[dry-run] 未写库,以上 {len(results)} 首仅出预览。确认可用后加 --write。")
        return

    written = 0
    for sid, lrc, _n, _ln in results:
        db.execute("UPDATE songs SET lyric=? WHERE id=?", (lrc, sid))
        written += 1
    db.commit()
    print(f"\n写库完成 {written} 首")
    if args.rebuild_json:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from songs_json import rebuild

        n_cat, n_song = rebuild(Path(args.db), PROJECT_DIR / "data" / "songs.json")
        print(f"已同步 data/songs.json: {n_cat} 大类, {n_song} 首")


if __name__ == "__main__":
    main()
