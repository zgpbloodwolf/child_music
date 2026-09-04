#!/usr/bin/env bash
# 启蒙音频后端:构建镜像 / 运行容器(等价于 docker-compose.yml)
# 自动重启由 Docker 的 --restart unless-stopped 保证:容器崩溃或宿主机重启后自动拉起
#
# 用法:
#   ./docker-run.sh                运行(从 ACR 拉取当前架构镜像)
#   ./docker-run.sh build          多架构打包并推送 ACR(amd64 + arm64)
#   ./docker-run.sh build-local    仅构建本机架构镜像到本地 docker(不推送,用于调试)
#   ./docker-run.sh all            推送 ACR 后运行
#   ./docker-run.sh logs           查看实时日志
#   ./docker-run.sh stop           停止并删除容器
#
# 多架构说明:
#   build 使用 docker buildx 一次性构建 linux/amd64 与 linux/arm64,推送至阿里云 ACR
#   生成单一多架构 manifest,任何架构的机器(开发机 amd64 / 橙派 arm64)pull 同一 tag
#   都会自动拿到对应架构镜像,部署机无需再本地 build(绕开橙派拉基础镜像超时问题)。
#   build-local 仅构建宿主机本机架构并 --load 到本地 docker,不推送,用于本地快速验证。
# 首次导入曲库:docker exec -it childmusic python scripts/migrate_from_json.py
set -e

# ---- 可配置项 ----
# ACR 仓库完整地址(含域名/命名空间/仓库名),不含 tag
ACR_REPO="crpi-lgmprcsgzikcd6ib.cn-hangzhou.personal.cr.aliyuncs.com/xuezgp/child_music"
# 镜像版本规则:
#   - 存在 VERSION 文件:固定使用其内容(显式钉住版本,优先级最高)
#   - build / all / build-local:查询 ACR 已有最大 x.y.z tag 并递增 patch;
#     查询失败(无凭据/无网络/尚无版本 tag)时回退 1.0.0
#   - 其余模式(run/logs/stop):使用 latest(每次 build 都会同步推送 latest)
# 私有仓库查询 tag 需要 ACR 凭据:export ACR_USER=... ACR_PASS=...;
#   未导出时自动复用 ~/.docker/config.json 里的 docker login 凭据
#   (credential helper 或明文 auth)。凭据不要写进 .env —— .env 会被 --env-file 整体注入容器。
# 多架构目标平台
PLATFORMS="linux/amd64,linux/arm64"
# ------------------

CONTAINER="childmusic"
IMAGE_LATEST="${ACR_REPO}:latest"

cd "$(dirname "$0")"
MODE="${1:-run}"

# 从 .env 安全读取一个变量值:按纯文本解析,不做 shell 展开,
# 因此兼容含特殊字符的值。
# 仅用于本脚本的变量替换;容器内环境变量由下方 --env-file 注入。
get_env() {
  local key="$1" default="$2" val
  [ -f .env ] || { printf '%s' "$default"; return; }
  val=$(grep -E "^${key}=" .env 2>/dev/null | head -n1 | cut -d= -f2-)
  # 去掉首尾成对的单/双引号
  case "$val" in
    \"*\") val="${val#\"}"; val="${val%\"}" ;;
    \'*\') val="${val#\'}"; val="${val%\'}" ;;
  esac
  printf '%s' "${val:-$default}"
}

PORT="$(get_env PORT 8823)"

# 确保已登录 ACR(build/push 前调用)。已登录则静默跳过。
ensure_acr_login() {
  if ! docker pull "$ACR_REPO" >/dev/null 2>&1; then
    echo "[ACR] 未登录或无拉取权限,尝试登录…"
    docker login "$(echo "$ACR_REPO" | cut -d/ -f1)"
  fi
}

# ---- 版本解析:根据 ACR 远端 tag 自动递增 ----

# 输出查询 ACR API 用的 user:pass;取不到则输出空(走匿名,仅公开仓库有效)。
# 优先级:ACR_USER/ACR_PASS 环境变量 > docker login 凭据(credential helper,或 config.json 明文 auth)。
acr_credentials() {
  local host cfg helper auth
  if [ -n "${ACR_USER:-}" ] && [ -n "${ACR_PASS:-}" ]; then
    printf '%s:%s' "$ACR_USER" "$ACR_PASS"
    return
  fi
  host="${ACR_REPO%%/*}"
  cfg="${HOME}/.docker/config.json"
  [ -f "$cfg" ] || return 0
  helper="$(sed -n 's/.*"credsStore"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$cfg")"
  if [ -n "$helper" ] && command -v "docker-credential-${helper}" >/dev/null 2>&1; then
    printf '%s\n' "$host" | "docker-credential-${helper}" get 2>/dev/null \
      | sed -n 's/.*"Username": *"\([^"]*\)".*"Secret": *"\([^"]*\)".*/\1:\2/p'
    return
  fi
  auth="$(tr -d '[:space:]' < "$cfg" | grep -o "\"${host//./\\.}\"[^}]*\"auth\":\"[^\"]*\"" | sed 's/.*"auth":"//;s/"$//')"
  [ -n "$auth" ] || return 0
  printf '%s' "$auth" | base64 -d 2>/dev/null || true
}

