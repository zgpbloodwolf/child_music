# resource —— 原始资源档案层(raw)

本目录存放从各处(网络合集、购买、录制等)获取的、**未经整理**的原始音频源文件。

> 一句话规则:**本目录里的文件,只增、不改、不删、不重命名。**
> 分类、命名、去重由 AI 整理时处理,不在本目录手工做。

## 为什么保持原样(看起来乱也没关系)

resource 的职责是**忠实保管原始数据**,不是"整理好的曲库":

- **可追溯**:保留原始文件名与目录结构,随时能查到「这首歌来自哪个来源」(整理后的 songs.json 用 `originalPath` 字段回指本目录)。
- **可重放**:整理出错时,raw 层是回滚基准 —— 删掉工程产物重新整理即可,原始数据不受影响。
- **分类会变**:一首歌的归类会调整;分类是 songs.json 里的一行数据,不该靠移动文件来表达。
- **来源各异**:不同来源的命名规则、目录结构千差万别,AI 整理时能从文件名 / 路径识别。

所以目录里再乱也没关系。

## 如何加新资源

直接把新资源丢进来(压缩包请先解压)。按来源建个子目录便于自己区分也行,不建直接堆也行。**不需要**手动重命名 / 分类 / 去重 —— 那是 AI 整理步骤的事。

## 资源如何进入 App(当前已落地的数据流)

```
resource/  (raw,本目录;整目录不入库,仅本 README 入库)
   │ ① AI 整理:读文件名 + 语义分类(不写脚本)
   ▼
data/songs.json  (仓库根,0.41MB;4 大类 / 14 子类 / 1119 首)
   │ ② 导入:server/scripts/migrate_from_json.py → SQLite 三表 + 音频归位
   ▼
server/data/music.db  (SQLite;只存相对 storage 根的路径,不存域名)
   │ ③ FastAPI 下发 JSON:/api/categories、/api/songs、/api/songs/ids …
   ▼
App  (player / 各页面走 Repository 接口 = ApiCatalogRepository)
```

1. **AI 整理**:读本目录音频文件名 → 按语义判断分类、解析歌名 / 演唱者 → 生成 `data/songs.json`。结构为 `{大类: {"_info": …, 子类 key: {"_info": …, "songs": [...]}}}`,顶层 key = category、二层 = subCategory。每首歌 `id` / `name` / `artist` / `src` / `cover` 必有;`originalPath`(回指本目录)与 `lyric`(lrc 文本)可选。
2. **导入**:`cd server && ./.venv/Scripts/python.exe scripts/migrate_from_json.py` —— 把 songs.json 写进 SQLite 三表,并把音频**复制**(优先硬链接)到 `server/storage/library/`。幂等,每次全量重建。
   - **子类 key 与目录名并不一致**(`children-classic` ↔ `children/classic`),脚本必须从每条记录的 `src` / `cover` 字段提取真实相对路径,**不能拿子类 key 拼路径**。
   - 音频源目录默认取 `src/static/library/`,该目录已不再存放音频;本地重跑请用环境变量 `SOURCE_LIBRARY_ROOT` 指向真实音频源(容器内挂 `/source`),`SOURCE_SONGS_JSON` 可另指定 songs.json 路径。
3. **运行时消费**:App 不再打包任何曲库数据 —— 元数据由后端 API 下发(响应里已拼成完整公网 URL),音频与封面由后端 `/library` 静态分发(支持 Range,可边下边播)。

## 几个约定

- **songs.json 是源数据单一来源**:既是导入脚本的输入,也承载 `originalPath` 追溯,不再分 registry / songs.ts 两个文件。
- **按分类分层嵌套**:查看时同类归总;`classics` 与 `story` 下的各 4 个子类当前是空占位(`songs: []`),有歌的是 6 个子类。
- **library 分层**:`{大类}/{子类}/`,路径由每条记录的 `src` 推导,两边一致。
- **raw 层不参与编译、不被任何代码引用**:代码只消费后端 API 与 `server/storage/library/`。

## 与各层的边界

| 层 | 位置 | 是否入库 | 维护方式 |
| --- | --- | --- | --- |
| **raw 档案层** | `resource/`(本目录) | 否,仅本 README | 只增、不改、不删;现有约 727MB / 240 个文件 |
| **源数据** | `data/songs.json` | 是 | AI 整理产出,可人工微调;`originalPath` 回指 raw |
| **后端库** | `server/data/music.db` | 否 | 迁移脚本全量重建;只存相对 storage 根的路径(如 `library/children/classic/cn002.mp3`) |
| **分发资源** | `server/storage/library/{大类}/{子类}/` | 否 | 音频 `{id}.mp3`(现有 1119 个);封面 `{id}{ext}`,可缺,缺失时前端用色块占位 |
| **App 包** | 无曲库资源 | — | 元数据与音频全部在线获取,包体积不随曲库增长 |

## 演进路线(元数据 + 音频两条独立线)

两条线的现状都已越过旧方案,记录如下:

**元数据**:

| 阶段 | 方案 | 状态 |
| --- | --- | --- |
| 早期 | `JsonCatalogRepository` fetch `src/static/data/songs.json` 到内存,JS 过滤 | 已弃用(实现仍留在 `src/repository/jsonCatalog.ts`,仅作离线兜底参考) |
| **现状** | **后端 API + SQLite**:分页、条件筛选、计数聚合全部下沉到 SQL | 已上线(1119 首) |
| 十万 / 百万级 | 给 `songs` 补 `(sub_category_id, sort_order, id)` 复合索引,必要时上全文检索 | 未做(当前规模无可测收益) |

**音频 / 封面**:

| 阶段 | 方案 | 状态 |
| --- | --- | --- |
| 早期 | 打包进 `src/static/library/`,随 App 安装、离线可用 | 已弃用(`src/static/` 现已无资源) |
| **现状** | **后端 `/library` 静态分发** + 客户端缓存头(音频 7 天 immutable,封面 / APK 5 分钟) | 已上线 |
| 后续 | 收藏歌曲本地离线缓存;曲库再上量级时改资源包 / 首启下载 | 未做 |

> 音频永远不进内存(播放时流式读单首);无论走哪条线,raw 层约定都不变。

## 备注

- 已经落盘的音频在 `server/storage/library/`,**不在本目录**;raw 层只作为追溯与重放基准保留。
- `src/repository/` 是工程层的取数入口,契约在 `src/repository/types.ts`:切换数据源只改 `src/repository/index.ts` 的实例化,业务代码不动。
