"""跨平台启动入口:python run.py

通过 root_path=/childmusic 让 FastAPI 感知反向代理的子路径前缀;
proxy_headers + forwarded_allow_ips 信任 Nginx 透传的 X-Forwarded-* 头
(用于 scheme/host 正确,影响生成的完整 URL)。
"""
import uvicorn

from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        # 不设 root_path:前缀统一由 app 内 StripPrefixMiddleware 处理(见 app/main.py)
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
