<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue';
import { onReachBottom } from '@dcloudio/uni-app';
import { getRepository } from '@/repository';
import { usePlayerStore } from '@/store/player';
import SongItem from '@/components/SongItem/SongItem.vue';
import MiniPlayer from '@/components/MiniPlayer/MiniPlayer.vue';
import type { SongMeta } from '@/types/song';

/**
 * 搜索页:按歌名 / 歌手 / 专辑搜索曲库。
 * 经 Repository 走后端接口(`GET /api/songs?keyword=`),不在前端内存过滤。
 * 结果由服务端分页(listPage,每页 SEARCH_PAGE_SIZE 条),触底加载下一页:
 * 关键词命中整库上千条时也不会一次挂载全部节点。
 */
const player = usePlayerStore();
const repo = getRepository();
const keyword = ref('');
/** 搜索结果(分页增量追加) */
const results = ref<SongMeta[]>([]);
/** 服务端总命中数(标题计数用,与已加载数区分) */
const total = ref(0);
/** 首屏(第一页)搜索中 */
const searching = ref(false);
/** 搜索请求失败标记:区分「无结果」与「失败」,失败时不误报「没有找到」 */
const searchFailed = ref(false);
/** 已加载页数(从 1 起,0 表示尚未加载) */
const loadedPage = ref(0);
/** 是否正在加载下一页 */
const loadingMore = ref(false);
/** 加载下一页失败标记(列表尾「点击重试」) */
const moreFailed = ref(false);
/** 是否还有下一页 */
const hasMore = ref(false);

/** 每页条数(与歌单页 PAGE_SIZE 一致) */
const SEARCH_PAGE_SIZE = 30;

/** 防抖句柄:输入停顿 350ms 后才发请求,避免在线数据源下每键一字都打一次接口 */
let searchTimer: ReturnType<typeof setTimeout> | null = null;
/**
 * 搜索序号:每次发起搜索时自增取号,回包时比对。
 * 防抖只挡住「连打」,挡不住「先发的请求后返回」——若无此守卫,慢响应会用
 * 旧关键词的结果覆盖新关键词的结果。与 player.ts 的 loadSeq 同一模式。
 */
let searchSeq = 0;

/** 复位结果与分页状态(新搜索发起 / 清空关键词时) */
function resetPaging(): void {
  results.value = [];
  total.value = 0;
  loadedPage.value = 0;
  hasMore.value = false;
  moreFailed.value = false;
}

/** 发起第一页搜索(防抖到点 / 失败重试共用) */
async function runSearch(kw: string): Promise<void> {
  const seq = ++searchSeq;
  searching.value = true;
  searchFailed.value = false;
  resetPaging();
  try {
    const res = await repo.listPage({ keyword: kw }, { number: 1, size: SEARCH_PAGE_SIZE });
    if (seq !== searchSeq) return; // 已被更新的关键词取代,丢弃本次结果
    results.value = res.items;
    total.value = res.total;
    loadedPage.value = 1;
    hasMore.value = res.items.length < res.total;
  } catch (err) {
    if (seq !== searchSeq) return; // 同上:旧请求的失败不应影响最新一次搜索的展示
    console.warn('搜索失败:', err);
    searchFailed.value = true;
  } finally {
    // 只有最新一次请求才能解除加载态,避免旧请求提前把「搜索中」关掉
    if (seq === searchSeq) searching.value = false;
  }
}

/** 加载下一页(触底 / 失败重试共用;关键词沿用当前输入) */
async function loadMore(): Promise<void> {
  const kw = keyword.value.trim();
  if (!kw || searching.value || loadingMore.value || !hasMore.value) return;
  // 不取新号(关键词未变),仅记录当前号:回包时若已发起新搜索则丢弃
  const seq = searchSeq;
  loadingMore.value = true;
  moreFailed.value = false;
  try {
    const res = await repo.listPage(
      { keyword: kw },
      { number: loadedPage.value + 1, size: SEARCH_PAGE_SIZE },
    );
    if (seq !== searchSeq) return; // 期间已发起新搜索,丢弃本次结果
    results.value = [...results.value, ...res.items];
    loadedPage.value += 1;
    hasMore.value = results.value.length < res.total;
  } catch (err) {
    if (seq !== searchSeq) return;
    console.warn('加载更多失败:', err);
    moreFailed.value = true;
  } finally {
    loadingMore.value = false;
  }
}

