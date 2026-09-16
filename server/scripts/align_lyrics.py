"""给只有纯文本歌词的歌补出时间轴。

背景
----
lrclib 对很多歌只提供 plainLyrics(无时间戳,见 enrich_lyrics.py)。播放器
src/utils/lyric.ts 的 parseLyric() 只认 [mm:ss] 标签,纯文本会整行丢弃并退回
「暂无歌词」。本脚本给这类歌补上时间轴。

为什么不用「整段文本强制对齐」
------------------------------
最初的做法是把整段歌词丢给 stable-ts 的 align() 做 forced alignment。
实测(归入 --method forced,已降级为备选)**这条路对本曲库不成立**:

  以 cn003《爸爸妈妈听我说》为例,Whisper 自己转写出的真实结构是
    V(30-49s) → V(59-79s) → C(80-104s) → 一段口白(107-123s) → V(124-144s) → C(144-189s)
  而 lrclib 的纯文本歌词是 V-C-V-C 顺序,且完全没有那段口白。
  两者**结构不同构**,按顺序对齐必然错位:前 4 行还对得上(误差 <0.2s),
  到第 5 行就整体错位。cn045《吉祥三宝》更隐蔽 —— 34 行"零退化段"看似完美,
  实际全挤在 0-80s,而音频有 210s。

  结论:错位不是参数问题,调 tol / 换模型都治不了。所以原先脚本里"把退化段均分
  填空"的做法只会产出**看起来能用其实是编的**时间轴,已删除。

现在的方法(--method occurrence,默认)
------------------------------------
不假设歌词与音频同构,改为「让音频自己说话」:

  1. 用 Whisper 转写音频(只要时间轴,不要它的文本),拿到 word 级时间戳,
     压成一个「字符 -> 时间」索引;
  2. 对每一句歌词,在整段转写里滑动窗口找最相似的片段,取相似度达标的**所有**
     出现位置(同一句唱 3 遍就得到 3 个时间);
  3. 输出时用**我们自己的歌词原文**(不是 ASR 文本,避免识别错字),只借它的时间。

这样重复段、口白穿插、顺序不一致都能自动处理,且产出的每个时间都来自真实演唱,
不是均分出来的。

★ 比较时必须把两边都归一到**拼音**,不能按字形比(见 norm()):Whisper 的中文输出
  是繁体,本库歌词是简体,且它的错字几乎都是同音错。实测同一对句子:
    小白菜呀 / 小白彩雅   字形 0.500 → 拼音 1.000
    端起碗来 / 斷雞萬來   字形 0.000 → 拼音 0.917
  按字形匹配这两句都会被判成「没唱这句」,覆盖率直接掉到 18%。

已知边界
--------
- 仍依赖转写质量:若某句被 ASR 错得离谱(相似度低于 --min-ratio)会漏掉,
  脚本会报告每首的覆盖率,覆盖率过低的不写库(需 --force 强写)。
- 只处理**已有纯文本歌词**的歌,不生成新歌词 —— ASR 文本有错字(实测把
  "消化不了"听成"笑话不良"),不能当歌词用。

环境准备(与 server/.venv 无关,需单独一套;torch 约 1GB)
--------------------------------------------------------
  python -m venv .workbuddy/venv-align
  .workbuddy/venv-align/Scripts/python.exe -m pip install \
      --index-url https://download.pytorch.org/whl/cpu torch torchaudio
  .workbuddy/venv-align/Scripts/python.exe -m pip install stable-ts faster-whisper pypinyin
注意 stable-ts 默认**不含** faster-whisper(它是可选 extra),必须单独装,
否则 load_faster_whisper 用不了。pypinyin 用于把歌词与转写都归一到拼音再比相似度
(见 norm() 的说明);缺这个库脚本仍能跑,只是同音错字会漏句。

模型下载:本机 huggingface.co DNS 不通,需走镜像;且新版 huggingface_hub 默认
走 Xet 协议,hf-mirror 不代理它的 CAS 端点(会返 401),必须关掉 Xet:
  HF_ENDPOINT=https://hf-mirror.com HF_HOME=<repo>/.workbuddy/hf HF_HUB_DISABLE_XET=1
(脚本已内置这三个默认值,一般不用手动 export。)

用法
----
  # 预览全部待处理的纯文本歌词歌曲(默认 --limit 1,便于先抽查)
  .workbuddy/venv-align/Scripts/python.exe server/scripts/align_lyrics.py --limit 5
  # 指定几首
  .workbuddy/venv-align/Scripts/python.exe server/scripts/align_lyrics.py --ids cn003,cn195
  # 确认可用后写库并同步 data/songs.json
  .workbuddy/venv-align/Scripts/python.exe server/scripts/align_lyrics.py --limit 5 --write --rebuild-json
"""
import argparse
import difflib
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


