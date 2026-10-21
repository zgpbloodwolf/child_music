import { defineStore } from 'pinia';
import { useIdMetaList } from '@/composables/useIdMetaList';
import { request } from '@/utils/request';
import { LIKE_KEY, currentMember, scopedKey } from '@/store/memberPrefs';

/**
 * 音乐库 store —— 管理「我喜欢的音乐」。
 *
 * 数据分层(成员机制引入后):
 * - UI 立即生效:内存 ids 即改即见,并写入「当前成员」的本地缓存
 *   (未选成员时回退旧版全局 key,与升级前行为完全一致);
 * - 云端同步:每次变更把完整 id 列表 PUT 到 /api/members/{id}/favorites
 *   (客户端全量、服务端照单全收,见 routers/members.py),经串行链保证
 *   连续变更按序到达;失败静默,下次变更自然重试。
 *
 * likedSongs 为 id 对应的轻量元数据,增量补全逻辑见 useIdMetaList。
 */

export const useLibraryStore = defineStore('library', () => {
  const { ids: likedIds, songs: likedSongs, persist, resetKey } = useIdMetaList(
    // 初始 key 按当前成员确定:选中成员则读成员专属缓存,否则读旧版全局 key
    scopedKey(LIKE_KEY, currentMember.value?.id),
  );

  /** 云端回写串行链:连续快速变更时保证 PUT 按序到达(后写覆盖先写) */
  let pushChain: Promise<void> = Promise.resolve();

  /** 是否已选成员(未选 = 纯本地模式,不与云端同步) */
  function cloudEnabled(): boolean {
    return currentMember.value !== null;
  }

  /** 是否已收藏 */
  function isLiked(songId: string): boolean {
    return likedIds.value.includes(songId);
  }

  /** 收藏列表回写云端(未选成员时跳过) */
  function pushFavorites(): Promise<void> {
    const memberId = currentMember.value?.id;
    if (!memberId) return Promise.resolve();
    const snapshot = [...likedIds.value];
    pushChain = pushChain.then(async () => {
      try {
        await request({
          url: `/api/members/${memberId}/favorites`,
          method: 'PUT',
          data: { songIds: snapshot },
        });
      } catch (err) {
        console.warn('收藏云端同步失败(下次变更自动重试):', err);
      }
    });
    return pushChain;
  }

  /** 切换某首歌的收藏状态:本地立即持久化 + 云端回写 */
  function toggleLike(songId: string) {
    const idx = likedIds.value.indexOf(songId);
    if (idx >= 0) {
      likedIds.value.splice(idx, 1);
    } else {
      likedIds.value.push(songId);
    }
    persist();
    void pushFavorites();
  }

  /**
   * 成员切换(由 member store 调用):重指该成员的本地缓存 key,
   * 并尽力拉取云端列表覆盖;拉取失败沿用本地缓存(离线兜底)。
   */
  async function adoptMember(memberId: string | null): Promise<void> {
    resetKey(scopedKey(LIKE_KEY, memberId));
    if (!memberId) return;
    try {
      const remote = await request<string[]>({ url: `/api/members/${memberId}/favorites` });
      likedIds.value = remote;
      persist();
    } catch (err) {
      console.warn('拉取云端收藏失败,沿用本地缓存:', err);
    }
  }

  return { likedIds, likedSongs, isLiked, toggleLike, adoptMember };
});
