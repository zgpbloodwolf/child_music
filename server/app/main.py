"""FastAPI 应用入口:装配路由、CORS、静态分发、反向代理前缀兼容。

前缀兼容(StripPrefixMiddleware):Nginx Proxy Manager 转发 /cmusic/* 时
默认保留前缀,本中间件把请求路径里的 /cmusic 剥掉,使后端路由(/api、
/library)在「Nginx 去前缀」与「Nginx 保留前缀」两种配置下都能命中。
"""
import mimetypes
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import BASE_DIR, settings
from .database import init_db
from .deps import require_intranet
from .routers import admin, catalog, version

# /library 的缓存策略(Starlette 默认只发 ETag / Last-Modified,不带 Cache-Control,
# 导致每次播放都要回源做一次条件请求)。
# - 音频:{id}.mp3,文件名即歌曲 id,且没有「同 id 换音频」的接口(只有删除后重建),
#   内容视为不可变 → 长缓存且 immutable,播放/拖动进度不再产生任何额外请求。
#   ⚠️ 代价:若后台删除后用同一个 id 传了新音频,老客户端最多 7 天后才会取到新文件。
# - 其余(封面、APK):会被原地替换(封面见 admin.replace_cover,APK 每次发版覆盖同名
#   文件),长缓存会让新版本发不出去 → 只给 5 分钟,其余靠 ETag 条件校验兜底。
AUDIO_EXTS = {".mp3", ".m4a", ".aac", ".flac", ".wav", ".ogg"}
AUDIO_CACHE_CONTROL = "public, max-age=604800, immutable"
MUTABLE_CACHE_CONTROL = "public, max-age=300"


class LibraryStaticFiles(StaticFiles):
    """静态分发 /library,并按扩展名补上 Cache-Control。"""

    def file_response(
        self,
        full_path,
        stat_result,
        scope,
        status_code: int = 200,
    ):
        response = super().file_response(full_path, stat_result, scope, status_code)
        # 命中条件请求时返回的是 304,同样应当带上 Cache-Control,故在此统一设置
        suffix = Path(str(full_path)).suffix.lower()
        response.headers["Cache-Control"] = (
            AUDIO_CACHE_CONTROL if suffix in AUDIO_EXTS else MUTABLE_CACHE_CONTROL
        )
        return response


class StripPrefixMiddleware:
    """剥掉反向代理保留的子路径前缀(如 /cmusic)。

    两种 Nginx 转发都兼容:
    - 去前缀:请求 /api/songs 直达 → 不剥
    - 保留前缀:请求 /cmusic/api/songs → 剥成 /api/songs
    """

    def __init__(self, app: Callable[..., Awaitable[None]], prefix: str) -> None:
        self.app = app
        self.prefix = (prefix or "").rstrip("/")

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") == "http" and self.prefix:
            path = scope.get("path", "") or ""
            if path == self.prefix:
                scope["path"] = "/"
                scope["raw_path"] = b"/"
            elif path.startswith(self.prefix + "/"):
                new = path[len(self.prefix):]
                scope["path"] = new
                scope["raw_path"] = new.encode()
        await self.app(scope, receive, send)


def _ensure_mimetypes() -> None:
    """显式注册音频 MIME,兜底部分 Windows 环境把 mp3 推断为 octet-stream。"""
    mimetypes.init()
    mimetypes.add_type("audio/mpeg", ".mp3")
    mimetypes.add_type("audio/mp4", ".m4a")
    mimetypes.add_type("audio/aac", ".aac")
    mimetypes.add_type("audio/flac", ".flac")
    mimetypes.add_type("audio/x-wav", ".wav")
    mimetypes.add_type("audio/ogg", ".ogg")


def create_app() -> FastAPI:
    _ensure_mimetypes()
    init_db()

    app = FastAPI(
        title="启蒙音频后端",
        description="音频/封面文件分发 + 曲库元数据 + 管理接口",
        version="1.0.0",
        # 不设 root_path:它会与 StaticFiles mount 交互,导致不带前缀的 /library 命中失败。
        # 反向代理子路径前缀统一交由下方 StripPrefixMiddleware 处理(兼容 Nginx 去/留前缀)。
    )

    # CORS 先加(内层),前缀剥离后加(最外层,最先执行)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(StripPrefixMiddleware, prefix=settings.root_path)

    app.include_router(catalog.router)
    app.include_router(admin.router)
    app.include_router(version.router)

    # 音频/封面静态分发(StaticFiles 原生支持 Range,返回 206;缓存头见 LibraryStaticFiles)
    app.mount("/library", LibraryStaticFiles(directory=settings.library_dir), name="library")

    admin_html = BASE_DIR / "admin_static" / "index.html"

    @app.get("/admin", include_in_schema=False)
    def admin_page(_=Depends(require_intranet)) -> FileResponse:
        """极简管理页:填 token → 上传/删除歌曲(限内网访问)。"""
        return FileResponse(admin_html)

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"name": "启蒙音频后端", "docs": "/docs", "admin": "/admin"}

    return app


app = create_app()
