"""配置读取:从 .env 加载,类型安全(pydantic-settings)。

所有路径相对 server/ 目录(BASE_DIR)。换域名/端口/前缀只改 .env 一处。
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# server/ 目录绝对路径(本文件位于 server/app/config.py)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """后端运行配置。字段名与 .env 的环境变量名(大写)一一对应。"""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",  # 绝对路径,任意 cwd 都能读到 server/.env
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 监听
    host: str = "0.0.0.0"
    port: int = 8823
    # 反向代理子路径前缀(公网 .../childmusic)
    root_path: str = "/childmusic"

    # 公网基础 URL(拼接 cover/src 的完整 URL)
    # 默认指向本机回环(仅本机联调用);生产务必在 .env 用 PUBLIC_BASE_URL 覆盖为真实公网地址
    public_base_url: str = "http://127.0.0.1:8823/childmusic"

    # 文件存储根目录(相对 BASE_DIR)
    storage_root: Path = Path("storage")
    # SQLite 路径(相对 BASE_DIR)
    db_path: Path = Path("data/music.db")

    # 管理接口 token
    admin_token: str = "change-me-to-a-strong-random-string"

    # App 整包更新配置(运维在 .env 维护,不入库;每次发版同步更新)
    # 展示版本号(versionName,如 1.0.1),versionCode 由其派生(见 routers/version.py)
    app_version: str = "1.0.0"
    # APK 下载完整 URL:可填后端 /library/apk/xxx.apk(经 StaticFiles 分发)或外链(GitHub Release)
    app_download_url: str = ""
    # 更新说明(展示在更新弹窗内容区,\n 换行)
    app_release_notes: str = ""
    # 是否强制更新(为 true 时客户端弹窗不可关闭)
    app_force_update: bool = False

    # CORS 白名单(逗号分隔字符串,见 cors_list 解析)
    cors_origins: str = "*"

    @property
    def library_dir(self) -> Path:
        """音频/封面存储目录(server/storage/library),按需创建。"""
        d = (BASE_DIR / self.storage_root / "library").resolve()
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def sqlite_url(self) -> str:
        """SQLite 连接串。相对 db_path 以 BASE_DIR 为基准解析。"""
        db = (BASE_DIR / self.db_path).resolve()
        db.parent.mkdir(parents=True, exist_ok=True)
        # as_posix 避免 Windows 反斜杠导致 sqlite:/// 解析异常
        return f"sqlite:///{db.as_posix()}"

    @property
    def cors_list(self) -> list[str]:
        """解析 CORS 白名单:* 透传,否则按逗号拆分。"""
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def public_base(self) -> str:
        """去掉末尾斜杠的公网基础 URL,便于后续 path 拼接。"""
        return self.public_base_url.rstrip("/")


# 全局单例
settings = Settings()
