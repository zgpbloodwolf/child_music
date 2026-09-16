# 启蒙音频后端服务

手机端音乐应用(`src/`)的音频/封面文件分发 + 曲库元数据 + 管理后端。
把原本打包进 App 的 729MB 音频剥离到本服务,App 改为在线播放(默认)+ 下载缓存离线。

## 架构

```
App / H5 / 小程序
   │  uni.request(元数据) + backgroundAudioManager(网络流) + uni.downloadFile(缓存)
   ▼
Nginx Proxy Manager:  your-domain.example.com/cmusic/*  ──►  192.168.x.x:8823/*
   ▼
FastAPI 后端(本服务,监听 0.0.0.0:8823)
   ├── /api/*        元数据查询 + /api/admin/* 管理(需 token)
   └── /library/*    静态文件分发(StaticFiles,原生支持 Range)
   存储:storage/library/{大类}/{子类}/{id}.mp3 + SQLite(data/music.db)
```

## 目录结构

```
server/
├── app/                 # FastAPI 应用
│   ├── main.py          # 入口:路由/CORS/StaticFiles/前缀兼容中间件
│   ├── config.py        # 配置(读 .env)
│   ├── database.py      # SQLAlchemy 引擎 + 会话
│   ├── deps.py          # get_db / verify_admin_token
│   ├── models.py        # ORM:categories / sub_categories / songs
│   ├── schemas.py       # Pydantic 模型(字段 camelCase 对齐前端)
│   ├── routers/         # catalog(查询)/ admin(管理)
│   └── services/        # meta(查询+URL拼接)/ storage(文件+时长)
├── admin_static/        # 极简管理页(/admin)
├── scripts/             # 一次性脚本(见各自头部 docstring)
│   ├── migrate_from_json.py      # songs.json + library → SQLite + storage
│   └── import-*.py / upload-*.py # 批量导入、上传到远端管理接口
├── storage/             # 音频存储根(.gitignore)
├── data/                # SQLite(.gitignore)
├── requirements.txt
├── .env.example
└── run.py               # 启动入口
```

## 快速开始

需要 Python 3.10+。

```bash
cd server
python -m venv .venv
# Windows: .venv\Scripts\activate   |  Linux: source .venv/bin/activate
pip install -r requirements.txt

# 1) 配置:复制模板并按需修改(尤其 ADMIN_TOKEN、PUBLIC_BASE_URL)
cp .env.example .env

# 2) 迁移:默认读 <仓库根>/data/songs.json,音频从 <仓库根>/src/static/library/ 取
#    (音频目录不随仓库分发;若手上没有,改用下方「Docker 部署」的 volumes/source/ 流程)
python scripts/migrate_from_json.py
# 预期输出:分类 4、子类 14、歌曲 1119、缺失音频文件 0

# 3) 启动
python run.py
# Uvicorn running on http://0.0.0.0:8823
```

## 配置(.env)

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| HOST / PORT | 0.0.0.0 / 8823 | 监听地址端口 |
| ROOT_PATH | /cmusic | 反向代理子路径前缀 |
| PUBLIC_BASE_URL | http://your-domain.example.com/cmusic | 拼接 cover/src 完整 URL 的公网基础地址 |
| STORAGE_ROOT | storage | 音频存储根(相对 server/) |
| DB_PATH | data/music.db | SQLite 路径(相对 server/) |
| ADMIN_TOKEN | change-me-… | 管理接口 token(**上线务必改为强随机串**) |
| CORS_ORIGINS | * | CORS 白名单(逗号分隔;生产建议收敛) |

换域名/前缀只改 `PUBLIC_BASE_URL` 与 `ROOT_PATH`,数据不动。

## API 概览

**元数据查询(公开)**:
- `GET /api/categories` 完整分类树(大类与子类均带 `songCount`,前端「N 首」直接读它)
- `GET /api/songs/{id}` 歌曲详情(含 src/lyric)
- `GET /api/songs?category=&sub=&keyword=&author=&ids=&page=&size=` 统一查询(带 page+size 返回分页结构,否则裸数组)
- `GET /api/songs/ids?category=&sub=&keyword=&author=` 只返回有序 id 数组(用于建播放入队;响应体约为带元数据的 1/10)
- `GET /api/authors?category=&sub=` 按作者聚合作品数(含该作者涉及的子类)
- `GET /api/subs/{id}`(带 `songCount`)、`GET /api/subs/{id}/category`

> 需要「任意条件的条数」时用 `GET /api/songs?...&page=1&size=1` 读响应里的 `total`,不要为计数新建接口。
> ⚠️ `/api/songs/ids` 必须声明在 `/api/songs/{id}` **之前**,否则会被后者当作 `song_id="ids"` 抢先匹配并 404。

**文件分发(公开,支持 Range)**:`GET /library/{大类}/{子类}/{id}.mp3`

