# 启蒙音频后端服务镜像
# 构建:docker compose build  或  docker build -t childmusic-backend .
# 基础镜像默认走国内 daocloud 镜像加速(多架构;本机无代理直连 docker.io 拉 arm64 极慢)
# 上游等价:docker.io/library/python:3.11-slim;如 mirror 失效可改回上游
ARG BASE_IMAGE=docker.m.daocloud.io/library/python:3.11-slim
FROM ${BASE_IMAGE}

WORKDIR /app

# UTF-8 环境,避免中文(歌曲名/接口提示)在容器内处理异常
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1

# 先装依赖(利用 Docker 层缓存:代码变更不触发重装)
# 用清华 PyPI 镜像加速国内下载(ARM 构建明显提速)
COPY requirements.txt ./
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 拷贝应用代码
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY admin_static/ ./admin_static/
COPY run.py ./

# 数据挂载点:音频/封面、SQLite、迁移用源数据(均由 compose 挂载持久卷)
RUN mkdir -p /app/storage/library /app/data /source
VOLUME ["/app/storage", "/app/data", "/source"]

EXPOSE 8823

CMD ["python", "run.py"]
