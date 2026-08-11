"""App 版本检查路由:返回最新整包信息(供客户端比对并下载 APK)。

数据源为 .env 配置(settings.app_*),不入库;无鉴权,App 启动公开访问。
versionCode 从 app_version 派生(主×100+次×10+修订),与 manifest.json 的
versionCode 数字保持一致,客户端据此做数值比对。
"""
from fastapi import APIRouter

from ..config import settings
from ..schemas import VersionOut

router = APIRouter(prefix="/api", tags=["版本"])


@router.get("/version/latest", response_model=VersionOut, summary="最新 App 版本")
def get_latest_version() -> VersionOut:
    """返回 .env 配置的最新版本信息。

    versionCode 优先取 APP_VERSION_CODE(须与 manifest.json versionCode 一致);
    未配置时从 app_version 派生("主.次.修订" → 主×100+次×10+修订,仅次/修订<10 内可靠),
    派生失败回退 0,避免阻断启动期检查。downloadUrl 为空时客户端会跳过下载仅提示。
    """
    # 优先用显式配置的 versionCode(推荐,避免派生公式在大版本号碰撞)
    if settings.app_version_code is not None:
        code = settings.app_version_code
    else:
        parts = (settings.app_version or "").split(".")
        while len(parts) < 3:
            parts.append("0")
        try:
            code = int(parts[0]) * 100 + int(parts[1]) * 10 + int(parts[2])
        except ValueError:
            code = 0

    return VersionOut(
        version=settings.app_version,
        version_code=code,
        download_url=settings.app_download_url,
        release_notes=settings.app_release_notes,
        force_update=settings.app_force_update,
    )
