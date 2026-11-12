import { defineStore } from 'pinia';
import { useIdMetaList } from '@/composables/useIdMetaList';
import { request } from '@/utils/request';
import { HISTORY_KEY, currentMember, scopedKey } from '@/store/memberPrefs';

/**
 * 播放历史 store —— 「最近播放 / 继续听」。
 *
 * 数据分层与 library store 同构(见其注释):本地立即生效 + 云端按当前成员
 * 全量回写 PUT /api/members/{id}/history(最新在前,服务端截断到 50 条)。
 * 未选成员时回退旧版全局 key,纯本地行为不变。
 *
 * 记录最近听过的音频 id(最新的在前,去重,上限 MAX_HISTORY)。
 * recent 为 id 对应的轻量元数据,增量补全逻辑见 useIdMetaList。
 */

/** 最多保留多少条历史(与服务端截断上限保持一致:云端拉回的列表最多 50 条,两端口径统一) */
const MAX_HISTORY = 50;

export const useHistoryStore = defineStore('history', () => {
  const { ids, songs, persist, resetKey } = useIdMetaList(
    scopedKey(HISTORY_KEY, currentMember.value?.id),
  );

  /** 云端回写串行链(同 library store) */
  let pushChain: Promise<void> = Promise.resolve();

  /** 历史 id 列表(最新在前) */
  // ids 已由 useIdMetaList 提供,此处重命名导出保持对外接口不变
  const recent = songs;

  /** 历史列表回写云端(未选成员时跳过) */
  function pushHistory(): Promise<void> {
    const memberId = currentMember.value?.id;
    if (!memberId) return Promise.resolve();
    const snapshot = [...ids.value];
    pushChain = pushChain.then(async () => {
      try {
        await request({
          url: `/api/members/${memberId}/history`,
          method: 'PUT',
          data: { songIds: snapshot },
        });
      } catch (err) {
        console.warn('历史云端同步失败(下次变更自动重试):', err);
      }
    });
    return pushChain;
  }

  /** 新增一条播放记录(去重并置顶,超过上限截断):本地持久化 + 云端回写 */
  function add(songId: string) {
    ids.value = [songId, ...ids.value.filter((id) => id !== songId)].slice(0, MAX_HISTORY);
    persist();
    void pushHistory();
  }

  /** 清空历史 */
  function clear() {
    ids.value = [];
    persist();
    void pushHistory();
  }

  /** 成员切换(由 member store 调用):重指该成员本地缓存 + 云端覆盖 */
  async function adoptMember(memberId: string | null): Promise<void> {
    resetKey(scopedKey(HISTORY_KEY, memberId));
    if (!memberId) return;
    try {
      const remote = await request<string[]>({ url: `/api/members/${memberId}/history` });
      ids.value = remote;
      persist();
    } catch (err) {
      console.warn('拉取云端历史失败,沿用本地缓存:', err);
    }
  }

  return { ids, recent, add, clear, adoptMember };
});