def _hf_hub_dir() -> Path:
    return Path(os.environ["HF_HOME"]) / "hub"


def _model_cached(model: str) -> bool:
    """模型是否已在本机缓存。

    faster-whisper 的 <size> 对应 HF 上的 Systran/faster-whisper-<size>,
    本地缓存目录是 hub/models--Systran--faster-whisper-<size>/snapshots/<rev>。
    """
    d = _hf_hub_dir() / f"models--Systran--faster-whisper-{model}" / "snapshots"
    return d.is_dir() and any(p.is_dir() for p in d.iterdir())


# 已缓存就必须走离线模式:huggingface_hub 每次都会先向 API 要 repo_info 做校验,
# 本机走代理时这个校验会间歇性 502,把本来能跑的推理整批打断。
# 仅在缓存确实存在时开,保证换机器/换模型仍能正常下载。
if _model_cached(MODEL):
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
COMPUTE = os.environ.get("ALIGN_COMPUTE", "int8")
LANG = os.environ.get("ALIGN_LANG", "zh")

_TS = re.compile(r"\[\d{1,2}:\d{1,2}(?:[.:]\d{1,3})?\]")
# 只保留中日韩表意文字、假名、拉丁字母与数字,去掉空格/标点/装饰符
_KEEP = re.compile(r"[^\w\u3040-\u30ff\u4e00-\u9fff]+")

try:
    from pypinyin import lazy_pinyin

    _PY_AVAILABLE = True
except Exception:  # noqa: BLE001 缺库降级为按字形匹配,不中断
    _PY_AVAILABLE = False

_PY_CACHE: dict[str, str] = {}


def _pinyin(ch: str) -> str:
    v = _PY_CACHE.get(ch)
    if v is None:
        v = _PY_CACHE[ch] = "".join(lazy_pinyin(ch))
    return v


def norm(s: str) -> str:
    """规范化成匹配用的字符序列。

    中文转拼音 —— 实测 ASR 的错字绝大多数是**同音/近音错**。以 cn003 的一句为例:
      歌词 "学得太多学得太杂消化不了"
      转写 "学的太多学的太杂笑话不良"   ← 得/的、消化/笑话、了/良 全是同音错
    按字形算相似度只有 0.54(低于任何合理门槛,会被判成「没唱这句」);
    转拼音后变成 0.88,稳稳命中。非中文(拉丁字母/数字/西里尔字母)原样保留。
    """
    s = _KEEP.sub("", s or "").lower()
    if not s or not _PY_AVAILABLE:
        return s
    return "".join(_pinyin(ch) if "\u4e00" <= ch <= "\u9fff" else ch for ch in s)


# 一行歌词认定为「在音频里出现过」的相似度下限。
#
# 门槛实测标定:Whisper 的中文输出是**繁体**,本库歌词是简体,且错字多为同音错,
# 所以按拼音比对而不是按字形。以 cn195《小白菜》为例(左=字形相似,右=拼音相似):
#   小白菜呀 / 小白彩雅      0.500 → 1.000
#   地里黄呀 / 滴滴黃雅      0.000 → 0.909
#   端起碗来 / 斷雞萬來      0.000 → 0.917
#   三两岁上 / 兩三歲雅      0.250 → 0.621   ← 最低的一个(ASR 把「三两」听成「兩三」)
# 取 0.6:既能收住最低那条,又因为拼音串长(每行 10+ 字符)不容易撞到不相干的句子。
MIN_RATIO = 0.6
# 占位冲突判定时给区间留的余量(字符)。必须是 0:歌词行在转写里是**紧挨着**的
# (「跟着爹爹」占 [49,61)、「好好地过呀」占 [61,72))),留任何正数余量都会把
# 相邻的两句判成冲突,导致后一句被整句丢掉 —— 实测这个值设成 4 时,
# cn195 有 6/17 句被这样误杀。同一句被反复命中由「区间重叠」本身就能挡住。
MIN_GAP_CHARS = 0
# 覆盖率(找到时间轴的行数 / 总行数)低于此值不写库
MIN_COVERAGE = 0.8


def is_plain(lyric: str) -> bool:
    """是否是无时间戳的纯文本歌词。"""
    return bool(lyric and lyric.strip()) and not _TS.search(lyric)


# ===== occurrence 法:把歌词行映射到转写时间轴 =====


