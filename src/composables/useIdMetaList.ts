import { ref, watch } from 'vue';
import type { SongMeta } from '@/types/song';
import { getRepository } from '@/repository';

/**
 * 「本地持久化 id 列表 + 按需补全的元数据列表」组合式函数。
 *
 * history(最近播放)与 library(我的收藏)同构:ids 落 uni storage、
 * 元数据经 Repository 增量补全后按 ids 顺序组装;差异只在变更动作
 * (置顶去重 / 切换收藏),由各 store 自行封装,公共部分收敛在此。
 *
 * metaCache 为模块级共享:两个 store 的列表常有大量重叠(最近播放过的
 * 歌往往也被收藏),共享后同一首歌的元数据全程只请求一次。
 */

/** 曲库数据源(模块级单例) */
const repo = getRepository();
/** id → 元数据 共享缓存(增量补全,避免全量重拉) */
const metaCache = new Map<string, SongMeta>();

/** 从本地存储读取 id 列表(坏数据兜底为空数组) */
function loadIds(key: string): string[] {
  try {
    const raw = uni.getStorageSync(key);
    if (Array.isArray(raw)) {
      return raw.filter((id: unknown): id is string => typeof id === 'string');
    }
    return [];
  } catch (e) {
    console.error(`读取本地 id 列表失败(${key}):`, e);
    return [];
  }
}

/**
 * @param storageKey 本地存储 key(ids 持久化位置)
 * @returns ids:id 列表(含义由调用方决定:最新在前 / 收藏顺序);
 *          songs:ids 对应的元数据列表(与 ids 同步同序);persist:落盘
 */
export function useIdMetaList(storageKey: string) {
  const ids = ref<string[]>(loadIds(storageKey));
  const songs = ref<SongMeta[]>([]);

  /** 按 ids 顺序组装 songs;仅对缓存缺失的 id 发请求(增量)。 */
  async function refresh(): Promise<void> {
    const missing = ids.value.filter((id) => !metaCache.has(id));
    if (missing.length > 0) {
      const got = await repo.listByIds(missing);
      got.forEach((s) => metaCache.set(s.id, s));
    }
    songs.value = ids.value
      .map((id) => metaCache.get(id))
      .filter((s): s is SongMeta => Boolean(s));
  }

  // ids 变化时按需补全缓存并重组 songs;immediate 保证初始化即加载
  watch(ids, () => { void refresh(); }, { immediate: true, deep: true });

  /** 持久化 ids 到本地存储(变更动作后由调用方调用) */
  function persist(): void {
    uni.setStorageSync(storageKey, ids.value);
  }

  return { ids, songs, refresh, persist };
}
