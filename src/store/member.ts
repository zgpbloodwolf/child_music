import { defineStore } from 'pinia';
import { useLibraryStore } from '@/store/library';
import { useHistoryStore } from '@/store/history';
import {
  currentMember,
  MEMBER_STORAGE_KEY,
  type MemberInfo,
} from '@/store/memberPrefs';

/**
 * 成员 store —— 登录身份在客户端的落地点。
 *
 * 定位:成员即登录账号(用户名 + 密码,见登录页与后端 /api/auth),
 * 登录成功由 auth store 调用 select() 确定当前成员;账号的创建/删除/列表
 * 只在管理后台进行,App 内不提供增删,也看不到其他账号。
 *
 * select() 负责「当前成员」的本地持久化,并带动收藏/播放历史切换
 * 数据源(按成员隔离,云端 + 本地双份)。
 *
 * 行为约定:
 * - 未选成员(理论上仅登录前的瞬间)时完全回退旧的纯本地行为,不阻断功能;
 * - 切换账号 = 「我的」页退出登录 → 登录页用另一账号登录(不做免密切换)。
 */

export const useMemberStore = defineStore('member', () => {
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

  return { select };
});
