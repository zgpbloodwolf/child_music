import { defineStore } from 'pinia';
import { ref, watch } from 'vue';
import type { SongMeta } from '@/types/song';
import { getRepository } from '@/repository';

/**
 * 音乐库 store —— 管理「我喜欢的音乐」(本地持久化)。
 * 使用 uni.setStorageSync / getStorageSync,跨端一致(见 CLAUDE.md 第 5、6 节)。
 * likedSongs 为 id 对应的轻量元数据,通过 Repository 异步映射。
 */

const LIKE_KEY = 'music_liked_ids';

/** 曲库数据源(模块级单例) */
const repo = getRepository();

/** 从本地存储读取已收藏的歌曲 id 列表 */
function loadLikedIds(): string[] {
  try {
    const raw = uni.getStorageSync(LIKE_KEY);
    if (Array.isArray(raw)) {
      return raw.filter((id: unknown): id is string => typeof id === 'string');
    }
    return [];
  } catch (e) {
    console.error('读取收藏列表失败:', e);
    return [];
  }
}

export const useLibraryStore = defineStore('library', () => {
  /** 已收藏的歌曲 id 列表 */
  const likedIds = ref<string[]>(loadLikedIds());

  /** 已收藏的歌曲元数据列表(按收藏顺序,与 likedIds 同步) */
  const likedSongs = ref<SongMeta[]>([]);

  // likedIds 变化时通过 Repository 异步映射;immediate 保证初始化即加载
  watch(likedIds, async (newIds) => {
    likedSongs.value = await repo.listByIds(newIds);
  }, { immediate: true, deep: true });

  /** 是否已收藏 */
  function isLiked(songId: string): boolean {
    return likedIds.value.includes(songId);
  }

  /** 持久化到本地存储 */
  function persist() {
    uni.setStorageSync(LIKE_KEY, likedIds.value);
  }

  /** 切换某首歌的收藏状态 */
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
