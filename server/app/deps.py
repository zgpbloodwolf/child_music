"""FastAPI 依赖:数据库会话(get_db)、登录态鉴权、管理接口鉴权与内网访问控制。"""
import secrets
from ipaddress import AddressValueError, ip_address

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import settings
from .models import Member
from .security import parse_token

# 复用 database.get_db 作为公开依赖(避免循环,直接 re-export)
from .database import get_db  # noqa: F401


def optional_member(
    x_auth_token: str = Header(default="", alias="X-Auth-Token"),
    db: Session = Depends(get_db),
):
    """从 X-Auth-Token 解析登录态,返回 Member;未登录/令牌无效/账号已删 → None。

    供「未登录也放行」的条件接口(如首个账号注册)使用;强制登录的接口
    请用 require_member。
    """
    if not x_auth_token:
        return None
    member_id = parse_token(x_auth_token)
    if not member_id:
        return None
    # 账号被其他端删除后,旧令牌即刻失效(签名虽对,人已不在)
    return db.get(Member, member_id)


def require_member(member=Depends(optional_member)):
    """强制登录依赖:任何 /api 业务路由挂它即可,未登录统一 401。"""
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或登录已过期"
        )
    return member


def _admin_token_ok(authorization: str) -> bool:
    """Authorization 头是否为有效的管理员 Bearer token。

    用 secrets.compare_digest 防时序攻击;token 存 .env,传输加密由 cpolar HTTPS 保障。
    未配置默认 token(change-me)时拒绝,避免误上线裸奔;
    空串同样拒绝(compose 的 "${ADMIN_TOKEN}" 在变量未定义时注入空串而非缺失,
    空串会导致 "Bearer "(空 token)通过校验)。
    """
    expected = f"Bearer {settings.admin_token}"
    return bool(
        settings.admin_token
        and not settings.admin_token.startswith("change-me")
        and secrets.compare_digest(authorization or "", expected)
    )


def verify_admin_token(authorization: str = Header(default="", description="Bearer <ADMIN_TOKEN>")) -> None:
    """管理接口鉴权:校验 Authorization: Bearer <token>(规则见 _admin_token_ok)。"""
    if not _admin_token_ok(authorization):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未授权:token 无效")


def require_member_or_admin(
    member=Depends(optional_member),
    authorization: str = Header(default=""),
):
    """会员登录 或 管理员 token 二选一放行(曲库元数据读取用)。

    管理页用管理员 Bearer token 维护曲库,但管理员不是会员、没有 X-Auth-Token,
    若只挂 require_member 会把管理页挡在 /api/categories、/api/songs 之外。
    挂在 router dependencies 上,返回值不被使用(各端点不依赖具体身份)。
    """
    if member is None and not _admin_token_ok(authorization):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或登录已过期"
        )


def _trusted_ip(ip_str: str) -> bool:
    """IP 是否属于可信网段(回环/私网等,复用管理白名单配置)。"""
    try:
        ip = ip_address(ip_str)
    except (ValueError, AddressValueError):
        return False
    return any(ip in net for net in settings.admin_allow_networks)


def _client_ip(request: Request) -> str:
    """取真实客户端 IP(防伪造)。

    两层规则:
    1. 只有「直连对端」本身可信(反代与后端同机/同私网,即 request.client.host
       在白名单网段内)时才采信其转发的 X-Forwarded-For;公网直连者的 XFF 一律
       忽略,直接用直连 IP——否则攻击者直连端口伪造 XFF: 10.0.0.1 即可绕过白名单。
    2. 采信时从 XFF 右端往左取第一个非可信地址:反代链逐层把来源追加在右侧,
       最右侧可信条目之前那一跳才是真实来源;客户端伪造的左侧条目不会被取到。
       整条链都可信(纯内网访问)时回退直连 IP。

    畸形 XFF 条目按不可信处理(取到即后续 403,失败方向安全)。
    """
    direct = request.client.host if request.client else ""
    if not settings.admin_trust_forwarded or not _trusted_ip(direct):
        return direct
    xff = request.headers.get("x-forwarded-for", "")
    for part in reversed(xff.split(",")):
        part = part.strip()
        if part and not _trusted_ip(part):
            return part
    return direct


def require_intranet(request: Request) -> None:
    """内网访问控制:仅放行白名单网段的请求,公网来源一律 403。

    覆盖 /admin 页面与 /api/admin/* 写接口,作为 token 之外的第二道防线。
    白名单默认覆盖私网段 + 回环(见 settings.admin_allow_networks),
    额外网段(如办公网公网出口、VPN 段)在 .env 的 ADMIN_ALLOW_CIDRS 追加。

    取 IP 逻辑见 _client_ip:直连对端可信才采信 X-Forwarded-For,且从右往左取。
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
