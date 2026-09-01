"""FastAPI 依赖:数据库会话(get_db)、管理接口鉴权与内网访问控制。"""
import secrets
from ipaddress import AddressValueError, ip_address

from fastapi import Header, HTTPException, Request, status

from .config import settings

# 复用 database.get_db 作为公开依赖(避免循环,直接 re-export)
from .database import get_db  # noqa: F401


def verify_admin_token(authorization: str = Header(default="", description="Bearer <ADMIN_TOKEN>")) -> None:
    """管理接口鉴权:校验 Authorization: Bearer <token>。

    用 secrets.compare_digest 防时序攻击;token 存 .env,传输加密由 cpolar HTTPS 保障。
    未配置默认 token(change-me)时拒绝,避免误上线裸奔。
    """
    expected = f"Bearer {settings.admin_token}"
    if settings.admin_token.startswith("change-me") or not secrets.compare_digest(
        authorization or "", expected
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未授权:token 无效")


def _client_ip(request: Request) -> str:
    """取真实客户端 IP。

    后端常与 Nginx 同机,request.client.host 会是 127.0.0.1(在白名单内),
    此时公网经反代访问会误放行。故默认信任反代透传的 X-Forwarded-For,
    取其最左端(经 Nginx 追加链的原始客户端 IP);未配置信任时回退直连 IP。

    注意:Nginx 默认追加而非覆盖 XFF,客户端可伪造原始值;但写接口另有
    admin_token 兜底,伪造 XFF 仅能命中 IP 检查,仍无法越权写操作。
    """
    if settings.admin_trust_forwarded:
        xff = request.headers.get("x-forwarded-for", "")
        if xff:
            # XFF 形如 "客户端IP, 一级代理, 二级代理";取最左端即原始客户端
            first = xff.split(",")[0].strip()
            if first:
                return first
    return request.client.host if request.client else ""


def require_intranet(request: Request) -> None:
    """内网访问控制:仅放行白名单网段的请求,公网来源一律 403。

    覆盖 /admin 页面与 /api/admin/* 写接口,作为 token 之外的第二道防线。
    白名单默认覆盖私网段 + 回环(见 settings.admin_allow_networks),
    额外网段(如办公网公网出口、VPN 段)在 .env 的 ADMIN_ALLOW_CIDRS 追加。

    取 IP 逻辑见 _client_ip:默认信任反代透传的 X-Forwarded-For。
    """
    ip_str = _client_ip(request)
    try:
        ip = ip_address(ip_str)
    except (ValueError, AddressValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="禁止访问:管理功能仅限内网",
        )
    if not any(ip in net for net in settings.admin_allow_networks):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="禁止访问:管理功能仅限内网",
        )
