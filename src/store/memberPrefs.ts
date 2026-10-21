import { ref } from 'vue';

/**
 * 成员相关的常量与「当前成员」共享状态。
 *
 * 独立成模块(而非塞进 member store)是为了避免 store 间循环依赖:
 * library/history 需要在**模块初始化阶段**就读到当前成员来决定本地存储 key,
 * member store 又要在切换时调用它们 —— 共享 ref 收敛在此,三方都只依赖本模块。
 */

/** 成员信息(对齐后端 MemberOut;createdAt 前端未消费,不进类型) */
export interface MemberInfo {
  id: string;
  name: string;
  /** 登录账号(小写;旧数据可能缺失) */
  username?: string;
  avatar: string;
}

/** 当前选中成员的本地持久化 key */
export const MEMBER_STORAGE_KEY = 'music_member_current';
/** 收藏 ids 的本地存储 key 基名(选中成员后实际 key 为 `${LIKE_KEY}:${memberId}`) */
export const LIKE_KEY = 'music_liked_ids';
/** 播放历史 ids 的本地存储 key 基名(同上) */
export const HISTORY_KEY = 'music_history_ids';

/** 可选头像(emoji:跨端渲染稳定,不引入图片资源与裁切链路) */
export const MEMBER_AVATARS = ['⭐', '🐱', '🦊', '🐰', '🐻', '🌈', '🚗', '🌸'] as const;

/** 读取当前成员(坏数据按未选处理) */
function loadCurrentMember(): MemberInfo | null {
  try {
    const raw = uni.getStorageSync(MEMBER_STORAGE_KEY) as unknown;
    if (
      raw
      && typeof raw === 'object'
      && typeof (raw as MemberInfo).id === 'string'
      && typeof (raw as MemberInfo).name === 'string'
    ) {
      return raw as MemberInfo;
    }
  } catch { /* 坏数据回退未选 */ }
  return null;
}

/**
 * 当前成员(模块级共享 ref):member store 负责写入,library/history store 只读。
 * 初始值在首次 import 时即确定,保证各数据 store 建立时就能拿到正确的存储 key。
 */
export const currentMember = ref<MemberInfo | null>(loadCurrentMember());

/** 成员维度的存储 key:未选成员时回退旧版 key(完全兼容旧数据与离线场景) */
export function scopedKey(baseKey: string, memberId: string | null | undefined): string {
  return memberId ? `${baseKey}:${memberId}` : baseKey;
}
