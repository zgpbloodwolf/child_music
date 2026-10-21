import { defineStore } from 'pinia';
import { ref } from 'vue';
import { request } from '@/utils/request';
import { useLibraryStore } from '@/store/library';
import { useHistoryStore } from '@/store/history';
import {
  currentMember,
  MEMBER_STORAGE_KEY,
  type MemberInfo,
} from '@/store/memberPrefs';

/**
 * 成员 store —— 成员账号管理。
 *
 * 定位:成员即登录账号(用户名 + 密码,见登录页与后端 /api/auth),
 * 登录成功由 auth store 确定当前成员;本 store 负责账号列表与增删,
 * 以及 select() 带来的数据源切换(收藏/播放历史按成员隔离,云端 + 本地双份)。
 *
 * 行为约定:
 * - 未选成员(理论上仅登录前的瞬间)时完全回退旧的纯本地行为,不阻断功能;
 * - 切换账号 = 「我的」页退出登录 → 登录页用另一账号登录(不做免密切换);
 * - 创建账号仅已登录用户可用(首个账号在登录页开放注册,由 auth store 走这里)。
 */

export const useMemberStore = defineStore('member', () => {
  /** 成员账号列表(账号管理页用) */
  const members = ref<MemberInfo[]>([]);

  /** 拉取成员列表并校验本地记录的当前成员仍存在(被删则退回未选状态) */
  async function refresh(): Promise<void> {
    try {
      members.value = await request<MemberInfo[]>({ url: '/api/members' });
      if (currentMember.value && !members.value.some((m) => m.id === currentMember.value!.id)) {
        await select(null);
      }
    } catch (err) {
      // 服务不可用:保持本地现状,管理页由调用方提示
      console.warn('获取成员列表失败:', err);
      throw err;
    }
  }

  /** 切换成员(null = 未选,回退纯本地模式)。本地立即生效,云端列表尽力覆盖。 */
  async function select(member: MemberInfo | null): Promise<void> {
    currentMember.value = member;
    try {
      if (member) uni.setStorageSync(MEMBER_STORAGE_KEY, member);
      else uni.removeStorageSync(MEMBER_STORAGE_KEY);
    } catch { /* 存储失败不影响本次会话 */ }
    await Promise.all([
      useLibraryStore().adoptMember(member?.id ?? null),
      useHistoryStore().adoptMember(member?.id ?? null),
    ]);
  }

  /** 创建成员账号(用户名唯一;密码在后端散列存储,此处明文仅存在于请求体) */
  async function create(
    username: string,
    password: string,
    name: string,
    avatar: string,
  ): Promise<MemberInfo> {
    const member = await request<MemberInfo>({
      url: '/api/members',
      method: 'POST',
      data: { username, password, name, avatar },
    });
    members.value = [...members.value, member];
    return member;
  }

  /** 删除成员账号(其云端收藏/历史级联删除;不能删当前登录账号,后端校验) */
  async function remove(memberId: string): Promise<void> {
    await request({ url: `/api/members/${memberId}`, method: 'DELETE' });
    members.value = members.value.filter((m) => m.id !== memberId);
    if (currentMember.value?.id === memberId) {
      await select(null);
    }
  }

  return { members, refresh, select, create, remove };
});
