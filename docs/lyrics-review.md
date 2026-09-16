# lrclib 歌词补录 · 待复核清单

> 本文件由 `server/scripts/enrich_lyrics.py` 生成,请勿手工编辑;重新运行脚本会覆盖它。

## 这份清单是什么

给缺歌词的歌补录时,按 `|本库时长 − lrclib 时长|` 分档:

- **strong(≤ 3s)**:同一录音/母带,已自动写入。
- **loose(≤ 8s)**:大概率是同一首歌的不同录音,即本清单。**默认不写入** —— 因为已实测出时长能对上、其实是另一首歌的情况:`cn134 小星星` 命中的是苏打绿的同名创作曲,歌词内容与儿歌毫无关系。

每条都附了 lrclib 的歌词首行,用它就能判断是不是同一首歌。

## 确认后怎么采纳

逐条过目、确认是同一首歌之后,一次性全部写入(不重新请求 lrclib):

```bash
server/.venv/Scripts/python.exe server/scripts/enrich_lyrics.py \
    --no-fetch --apply-loose --rebuild-json
```

已确认**不是**本曲的,请把歌曲 id 加进 `server/scripts/enrich_lyrics.py` 的
`NO_VALID_MATCH`,脚本会把该曲整首排除,不再出现在本清单里。

## 已确认 lrclib 无正主、已排除的歌曲

| 歌曲 id | 原因 |
|---------|------|
| `cn134` | 命中全是同名流行曲(苏打绿/杨千嬅/张震岳/万芳/王心凌),没有儿歌《小星星》 |
| `en003` | 本曲属 children-english(早教英语),命中全是同名的中文/日文流行曲 |

## 待复核(12 首)

| # | 歌曲 | 本库时长 | lrclib 命中 | lrclib 歌手 | 时长差 | 歌词 | 首行 |
|---|------|---------|-------------|-------------|--------|------|------|
| 1 | `cn021` 大王叫我来巡山 | 234.4s | 赵英俊 - 大王叫我来巡山 | nobody | +7.57s | 带时间轴 | 太阳对我眨眼睛 |
| 2 | `cn023` DO RE MI | 140.0s | Do-Re-Mi | Dinah Shore | +5.96s | 纯文本 | Do, a deer, a female deer |
| 3 | `cn082` 让我们荡起双桨 | 136.2s | 让我们荡起双桨 | 小蓓蕾组合 | +3.54s | 带时间轴 | 让我们荡起双桨 |
| 4 | `cn090` 生日快乐 | 126.0s | 生日快乐 | 卓依婷 | +3.60s | 带时间轴 | 祝你生日快乐 |
| 5 | `cn109` 外婆的澎湖湾 | 175.8s | 外婆的澎湖湾 | 潘安邦 | +5.31s | 带时间轴 | 晚风轻拂澎湖湾 白浪逐沙滩 |
| 6 | `cn112` 小螺号 | 228.2s | 小螺号 | 王雪晶 | +6.22s | 带时间轴 | 小螺号 嘀嘀嘀吹 |
| 7 | `cn155` 卓玛 | 217.7s | 卓玛 | 降央卓玛 | +3.06s | 带时间轴 | 草原的风 草原的雨 草原的羊群 |
| 8 | `cn196` 小蜜蜂 | 135.8s | 小蜜蜂 | 陳美齡 | +7.29s | 带时间轴 | 嗡嗡嗡 小蜜蜂 |
| 9 | `cn514` 童年 | 220.3s | 童年 | 罗大佑 | +7.69s | 带时间轴 | 池塘边的榕树上 |
| 10 | `cn539` Row Row Row Your Boa | 80.8s | Row, Row, Row Your Boat | Toddler Tunes | +5.85s | 带时间轴 | Row, row, row your boat |
| 11 | `en054` a sailor went to sea | 36.0s | A Sailor Went to Sea | The Wiggles | +3.03s | 带时间轴 | A sailor went to sea, sea, sea |
| 12 | `en079` Up On The Housetop | 89.4s | Up on the Housetop | Various Artists | +4.43s | 纯文本 | Up on the housetop, reindeer pause |
