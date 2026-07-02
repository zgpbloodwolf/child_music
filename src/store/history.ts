import { defineStore } from 'pinia';
import { ref, watch } from 'vue';
import type { SongMeta } from '@/types/song';
import { getRepository } from '@/repository';

/**
 * 播放历史 store —— 「最近播放 / 继续听」(本地持久化)。
 * 记录最近听过的音频 id(最新的在前,去重,上限 MAX_HISTORY)。
 * recent 为 id 对应的轻量元数据,通过 Repository 异步映射(列表展示用,不含音频地址)。
 */

const HISTORY_KEY = 'music_history_ids';
/** 最多保留多少条历史 */
const MAX_HISTORY = 20;

/** 曲库数据源(模块级单例) */
const repo = getRepository();

/** 从本地存储读取历史 id 列表 */
function loadHistory(): string[] {
  try {
    const raw = uni.getStorageSync(HISTORY_KEY);
    if (Array.isArray(raw)) {
      return raw.filter((id: unknown): id is string => typeof id === 'string');
    }
    return [];
  } catch (e) {
    console.error('读取播放历史失败:', e);
    return [];
  }
}

export const useHistoryStore = defineStore('history', () => {
  /** 历史 id 列表(最新在前) */
  const ids = ref<string[]>(loadHistory());

  /** 历史歌曲元数据列表(最新在前,与 ids 同步) */
  const recent = ref<SongMeta[]>([]);

  // ids 变化时通过 Repository 异步映射为元数据;immediate 保证初始化即加载
  watch(ids, async (newIds) => {
    recent.value = await repo.listByIds(newIds);
  }, { immediate: true, deep: true });

  /** 新增一条播放记录(去重并置顶,超过上限截断) */
  function add(songId: string) {
    ids.value = [songId, ...ids.value.filter((id) => id !== songId)].slice(0, MAX_HISTORY);
    uni.setStorageSync(HISTORY_KEY, ids.value);
  }

  /** 清空历史 */
  function clear() {
    ids.value = [];
    uni.setStorageSync(HISTORY_KEY, ids.value);
  }

  return { ids, recent, add, clear };
});