/** 关键词变化时异步搜索(防抖;空关键词立即清空结果) */
watch(keyword, (kw) => {
  if (searchTimer) clearTimeout(searchTimer);
  const trimmed = (kw ?? '').trim();
  if (!trimmed) {
    // 清空关键词也要取号:使在途响应作废,否则迟到的结果会重新填满已清空的列表
    searchSeq += 1;
    searching.value = false;
    searchFailed.value = false;
    resetPaging();
    return;
  }
  searchTimer = setTimeout(() => { void runSearch(trimmed); }, 350);
});

/** 触底加载下一页 */
onReachBottom(() => {
  void loadMore();
});

onUnmounted(() => {
  if (searchTimer) clearTimeout(searchTimer);
  searchSeq += 1; // 页面已卸载,使在途响应作废
});

/** 失败重试:沿用当前关键词重发第一页 */
function retrySearch() {
  const kw = keyword.value.trim();
  if (kw) void runSearch(kw);
}

/** 清空输入(结果由 watch 自动复位) */
function clearKeyword() {
  keyword.value = '';
}

/** 点击搜索结果:以当前结果列表为队列播放 */
function play(song: SongMeta) {
  player.playSong(song.id, results.value.map((s) => s.id));
}
</script>

<template>
  <view class="page">
    <view class="search-wrap">
      <view class="search-box">
        <input
          class="search-input"
          v-model="keyword"
          placeholder="搜索歌曲 / 歌手 / 专辑"
          confirm-type="search"
          :focus="true"
        />
        <text v-if="keyword" class="clear-btn" @click="clearKeyword">✕</text>
      </view>
    </view>

    <!-- 加载态(防抖 + 请求期间显示,避免闪现「没有找到」) -->
    <view v-if="keyword && searching" class="empty">
      <text>搜索中...</text>
    </view>

    <!-- 失败态(网络/服务异常,与「无结果」区分;点击重试) -->
    <view v-else-if="keyword && searchFailed" class="empty" @click="retrySearch">
      <text>搜索失败,点击重试</text>
    </view>

    <!-- 搜索结果(标题计数用服务端 total;列表分页增量) -->
    <view v-else-if="keyword && results.length" class="result-section">
      <text class="section-title">搜索结果({{ total }})</text>
      <view class="song-list">
        <SongItem
          v-for="song in results"
          :key="song.id"
          :song="song"
          @play="play(song)"
        />
      </view>
      <view v-if="loadingMore" class="more"><text>加载中...</text></view>
      <view v-else-if="moreFailed" class="more" @click="loadMore()">
        <text>加载失败,点击重试</text>
      </view>
      <view v-else-if="!hasMore" class="more"><text>已加载全部 {{ results.length }} 首</text></view>
    </view>

    <view v-else-if="keyword" class="empty">
      <text>没有找到相关歌曲</text>
    </view>

    <view v-else class="empty">
      <text>输入关键词搜索内置曲库</text>
    </view>

    <!-- 给底部悬浮播放栏预留滚动空间 -->
    <view class="bottom-pad" />
    <MiniPlayer />
  </view>
</template>

<style scoped lang="scss">
.page {
  min-height: 100vh;
}
.search-wrap {
  padding: 16rpx;
}
.search-box {
  display: flex;
  align-items: center;
  background: $bg-card;
  border-radius: 999rpx;
}
.search-input {
  flex: 1;
  min-width: 0;
  padding: 18rpx 24rpx;
  font-size: 28rpx;
  color: $text-main;
}
.clear-btn {
  flex-shrink: 0;
  padding: 12rpx 24rpx 12rpx 8rpx;
  font-size: 28rpx;
  color: $text-disable;
}
.result-section {
  padding: 0 16rpx;
}
.section-title {
  display: block;
  padding: 8rpx 8rpx 16rpx;
  font-size: 28rpx;
  font-weight: bold;
  color: $text-main;
}
.song-list {
  background: $bg-card;
  border-radius: 16rpx;
  overflow: hidden;
}
.more {
  padding: 24rpx 0;
  text-align: center;
  color: $text-sub;
  font-size: 24rpx;
}
.empty {
  margin-top: 120rpx;
  text-align: center;
  color: $text-sub;
  font-size: 26rpx;
}
.bottom-pad {
  height: 160rpx;
}
</style>