# 查询 ACR 远端已有的最大 x.y.z 版本 tag;查询失败或没有版本 tag 时输出空。
# 走 Docker Registry v2 API:先从 401 响应头发现 token 服务,再取 tag 列表。
remote_max_version() {
  local host repo header realm service token_url token creds tags
  host="${ACR_REPO%%/*}"
  repo="${ACR_REPO#*/}"
  header="$(curl -sS -m 10 -o /dev/null -D - "https://${host}/v2/" 2>/dev/null \
    | tr -d '\r' | grep -i '^www-authenticate:' || true)"
  realm="$(printf '%s' "$header" | sed -n 's/.*realm="\([^"]*\)".*/\1/p')"
  service="$(printf '%s' "$header" | sed -n 's/.*service="\([^"]*\)".*/\1/p')"
  [ -n "$realm" ] || return 0
  token_url="${realm}?scope=repository:${repo}:pull"
  if [ -n "$service" ]; then
    token_url="${token_url}&service=${service}"
  fi
  creds="$(acr_credentials)"
  if [ -n "$creds" ]; then
    token="$(curl -sS -m 10 -u "$creds" "$token_url" 2>/dev/null \
      | sed -n 's/.*"token": *"\([^"]*\)".*/\1/p')"
  else
    token="$(curl -sS -m 10 "$token_url" 2>/dev/null \
      | sed -n 's/.*"token": *"\([^"]*\)".*/\1/p')"
  fi
  [ -n "$token" ] || return 0
  tags="$(curl -sS -m 10 -H "Authorization: Bearer ${token}" \
    "https://${host}/v2/${repo}/tags/list" 2>/dev/null || true)"
  printf '%s' "$tags" | tr ',[]"' '\n' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' \
    | sort -t. -k1,1n -k2,2n -k3,3n | tail -n1
}

# 解析本次镜像版本(结果写入 VERSION_VAL):
#   VERSION 文件存在且非空 → 钉住该版本
#   build 类模式           → ACR 最大 x.y.z 递增 patch(查不到回退 1.0.0)
#   其余模式               → latest
resolve_version() {
  VERSION_VAL=""
  if [ -f VERSION ]; then
    VERSION_VAL="$(tr -d '[:space:]' < VERSION)"
  fi
  if [ -n "$VERSION_VAL" ]; then
    echo "[版本] 使用 VERSION 文件钉住:${VERSION_VAL}"
    return
  fi
  case "$MODE" in
    build|build-local|all)
      local max
      max="$(remote_max_version)"
      if [ -n "$max" ]; then
        VERSION_VAL="$(printf '%s' "$max" | awk -F. '{print $1"."$2"."$3+1}')"
        echo "[版本] ACR 当前最大 ${max},本次构建 ${VERSION_VAL}"
      else
        VERSION_VAL="1.0.0"
        echo "[版本] 未获取到 ACR 远端版本(无凭据/无网络/尚无版本 tag),回退 ${VERSION_VAL}"
      fi
      ;;
    *)
      VERSION_VAL="latest"
      ;;
  esac
}

resolve_version
IMAGE_TAG="${ACR_REPO}:${VERSION_VAL}"

# 多架构打包并推送 ACR
build() {
  echo "[构建] 多架构构建 ${PLATFORMS} 并推送 ACR…"
  ensure_acr_login
  # --provenance=false --sbom=false:ACR 个人版不支持 buildx 默认附带的
  # attestation 清单(application/vnd.oci.empty.v1+json),会报
  # "denied: unknown manifest class",必须显式关闭。
  docker buildx build \
    --platform "$PLATFORMS" \
    --provenance=false \
    --sbom=false \
    -t "$IMAGE_TAG" \
    -t "$IMAGE_LATEST" \
    --push \
    .
  echo "[构建] 已推送多架构镜像:"
  echo "  ${IMAGE_TAG}"
  echo "  ${IMAGE_LATEST}"
  echo "[构建] 任意架构机器执行:docker pull ${IMAGE_TAG}"
}

# 仅构建本机架构到本地 docker(不推送,用于调试)
build_local() {
  echo "[构建] 本机架构构建并加载到本地 docker…"
  docker buildx build --load -t "$IMAGE_TAG" .
  echo "[构建] 已加载本地镜像:${IMAGE_TAG}"
}

# 运行容器(从 ACR 拉取当前架构)
run() {
  echo "[运行] 拉取镜像 ${IMAGE_TAG}(自动选择本机架构)…"
  docker pull "$IMAGE_TAG"
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  docker run -d \
    --name "$CONTAINER" \
    --restart unless-stopped \
    -p "${PORT}:${PORT}" \
    -v "$(pwd)/volumes/storage:/app/storage" \
    -v "$(pwd)/volumes/db:/app/data" \
    -v "$(pwd)/volumes/source:/source:ro" \
    --env-file .env \
    -e SOURCE_SONGS_JSON=/source/songs.json \
    -e SOURCE_LIBRARY_ROOT=/source \
    "$IMAGE_TAG"
  echo "已启动: http://<本机IP>:${PORT}/cmusic"
  echo "日志:   ./docker-run.sh logs   或   docker logs -f $CONTAINER"
}

# 实时日志
logs() {
  docker logs -f "$CONTAINER"
}

# 停止并删除容器(数据卷保留)
stop() {
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  echo "已停止并删除容器 $CONTAINER(volumes 目录保留)"
}

case "${1:-run}" in
  build)       build ;;
  build-local) build_local ;;
  run)         run ;;
  all)         build; run ;;
  logs)        logs ;;
  stop)        stop ;;
  *) echo "用法: $0 [build|build-local|run|all|logs|stop]"; exit 1 ;;
esac
