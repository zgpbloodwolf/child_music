/**
 * 登录会话令牌的本地存取。
 *
 * 独立成无依赖的小模块:utils/request.ts 要在**每次请求**里读令牌,
 * auth store 又依赖 request —— 若令牌逻辑放进 store 会形成循环依赖。
 */

/** 会话令牌(HMAC 串,由 POST /api/auth/login 签发)的本地存储 key */
export const AUTH_TOKEN_KEY = 'music_auth_token';

/** 读取令牌(未登录/读取失败返回空串) */
export function getAuthToken(): string {
  try {
    return (uni.getStorageSync(AUTH_TOKEN_KEY) as string) || '';
  } catch {
    return '';
  }
}

/** 保存令牌(登录成功时) */
export function setAuthToken(token: string): void {
  try {
    uni.setStorageSync(AUTH_TOKEN_KEY, token);
  } catch { /* 存储失败不影响本次会话 */ }
}

/** 清除令牌(登出/令牌失效时) */
export function clearAuthToken(): void {
  try {
    uni.removeStorageSync(AUTH_TOKEN_KEY);
  } catch { /* 忽略 */ }
}
