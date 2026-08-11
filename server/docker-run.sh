#!/usr/bin/env bash
# 启蒙音频后端:构建镜像 / 运行容器(等价于 docker-compose.yml)
# 用法:
#   ./docker-run.sh          运行(代码没变时,默认)
#   ./docker-run.sh build    打包镜像(代码更新后执行一次)
#   ./docker-run.sh all      打包并运行
# 首次导入曲库:docker exec -it childmusic python scripts/migrate_from_json.py
set -e

IMAGE="childmusic-backend:1.0.0"
CONTAINER="childmusic"
PORT="8823"

cd "$(dirname "$0")"

# 打包镜像
build() {
  docker build -t "$IMAGE" .
}

# 运行容器
run() {
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
    "$IMAGE"
  echo "已启动: http://<本机IP>:${PORT}/cmusic"
}

case "${1:-run}" in
  build) build ;;
  run)   run ;;
  all)   build; run ;;
  *) echo "用法: $0 [build|run|all]"; exit 1 ;;
esac
