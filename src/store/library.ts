import { defineStore } from 'pinia';
import { useIdMetaList } from '@/composables/useIdMetaList';

/**
 * 音乐库 store —— 管理「我喜欢的音乐」(本地持久化)。
 * 使用 uni.setStorageSync / getStorageSync,跨端一致(见 CLAUDE.md 第 5、6 节)。
 * likedSongs 为 id 对应的轻量元数据,增量补全逻辑见 useIdMetaList。
 */

const LIKE_KEY = 'music_liked_ids';

export const useLibraryStore = defineStore('library', () => {
  const { ids: likedIds, songs: likedSongs, persist } = useIdMetaList(LIKE_KEY);

  /** 是否已收藏 */
  function isLiked(songId: string): boolean {
    return likedIds.value.includes(songId);
  }

  /** 切换某首歌的收藏状态并持久化 */
  function toggleLike(songId: string) {
    const idx = likedIds.value.indexOf(songId);
    if (idx >= 0) {
      likedIds.value.splice(idx, 1);
    } else {
      likedIds.value.push(songId);
    }
    persist();
  }

  return { likedIds, likedSongs, isLiked, toggleLike };
});
