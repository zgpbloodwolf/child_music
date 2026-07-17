# 儿童音乐后端服务

手机端音乐应用(`src/`)的音频/封面文件分发 + 曲库元数据 + 管理后端。
把原本打包进 App 的 729MB 音频剥离到本服务,App 改为在线播放(默认)+ 下载缓存离线。

## 架构

```
App / H5 / 小程序
   │  uni.request(元数据) + backgroundAudioManager(网络流) + uni.downloadFile(缓存)
   ▼
Nginx Proxy Manager:  your-domain.example.com/childmusic/*  ──►  192.168.x.x:8823/*
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
├── scripts/migrate_from_json.py  # 一次性迁移:songs.json → SQLite + 拷贝文件
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

# 2) 迁移:把 src/static/data/songs.json 与 src/static/library/ 导入
python scripts/migrate_from_json.py
# 预期输出:分类 4、子类 17、歌曲 239、缺失音频文件 0

# 3) 启动
python run.py
# Uvicorn running on http://0.0.0.0:8823
```

## 配置(.env)

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| HOST / PORT | 0.0.0.0 / 8823 | 监听地址端口 |
| ROOT_PATH | /childmusic | 反向代理子路径前缀 |
| PUBLIC_BASE_URL | http://your-domain.example.com/childmusic | 拼接 cover/src 完整 URL 的公网基础地址 |
| STORAGE_ROOT | storage | 音频存储根(相对 server/) |
| DB_PATH | data/music.db | SQLite 路径(相对 server/) |
| ADMIN_TOKEN | change-me-… | 管理接口 token(**上线务必改为强随机串**) |
| CORS_ORIGINS | * | CORS 白名单(逗号分隔;生产建议收敛) |

换域名/前缀只改 `PUBLIC_BASE_URL` 与 `ROOT_PATH`,数据不动。

## API 概览

**元数据查询(公开)**:
- `GET /api/categories` 完整分类树
- `GET /api/songs/{id}` 歌曲详情(含 src/lyric)
- `GET /api/songs?category=&sub=&keyword=&ids=&page=&size=` 统一查询(带 page+size 返回分页结构,否则裸数组)
- `GET /api/subs/{id}`、`GET /api/subs/{id}/category`

**文件分发(公开,支持 Range)**:`GET /library/{大类}/{子类}/{id}.mp3`

**管理(需 `Authorization: Bearer <ADMIN_TOKEN>`)**:
- `POST /api/admin/songs` 上传(multipart:audio + cover? + 元数据)
- `PUT /api/admin/songs/{id}` 编辑、`DELETE /api/admin/songs/{id}` 删除(连文件)
- `POST /api/admin/songs/{id}/cover` 替换封面
- `POST /api/admin/categories`、`PUT /api/admin/categories/{id}`、`DELETE /api/admin/categories/{id}`
- `POST /api/admin/subs`、`DELETE /api/admin/subs/{id}`

管理页:浏览器打开 `http://<host>:8823/admin`(或经反代 `.../childmusic/admin`)。

## 验证

```bash
# 元数据:应返回 239 条
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
   - Define location:`/childmusic`
   - Forward Hostname / IP:`192.168.x.x`,Forward Port:`8823`

NPM 默认保留 `/childmusic` 前缀转发到后端,后端中间件自动剥除,路由正常命中,无需手动 rewrite。
公网访问即 `http://your-domain.example.com/childmusic/api/categories`、`.../library/children/classic/cn002.mp3`。

> 缓存:建议在 NPM 对 `/library/` 路径加响应头 `Cache-Control: public, max-age=604800`(音频文件不可变)。

## 常驻部署

**Windows(NSSM,推荐)**:
```powershell
nssm install childmusic-backend "C:\Python311\python.exe" "C:\path\to\server\run.py"
nssm set childmusic-backend AppDirectory "C:\path\to\server"
nssm set childmusic-backend AppEnvironmentExtra "PYTHONUNBUFFERED=1"
nssm start childmusic-backend
```

**Linux(systemd)**:见下方模板,`/etc/systemd/system/childmusic-backend.service`
```ini
[Unit]
Description=儿童音乐后端服务
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

### 1. 准备源数据(首次导入用)
把前端的音频目录与 `songs.json` 放到 compose 同级的 `volumes/source/`:

```
server/
└── volumes/
    └── source/
        ├── songs.json              ← 来自 src/static/data/songs.json
        └── library/                ← 来自 src/static/library/
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
# 预期:分类 4、子类 16、歌曲 239、缺失音频文件 0
```

### 5. CasaOS 管理
- 启动后 CasaOS「应用」列表会自动出现 `childmusic` 容器,可启停、查看日志。
- 也可在 CasaOS「自定义应用」中用本目录的 `docker-compose.yml` 导入。
- Nginx Proxy Manager 把 `/childmusic` 转发到 `192.168.x.x:8823`(宿主机端口,见 compose 的 `ports` 映射)。

> 备份:只需备份 `volumes/storage` 与 `volumes/db` 两个目录;`volumes/source` 导入后可删。
> 升级代码:`docker compose up -d --build`(数据卷不受影响)。

## 跨端注意事项

- **微信小程序(阻塞)**:小程序生产强制 HTTPS。`http://your-domain.example.com` 需有 HTTPS 入口才能用于小程序;并在公众平台配置 `request`、`downloadFile` 合法域名。App / H5 无此限制。
- **H5**:依赖后端 CORS(已配置);开发期 `CORS_ORIGINS=*`,生产收敛到具体域名。
- **App 端**:`INTERNET` 权限默认有;backgroundAudioManager 原生支持网络流播放(后台/锁屏/Range)。
- **封面**:现有数据无封面图,`cover` 返回的 URL 会 404,前端用色块兜底;可通过管理页或 `/api/admin/songs/{id}/cover` 补传。
