# child_music

启蒙音频:手机端音乐播放应用（听歌、歌单、播放控制、后台播放等）。

## 技术栈

- **前端**：uni-app + Vue 3 + TypeScript + Pinia
- **后端**：FastAPI + SQLite + Docker
- **部署**：CasaOS + Nginx Proxy Manager + cpolar 隧道

---

## 本地开发

```bash
# 安装依赖
pnpm install

# H5 开发
pnpm dev:h5

# App 开发（需 HBuilderX 真机/模拟器）
pnpm dev:app
```

---

## 部署更新（服务器 192.168.50.88）

### 1. 拉取最新代码

```bash
cd /DATA/AppData/childmusic/child_music

# 如果有本地修改冲突
git reset --hard HEAD

# 拉取
git pull
```

### 2. 配置环境变量

```bash
cd server

# 创建 .env（敏感信息不入库）
# 生成 ADMIN_TOKEN: openssl rand -hex 32
cat > .env << 'EOF'
PUBLIC_BASE_URL=http://你的域名或隧道地址/cmusic
ADMIN_TOKEN=用openssl生成的token
EOF
```

### 3. 重启 Docker 容器

```bash
# CasaOS 旧版 Docker 用 docker-compose（带连字符）
docker-compose down
docker-compose up -d --build

# 或新版 Docker
docker compose down
docker compose up -d --build

# 或用纯 docker 脚本(server/docker-run.sh,等价上面,未装 compose 时用)
bash docker-run.sh all
```

### 4. 验证

```bash
# 检查容器状态
docker-compose ps

# 测试 API
curl http://localhost:8823/cmusic/api/categories
```

---

## 打包发布 App

### 1. 修改前端 .env

```bash
# 根目录 .env
VITE_APP_ENV=online
VITE_API_BASE_URL_ONLINE=http://你的域名或隧道地址/cmusic
```

### 2. 打包

```bash
pnpm build:app
```

### 3. 上传 APK

打包后的 APK 在 `dist/build/app/` 目录，上传到服务器：

```bash
# 复制到服务器存储目录
scp dist/build/app/*.apk user@192.168.50.88:/DATA/AppData/childmusic/child_music/server/storage/library/apk/
```

### 4. 更新版本号

编辑 `server/.env`：

```bash
APP_VERSION=1.0.4
APP_DOWNLOAD_URL=http://你的域名或隧道地址/cmusic/library/apk/child-music.apk
APP_RELEASE_NOTES=更新内容说明
APP_FORCE_UPDATE=false
```

重启容器生效。

---

## 目录结构

```
├── src/                # 前端源码
│   ├── pages/          # 页面
│   ├── components/     # 组件
│   ├── store/          # Pinia 状态管理
│   ├── api/            # 接口定义
│   └── utils/          # 工具函数
├── server/             # 后端源码
│   ├── app/            # FastAPI 应用
│   ├── scripts/        # 数据导入脚本
│   └── storage/        # 音频/封面存储
└── docker-compose.yml  # Docker 部署配置
```

---

## 敏感信息说明

以下信息**不要提交到 git**：

- `PUBLIC_BASE_URL`：公网隧道地址
- `ADMIN_TOKEN`：管理接口 token
- `APP_DOWNLOAD_URL`：APK 下载地址

这些配置通过服务器的 `.env` 文件注入，已在 `.gitignore` 中排除。