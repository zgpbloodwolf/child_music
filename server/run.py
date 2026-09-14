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
        # proxy_headers 用于 scheme/host 正确(X-Forwarded-Proto 等,URL 拼接实际走
        # PUBLIC_BASE_URL 配置,不依赖请求头)。信任范围仅回环+私网(含 docker 网桥
        # 172.16/12):公网直连者透传的 X-Forwarded-* 不被采信,与 deps._client_ip
        # 的信任方向一致;此前 "*" 会让任意直连者的 XFF 改写 request.client.host。
        proxy_headers=True,
        forwarded_allow_ips="127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16",
    )
