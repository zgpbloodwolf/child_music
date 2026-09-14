import { defineStore } from 'pinia';
import { useIdMetaList } from '@/composables/useIdMetaList';

/**
 * 播放历史 store —— 「最近播放 / 继续听」(本地持久化)。
 * 记录最近听过的音频 id(最新的在前,去重,上限 MAX_HISTORY)。
 * recent 为 id 对应的轻量元数据,增量补全逻辑见 useIdMetaList。
 */

const HISTORY_KEY = 'music_history_ids';
/** 最多保留多少条历史 */
const MAX_HISTORY = 20;

export const useHistoryStore = defineStore('history', () => {
  const { ids, songs, persist } = useIdMetaList(HISTORY_KEY);

  /** 历史 id 列表(最新在前) */
  // ids 已由 useIdMetaList 提供,此处重命名导出保持对外接口不变
  const recent = songs;

  /** 新增一条播放记录(去重并置顶,超过上限截断)并持久化 */
  function add(songId: string) {
    ids.value = [songId, ...ids.value.filter((id) => id !== songId)].slice(0, MAX_HISTORY);
    persist();
  }

  /** 清空历史 */
  function clear() {
    ids.value = [];
    persist();
  }

  return { ids, recent, add, clear };
});