def build_char_index(segments) -> tuple[str, list[tuple[float, float]]]:
    """把所有 word 级时间戳压成 (整段字符, 每字符对应的时间区间)。

    转写文本只用来定位,不参与输出。以字符为单位做索引,这样歌词行跨
    segment、或被切碎成多个 word 都不影响匹配。
    """
    chars: list[str] = []
    spans: list[tuple[float, float]] = []
    for seg in segments:
        for w in (getattr(seg, "words", None) or []):
            t = norm(w.word)
            if not t:
                continue
            chars.append(t)
            spans.extend([(float(w.start), float(w.end))] * len(t))
    return "".join(chars), spans


def score_line(line_norm: str, full: str, min_ratio: float) -> list[tuple[float, int, int]]:
    """给一行歌词在整段转写上滑窗打分,返回达标的窗口 [(相似度, 起字符, 止字符)]。"""
    L = len(line_norm)
    if L < 2 or len(full) < 2:
        return []
    # 拼音串的音节长度不齐(2~6 字符),唱的时候还可能被拉长/吞字,
    # 所以多试几个宽度取最高分,而不是只按字符数等比取值。
    widths = sorted({w for w in (int(L * 0.6), int(L * 0.8), L, int(L * 1.2), int(L * 1.5))
                     if w >= 2})
    hits: list[tuple[float, int, int]] = []
    for wlen in widths:
        if wlen > len(full):
            continue
        for off in range(0, len(full) - wlen + 1):
            r = difflib.SequenceMatcher(None, line_norm, full[off:off + wlen]).ratio()
            if r >= min_ratio:
                hits.append((r, off, off + wlen))
    return hits


def assign_lines(lyric: str, full: str, spans,
                 min_ratio: float) -> tuple[list[tuple[float, str]], list[str]]:
    """把整段转写「切分」给歌词的各个句子。

    返回 ([(开始秒, 歌词原文), ...] 按时间升序, 没能定位到的句子列表)。

    这里的关键是**全局**分配,而不是逐句各找各的:把所有句子的候选窗口放在一起,
    按相似度从高到低占位,同一段音频只归最像的那一句。

    逐句独立匹配行不通 —— 儿歌里大量 3~4 字的短句(「亲娘呀」「我喝汤呀」),
    它们的拼音串短,在整首歌里到处都能凑到 0.6 以上。实测 cn195《小白菜》
    逐句匹配会输出 69 行乱麻(「亲娘呀」一个人就对上十几处);全局分配后
    每段音频归位给最像的那句,重复段仍会保留多份(那是对的,副歌确实唱了多遍)。

    另一个要点:按「规范化后的文本」去重后再匹配。儿歌同一句歌词常在文本里重复
    列出(cn003 的 18 行里只有 7 句不同),不去重就会成倍重复输出。
    """
    lines = [l.strip() for l in lyric.splitlines() if l.strip()]
    uniq: dict[str, str] = {}          # 规范化文本 -> 首次出现的原文
    for line in lines:
        k = norm(line)
        if len(k) >= 2 and k not in uniq:
            uniq[k] = line

    hits: list[tuple[float, int, int, str]] = []
    for k, line in uniq.items():
        for r, a, b in score_line(k, full, min_ratio):
            hits.append((r, a, b, line))
    if not hits:
        return [], list(uniq.values())

    # 全局非极大值抑制:相似度高的先占位,与已占位区间重叠的一律丢弃
    hits.sort(key=lambda h: -h[0])
    kept: list[tuple[float, int, int, str]] = []
    for r, a, b, line in hits:
        if any(not (b <= ka - MIN_GAP_CHARS or a >= kb + MIN_GAP_CHARS)
               for _r, ka, kb, _l in kept):
            continue
        kept.append((r, a, b, line))
    kept.sort(key=lambda h: h[1])

    # 每段取它自己的起止(止=该窗口最后一个字符所在 word 的结束时刻)
    raw: list[tuple[float, float, str]] = []
    for _r, a, b, line in kept:
        if a >= len(spans):
            continue
        raw.append((spans[a][0], spans[min(b, len(spans)) - 1][1], line))

    # 中文的 word 粒度很粗,一个 word 里常挤着两句歌词(如 "斷雞萬來淚汪汪雅"),
    # 它们会拿到完全相同的时间戳,播放器只认最后一条,前一句就被吞掉。
    # 在**该 word 自身的真实时长内**按顺序摊开 —— 区间很小(<1s),不是凭空编时间。
    entries: list[tuple[float, str]] = []
    i = 0
    while i < len(raw):
        j = i
        while j + 1 < len(raw) and abs(raw[j + 1][0] - raw[i][0]) < 1e-6:
            j += 1
        if j > i:
            t0 = raw[i][0]
            end = max(r[1] for r in raw[i:j + 1])
            step = (end - t0) / (j - i + 1)
            for k in range(i, j + 1):
                entries.append((t0 + step * (k - i), raw[k][2]))
        else:
            entries.append((raw[i][0], raw[i][2]))
        i = j + 1

    claimed = {line for _r, _a, _b, line in kept}
    missed = [line for line in uniq.values() if line not in claimed]

    # 极少数情况下摊开后仍会撞在同一时刻(word 时间戳的 start==end),
    # 保证时间轴严格递增,否则播放器只会显示最后一条
    for i in range(1, len(entries)):
        if entries[i][0] <= entries[i - 1][0]:
            entries[i] = (entries[i - 1][0] + 0.01, entries[i][1])
    return entries, missed