**管理(需 `Authorization: Bearer <ADMIN_TOKEN>`)**:
- `POST /api/admin/songs` 上传(multipart:audio + cover? + 元数据)
- `PUT /api/admin/songs/{id}` 编辑、`DELETE /api/admin/songs/{id}` 删除(连文件)
- `POST /api/admin/songs/{id}/cover` 替换封面
- `POST /api/admin/categories`、`PUT /api/admin/categories/{id}`、`DELETE /api/admin/categories/{id}`
- `POST /api/admin/subs`、`DELETE /api/admin/subs/{id}`

管理页:浏览器打开 `http://<host>:8823/admin`(或经反代 `.../cmusic/admin`)。

## 验证

```bash
# 元数据:应返回 1119 条
curl http://localhost:8823/api/songs | python -c "import sys,json;print(len(json.load(sys.stdin)))"

# 详情:src 应为完整公网 URL
curl http://localhost:8823/api/songs/cn002

# Range(拖进度条关键):期望 206 + Accept-Ranges: bytes
curl -I -r 0-0 http://localhost:8823/library/children/classic/cn002.mp3

# 上传(替换 token)
curl -X POST http://localhost:8823/api/admin/songs \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -F audio=@test.mp3 -F id=test001 -F name=测试 -F artist=测试 \
  -F category_id=children -F sub_category_id=children-classic

# 核对歌曲数
sqlite3 data/music.db "SELECT sub_category_id, COUNT(*) FROM songs GROUP BY sub_category_id;"
```

## Nginx Proxy Manager 配置(关键)

后端内置 `StripPrefixMiddleware`,**兼容 Nginx 去前缀与保留前缀两种转发**。NPM 推荐用 Custom Location:

1. Proxy Hosts → 新建 Proxy Host:
   - Domain Names:`your-domain.example.com`
   - Forward Hostname / IP:`192.168.x.x`,Forward Port:`8823`
2. Custom Locations 添加:
   - Define location:`/cmusic`
   - Forward Hostname / IP:`192.168.x.x`,Forward Port:`8823`

NPM 默认保留 `/cmusic` 前缀转发到后端,后端中间件自动剥除,路由正常命中,无需手动 rewrite。
公网访问即 `http://your-domain.example.com/cmusic/api/categories`、`.../library/children/classic/cn002.mp3`。

> 缓存:后端已直接下发 `Cache-Control`(`.mp3` 长缓存且 `immutable`;APK 与封面走短缓存,因为二者会被原地替换),NPM 无需重复配置。

## 常驻部署

**Windows(NSSM,推荐)**:
```powershell
nssm install childmusic-backend "C:\Python311\python.exe" "C:\path\to\server\run.py"
nssm set childmusic-backend AppDirectory "C:\path\to\server"
nssm set childmusic-backend AppEnvironmentExtra "PYTHONUNBUFFERED=1"
nssm start childmusic-backend
```

**Linux(systemd)**:见下方模板,`/etc/systemd/system/cmusic-backend.service`
```ini
[Unit]
Description=启蒙音频后端服务
After=network.target
[Service]
Type=simple
WorkingDirectory=/opt/server
ExecStart=/usr/bin/python3 /opt/server/run.py
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
```

## Docker / CasaOS 部署(推荐)

后端已提供 `Dockerfile` 与 `docker-compose.yml`。音频/封面与 SQLite 通过 volume 持久化,容器重建不丢数据。CasaOS 可直接以 Compose 导入并管理(启停/日志/备份)。

> 也可用本目录的 `docker-run.sh`(纯 `docker` 命令,与 compose 等价,适合未安装 `docker compose` 的环境),用法见本节末尾。

### 1. 准备源数据(首次导入用)
把曲库源数据与音频目录放到 compose 同级的 `volumes/source/`:

```
server/
└── volumes/
    └── source/
        ├── songs.json              ← 来自 <仓库根>/data/songs.json
        └── library/                ← 音频目录(现由本服务的 storage/library/ 持有,或旧工程层的 src/static/library/)
            └── children/classic/cn002.mp3 ...
```

### 2. 改配置
编辑 `docker-compose.yml`:`ADMIN_TOKEN` 改为强随机串(默认值会被服务拒绝);按需改 `PUBLIC_BASE_URL`。

### 3. 构建并启动
```bash
docker compose up -d --build
```

### 4. 首次导入曲库(只需一次)
```bash
docker compose exec childmusic python scripts/migrate_from_json.py
# 预期:分类 4、子类 14、歌曲 1119、缺失音频文件 0
```

### 5. CasaOS 管理
- 启动后 CasaOS「应用」列表会自动出现 `childmusic` 容器,可启停、查看日志。
- 也可在 CasaOS「自定义应用」中用本目录的 `docker-compose.yml` 导入。
- Nginx Proxy Manager 把 `/cmusic` 转发到 `192.168.x.x:8823`(宿主机端口,见 compose 的 `ports` 映射)。

### 用 docker-run.sh(构建推送 ACR + 运行,推荐)

本目录的 `docker-run.sh` 用 `docker buildx` 一次性构建 amd64 + arm64 多架构镜像,推送阿里云 ACR 后,任意架构机器(开发机 / 橙派)`run` 都会拉取到匹配架构的镜像,**部署机无需本地 build**(绕开橙派拉基础镜像超时问题):

