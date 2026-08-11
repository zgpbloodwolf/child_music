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
/** id → 元数据 缓存:增量补全,避免每次收藏切换都全量 listByIds */
const metaCache = new Map<string, SongMeta>();

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

  /**
   * 按 likedIds 顺序组装 likedSongs;仅对缓存缺失的 id 发请求(增量)。
   * 首次加载建缓存,之后收藏一首新歌只补取那一条,不再全量重拉。
   */
  async function refresh() {
    const missing = likedIds.value.filter((id) => !metaCache.has(id));
    if (missing.length > 0) {
      const got = await repo.listByIds(missing);
      got.forEach((s) => metaCache.set(s.id, s));
    }
    likedSongs.value = likedIds.value
      .map((id) => metaCache.get(id))
      .filter((s): s is SongMeta => Boolean(s));
  }

  // likedIds 变化时按需补全缓存并重组 likedSongs;immediate 保证初始化即加载
  watch(likedIds, () => { void refresh(); }, { immediate: true, deep: true });

  /** 是否已收藏 */
  function isLiked(songId: string): boolean {
    return likedIds.value.includes(songId);
  }

  /** 持久化到本地存储 */
  function persist() {
    uni.setStorageSync(LIKE_KEY, likedIds.value);
  }

  /** 切换某首歌的收藏状态;增量补全/重组收藏列表 */
  function toggleLike(songId: string) {
    const idx = likedIds.value.indexOf(songId);
    if (idx >= 0) {
      likedIds.value.splice(idx, 1);
    } else {
      likedIds.value.push(songId);
    }
    persist();
    void refresh();
  }

  return { likedIds, likedSongs, isLiked, toggleLike };
});
