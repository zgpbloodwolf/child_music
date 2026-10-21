"""账号密码散列与无状态会话令牌。

- 密码:PBKDF2-HMAC-SHA256(每账号独立随机盐),存储格式
  ``pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>``;
- 会话令牌:不落库的 HMAC 签名串 ``<member_id>.<过期时间戳>.<签名>``,
  校验只需密钥(密钥在 .env,不入库),SQLite 里不需要会话表。
  传输加密由 HTTPS(cpolar/反代)保障。
"""
import hashlib
import hmac
import secrets
import time

from .config import settings

PBKDF2_ITERATIONS = 100_000
# 会话有效期:家庭场景从宽,一年重登一次
TOKEN_TTL_SECONDS = 365 * 24 * 3600


def _secret() -> str:
    """HMAC 密钥:优先 AUTH_SECRET,未配置回退 ADMIN_TOKEN。"""
    return settings.auth_secret or settings.admin_token


def hash_password(password: str) -> str:
    """生成可校验的密码散列串(盐随机,同密码每次结果不同)。"""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    """按存储格式解析并校验密码;格式异常一律 False(失败方向安全)。"""
    try:
        algo, iterations, salt, digest = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        calc = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations)
        ).hex()
        return hmac.compare_digest(calc, digest)
    except (ValueError, TypeError):
        return False


def _sign(payload: str) -> str:
    return hmac.new(
        _secret().encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def make_token(member_id: str) -> str:
    """签发会话令牌:<member_id>.<过期时间戳>.<HMAC签名>。"""
    exp = int(time.time()) + TOKEN_TTL_SECONDS
    payload = f"{member_id}.{exp}"
    return f"{payload}.{_sign(payload)}"


def parse_token(token: str) -> str | None:
    """校验令牌,通过返回 member_id;过期/签名不符/格式错一律 None。"""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    member_id, exp, sig = parts
    if not member_id or not exp.isdigit():
        return None
    if int(exp) < time.time():
        return None
    if not hmac.compare_digest(_sign(f"{member_id}.{exp}"), sig):
        return None
    return member_id