```bash
./docker-run.sh build    # 多架构打包并推送 ACR(代码更新后,在开发机执行)
./docker-run.sh run      # 从 ACR 拉取镜像并运行(部署机日常 / 升级用)
./docker-run.sh all      # 推送 ACR 后本机运行
./docker-run.sh build-local  # 仅构建本机架构到本地 docker(不推送,调试用)
./docker-run.sh stop     # 停止并删除容器
./docker-run.sh logs     # 跟踪日志
```

版本号自动管理:每次 `build` 自动查询 ACR 已有最大 `x.y.z` tag 并递增 patch(首次为 1.0.0),同时更新 `latest`;写一个 `VERSION` 文件(内容如 `1.2.3`)可显式钉住本次版本。查询远端 tag 需要 ACR 凭据:`export ACR_USER=... ACR_PASS=...`,或已 `docker login` 过 ACR(自动复用 `~/.docker/config.json` 凭据)。凭据不要写进 `.env`(会被 `--env-file` 整体注入容器)。

首次导入曲库:
```bash
docker exec -it childmusic python scripts/migrate_from_json.py
```

> 构建机上拉基础镜像 `python:3.11-slim` 常超时(daemon.json 的 mirror 多已失效,且 dockerd 不继承 shell 代理)。先 `docker pull docker.m.daocloud.io/library/python:3.11-slim` 拉到本地,`build` 的 FROM 即命中缓存、绕过联网拉取。

> 备份:只需备份 `volumes/storage` 与 `volumes/db` 两个目录;`volumes/source` 导入后可删。
> 升级代码:开发机 `./docker-run.sh build`,部署机 `./docker-run.sh run`(拉取最新 latest,数据卷不受影响);或 `docker compose up -d --build` 本地构建。

## 内容同步:改了本地曲库数据,怎么让线上跟着变

线上服务器有一份**独立的运行库**(compose 挂 `./volumes/db`)。本机改了
`data/songs.json` / 本地 DB 之后,线上**不会自动跟着变**,必须显式推一次。

环境拓扑(别搞混,本机开发机的 IP 就是它自己的局域网 IP):

| 角色 | 地址 |
|---|---|
| 本机开发 | `127.0.0.1:8823`(对手机联调时用本机局域网 `192.168.x.x`) |
| 线上服务器 | `192.168.x.x:8823`,内网可直连 |
| 公网入口 | `http://your-domain.example.com/cmusic`(反代/隧道入口,打包好的 App 写死它) |

> 本文档一律用占位地址,**别把真实内网 IP 或公网隧道域名提交进仓库**
> (cpolar 之类的免费隧道域名还会随隧道重建而变,写死反而误导)。
> 真实地址只放各自机器的 `.env`(已 .gitignore)。

推歌词:

```bash
python scripts/push_lyrics.py --base-url http://192.168.x.x:8823 --token <ADMIN_TOKEN> --verify
```

- `--token` 用**服务器** `.env` 里的 `ADMIN_TOKEN`,与开发机 `server/.env` 的
  `local-test-token-2026` 不是同一个值。
- 必须**在内网直连**服务器:`/api/admin/*` 有 `require_intranet`,公网来源一律 403
  (走 cpolar 反代也一样,除非把出口网段加进 `ADMIN_ALLOW_CIDRS`)。
- 脚本只发 `{"lyric": ...}`。远端 `SongUpdate` 无必填字段且路由用
  `exclude_unset=True`,不会清空其他字段。开写前先用**不存在的 id** 探测一次
  (401=token 错 / 403=不在内网 / 404=可写),该探测不改动任何数据。
- `--dry-run` 只看差异;`--overwrite` 才覆盖两边不一致的;`--ids cn003,en077` 只推指定歌。

> **坑:别用 `/api/songs?missing=lyric` 判断线上缺不缺歌词。** 线上镜像常比本地旧
> (实测 2026-09 部署的那版没有 `missing` 参数),传了会被忽略并返回**全量**,看起来
> 像「1119 首全都没歌词」;服务器 admin 页那个「无歌词」筛选同样是失效的。
> 要判断线上真实覆盖,只能逐首 `GET /api/songs/{id}` —— 脚本已按此实现。

> 若线上镜像确实过旧(缺 `missing` 等接口),除了推数据,也该考虑 `./docker-run.sh
> build` + 部署机 `run` 重新发一版镜像。

## 跨端注意事项

- **微信小程序(阻塞)**:小程序生产强制 HTTPS。`http://your-domain.example.com` 需有 HTTPS 入口才能用于小程序;并在公众平台配置 `request`、`downloadFile` 合法域名。App / H5 无此限制。
- **H5**:依赖后端 CORS(已配置);开发期 `CORS_ORIGINS=*`,生产收敛到具体域名。
- **App 端**:`INTERNET` 权限默认有;backgroundAudioManager 原生支持网络流播放(后台/锁屏/Range)。
- **封面**:现有数据无封面图,`cover` 返回的 URL 会 404,前端用色块兜底;可通过管理页或 `/api/admin/songs/{id}/cover` 补传。
