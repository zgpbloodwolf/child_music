"""账号密码散列与无状态会话令牌。

- 密码:PBKDF2-HMAC-SHA256(每账号独立随机盐),存储格式
  ``pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>``;
- 会话令牌:不落库的 HMAC 签名串 ``<主体>.<过期时间戳>.<签名>``,
  校验只需密钥(密钥在 .env,不入库),SQLite 里不需要会话表。
  会员令牌主体是 member_id;管理员令牌主体是 ``admin:<id>:<世代>``(带前缀,
  与会员令牌互不可冒充;主体恒为 ASCII,可安全放进 Authorization 头)。
  传输加密由 HTTPS(cpolar/反代)保障。
"""
import hashlib
import hmac
import secrets
import time

from .config import settings

PBKDF2_ITERATIONS = 100_000
# 会员会话有效期:家庭场景从宽,一年重登一次
TOKEN_TTL_SECONDS = 365 * 24 * 3600
# 管理员会话有效期:短于会员,过期自动回登录页
ADMIN_TOKEN_TTL_SECONDS = 7 * 24 * 3600
# 管理员令牌主体前缀(与会员令牌区分,parse_admin_token 据此识别)
ADMIN_SUBJECT_PREFIX = "admin:"


def _secret() -> str:
    """HMAC 密钥:优先 AUTH_SECRET,未配置回退 ADMIN_TOKEN。"""
    return settings.auth_secret or settings.admin_token


def secret_ready() -> bool:
    """签名密钥是否已正确配置(非空且非源码里的默认 change-me 值)。

    管理员登录的前置守卫:默认密钥公开在源码里,若用它签发管理员令牌,
    任何读过源码的内网用户都能自签同格式令牌获得全部管理权限,
    故未配置时登录接口直接拒绝(503)。
    """
    secret = _secret()
    return bool(secret) and not secret.startswith("change-me")


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


def make_token(member_id: str, ttl_seconds: int = TOKEN_TTL_SECONDS) -> str:
    """签发会员会话令牌:<member_id>.<过期时间戳>.<HMAC签名>。"""
    exp = int(time.time()) + ttl_seconds
    payload = f"{member_id}.{exp}"
    return f"{payload}.{_sign(payload)}"


def parse_token(token: str) -> str | None:
    """校验令牌,通过返回令牌主体(会员令牌即 member_id,管理员令牌带 admin: 前缀)。

    过期/签名不符/格式错一律 None。管理员令牌主体形如 admin:<id>:<版本>,
    调用方 optional_member 拿它查 Member 主键永远查不到 → 天然视为匿名。
    """
    parts = token.split(".")
    if len(parts) != 3:
        return None
    subject, exp, sig = parts
    if not subject or not exp.isdigit():
        return None
    if int(exp) < time.time():
        return None
    if not hmac.compare_digest(_sign(f"{subject}.{exp}"), sig):
        return None
    return subject


def make_admin_token(admin_id: str, pwd_version: int) -> str:
    """签发管理员会话令牌,主体 admin:<id>:<pwd_version>(冒号分隔,恒 ASCII)。

    pwd_version 是令牌世代:改密 +1 后,旧世代令牌即刻失效(见 deps 校验)。
    """
    subject = f"{ADMIN_SUBJECT_PREFIX}{admin_id}:{pwd_version}"
    return make_token(subject, ADMIN_TOKEN_TTL_SECONDS)


def parse_admin_token(token: str) -> tuple[str, int] | None:
    """校验管理员会话令牌,通过返回 (admin_id, pwd_version);其余情况 None。

    与 parse_token 同一套格式/exp/签名校验,额外要求主体带 admin: 前缀,
    会员令牌(主体是裸 member_id)在这里必然解析失败,不可冒充。
    """
    subject = parse_token(token)
    if not subject or not subject.startswith(ADMIN_SUBJECT_PREFIX):
        return None
    rest = subject[len(ADMIN_SUBJECT_PREFIX):]
    admin_id, _, version = rest.rpartition(":")
    if not admin_id or not version.isdigit():
        return None
    return admin_id, int(version)