def to_lrc(entries: list[tuple[float, str]]) -> str:
    lines = []
    for start, text in entries:
        m, s = divmod(start, 60)
        lines.append(f"[{int(m):02d}:{s:05.2f}] {text}")
    return "\n".join(lines)


# ===== forced 法(备选,见模块 docstring:对本曲库不成立) =====


def align_forced(model, audio: Path, lyric: str) -> list[tuple[float, str]]:
    """整段文本强制对齐。仅用于对照/个别结构规整的歌。"""
    res = model.align(str(audio), lyric, language=LANG, original_split=True)
    return [(float(s.start), (s.text or "").strip()) for s in res.segments
            if (s.text or "").strip()]


# ===== 主流程 =====


def main() -> None:
    ap = argparse.ArgumentParser(description="给纯文本歌词补时间轴")
    ap.add_argument("--db", default=str(DB_PATH))
    ap.add_argument("--ids", help="逗号分隔的歌曲 id;不给则按库顺序取")
    ap.add_argument("--limit", type=int, default=1, help="最多处理几首(默认 1,便于先抽查)")
    ap.add_argument("--method", choices=["occurrence", "forced"], default="occurrence",
                    help="occurrence=按句在转写里找所有出现位置(默认);forced=整段强制对齐")
    ap.add_argument("--min-ratio", type=float, default=MIN_RATIO, help="行匹配相似度下限")
    ap.add_argument("--min-coverage", type=float, default=MIN_COVERAGE,
                    help="覆盖率低于此值不写库(需 --force 强写)")
    ap.add_argument("--force", action="store_true", help="覆盖率不达标也写库")
    ap.add_argument("--write", action="store_true", help="写库(默认只出预览)")
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
        print("没有需要对齐的纯文本歌词歌曲")
        return
    print(f"待处理 {len(rows)} 首(方法 {args.method})\n")

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
            print(f"[{i}/{len(rows)}] {sid} 音频缺失,跳过: {audio}")
            continue
        lines = [l.strip() for l in row["lyric"].splitlines() if l.strip()]
        print(f"[{i}/{len(rows)}] {sid} {row['name']} / {row['artist']} / "
              f"{row['duration']:.0f}s / {len(lines)} 行")

        t0 = time.time()
        try:
            if args.method == "forced":
                entries = align_forced(model, audio, row["lyric"])
                missed, uniq = [], len(lines)
            else:
                res = model.transcribe(str(audio), language=LANG,
                                       word_timestamps=True, vad=True)
                full, spans = build_char_index(res.segments)
                entries, missed = assign_lines(row["lyric"], full, spans,
                                               args.min_ratio)
                uniq = len({norm(l) for l in lines if len(norm(l)) >= 2})
        except Exception as e:  # noqa: BLE001
            print(f"  处理异常: {repr(e)[:140]}")
            continue
        elapsed = time.time() - t0

        found = uniq - len(missed)
        coverage = found / uniq if uniq else 0.0
        print(f"  用时 {elapsed:.1f}s ({elapsed / max(row['duration'], 1):.2f}x)  "
              f"输出 {len(entries)} 行  "
              f"覆盖 {found}/{uniq} 个不同句 = {coverage * 100:.0f}%")
        if missed:
            print(f"  未定位到({len(missed)} 句): " + " | ".join(m[:18] for m in missed[:5]))

        lrc = to_lrc(entries)
        out = PROJECT_DIR / ".workbuddy" / f"_align_{sid}.lrc"
        out.write_text(lrc, encoding="utf-8")
        print(f"  预览 -> {out}")
        results.append((sid, row["name"], lrc, coverage, len(entries), len(missed)))

    ok = [r for r in results if r[3] >= args.min_coverage]
    bad = [r for r in results if r[3] < args.min_coverage]
    if bad:
        print(f"\n覆盖率不达标 {len(bad)} 首(需 --force 才写): "
              + ", ".join(f"{r[0]}({r[3] * 100:.0f}%)" for r in bad))

    if not args.write:
        print(f"\n[dry-run] 未写库,以上 {len(results)} 首仅出预览。确认可用后加 --write。")
        return

    target = results if args.force else ok
    written = 0
    for sid, _name, lrc, _cov, _n, _m in target:
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
