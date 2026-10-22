/**
 * 登录态 store:登录 / 启动校验 / 自助修改资料与密码 / 登出。
 *
 * - 登录成功 = 拿到会话令牌 + 确定当前成员(数据隔离身份);
 * - 账号一律由管理员在后台创建,登录页不开放注册,App 内也不提供开号;
 * - 启动校验(GET /api/auth/me)确认令牌仍有效、账号未被删;
 * - 自助修改(PUT /api/auth/profile、/api/auth/password)只能改自己:
 *   昵称/头像/密码可改,登录账号(username)不开放自改;
 * - 切换账号 = 退出登录 → 登录页用另一账号登录(不做免密切换)。
 */
import { defineStore } from 'pinia';
import { request } from '@/utils/request';
import { clearAuthToken, getAuthToken, setAuthToken } from '@/utils/authToken';
import { useMemberStore } from '@/store/member';
import { currentMember, MEMBER_STORAGE_KEY, type MemberInfo } from '@/store/memberPrefs';

/** POST /api/auth/login 响应 */
interface LoginResp {
  token: string;
  member: MemberInfo;
}

export const useAuthStore = defineStore('auth', () => {
  /** 账号密码登录:存令牌 → 确定当前成员(收藏/历史随账号加载) */
  async function login(username: string, password: string): Promise<void> {
    const resp = await request<LoginResp>({
      url: '/api/auth/login',
      method: 'POST',
      data: { username, password },
    });
    setAuthToken(resp.token);
    await useMemberStore().select(resp.member);
  }

  /**
   * 启动校验:本地有令牌时回读当前账号,确认令牌有效、账号未被删。
   * 返回是否有效;失败(401 等)由 request.ts 统一清令牌并踢回登录页,
   * 调用方(App.vue)据返回值决定是否继续预热等启动初始化。
   */
  async function ensureValid(): Promise<boolean> {
    if (!getAuthToken()) return false;
    try {
      const me = await request<MemberInfo>({ url: '/api/auth/me' });
      currentMember.value = me;
      uni.setStorageSync(MEMBER_STORAGE_KEY, me);
      return true;
    } catch {
      // 令牌无效时 request.ts 已处理跳转;网络抖动则保持本地现状
      return false;
    }
  }

  /**
   * 自助修改资料(昵称/头像):成功后用服务端返回的最新账号信息
   * 更新共享 currentMember 与本地缓存(与 ensureValid 同口径),
   * 「我的」页头部等引用处自动刷新。
   */
  async function updateProfile(profile: { name: string; avatar: string }): Promise<void> {
    const me = await request<MemberInfo>({
      url: '/api/auth/profile',
      method: 'PUT',
      data: profile,
    });
    currentMember.value = me;
    uni.setStorageSync(MEMBER_STORAGE_KEY, me);
  }

  /**
   * 自助修改密码:需旧密码验证。旧密码错误时后端返回 400 并抛
   * RequestError(含后端中文提示),由调用方(账号管理页)toast。
   */
  async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
    await request<{ ok: boolean }>({
      url: '/api/auth/password',
      method: 'PUT',
      data: { oldPassword, newPassword },
    });
  }

  /** 登出:清令牌与本地身份,回到未选成员状态,跳转登录页 */
  function logout(): void {
    clearAuthToken();
    void useMemberStore().select(null).finally(() => {
      uni.reLaunch({ url: '/pages/login/index' });
    });
  }

  return { login, ensureValid, updateProfile, changePassword, logout };
});
