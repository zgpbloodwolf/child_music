<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { onLoad, onReachBottom } from '@dcloudio/uni-app';
import type { SubCategory, Category } from '@/types/category';
import { getRepository, type PageResult, type SongQuery } from '@/repository';
import { usePlayerStore } from '@/store/player';
import SongItem from '@/components/SongItem/SongItem.vue';
import CoverImage from '@/components/CoverImage/CoverImage.vue';
import MiniPlayer from '@/components/MiniPlayer/MiniPlayer.vue';
import type { CoverVariant } from '@/components/CoverImage/CoverImage.vue';
import { coverVariantOf } from '@/components/CoverImage/CoverImage.vue';
import type { SongMeta } from '@/types/song';

/**
 * 歌单详情页:支持四种来源(互斥)
 * - ?sub=xx    按子分类(如「唐诗」)渲染该子分类下音频
 * - ?author=xx 按作者(如「李白」)渲染该作者在 poetry 大类下的作品
 * - ?cat=xx    按大类渲染(首页分类区「全部歌曲」入口)
 * - ?all=1     整个曲库
 * 页面背景/标题/按钮按来源大类沿用分类皮肤,与首页分类区连贯(不断皮)。
 *
 * 数据分两条路径,同一批数据不重复传输:
 * - id 队列:repo.listIds(query) 一次取回「完整且有序」的 id(体积约为带元数据的 1/10),
 *   供「N 首」计数与 player.playList 入队使用(队列必须是完整的,否则播到已加载末尾就断了);
 * - 列表内容:repo.listPage(query, {page,size}) 由服务端分页返回本页元数据。
 * 两者复用同一个 listQuery,顺序口径一致,故 listSongs 的下标可直接映射到队列下标。
 */
type ListMode = 'sub' | 'author' | 'cat' | 'all';

const player = usePlayerStore();
const repo = getRepository();
const mode = ref<ListMode>('sub');
const subId = ref('');
const authorName = ref('');
/** cat 模式:目标大类 id */
const catId = ref('');
/** cat 模式:大类元信息(标题/描述) */
const catMeta = ref<Category | null>(null);

/** 子分类(仅 sub 模式有值,异步加载) */
const sub = ref<SubCategory | null>(null);
/** 当前皮肤主题(异步:作者模式恒 poetry,子分类模式取所属大类) */
const theme = ref<string>('');

/** 当前列表的歌曲 id(来源随 mode 变化,异步加载) */
const songIds = ref<string[]>([]);
/** 首屏加载中(loadMeta→loadIds→loadFirstPage 整个链路) */
const initialLoading = ref(true);
/** 加载失败标记(区分「暂无音频」与「加载失败」) */
const loadError = ref(false);

// ===== 分页加载 =====
/** 每页加载数量 */
const PAGE_SIZE = 30;
/** 当前已加载页数 */
const loadedPage = ref(0);
/** 是否正在加载更多 */
const loadingMore = ref(false);
/** 是否还有更多数据 */
const hasMore = ref(true);

/** 加载分类元数据(sub + theme);loadIds 依赖 sub,需先完成 */
async function loadMeta(): Promise<void> {
  if (mode.value === 'sub') {
    // 两次查询互不依赖,并行以省一个 RTT
    const [s, catId] = await Promise.all([
      repo.findSub(subId.value),
      repo.categoryIdOfSub(subId.value),
    ]);
    sub.value = s;
    theme.value = catId ?? '';
  } else if (mode.value === 'cat') {
    sub.value = null;
    const cats = await repo.getCategories();
    catMeta.value = cats.find((c) => c.id === catId.value) ?? null;
    theme.value = catId.value;
  } else if (mode.value === 'all') {
    sub.value = null;
    catMeta.value = null;
    theme.value = '';
  } else {
    sub.value = null;
    theme.value = 'poetry';
  }
}

/**
 * 当前列表的查询条件(由 mode 派生)。
 * id 队列与分页内容共用同一条件,保证两者口径一致;返回 null 表示无有效来源
 * (如 sub 模式但子分类不存在),此时 id 与列表都为空。
 */
const listQuery = computed<SongQuery | null>(() => {
  if (mode.value === 'author') return { category: 'poetry', author: authorName.value };
  if (mode.value === 'cat') return { category: catId.value };
  if (mode.value === 'sub') return sub.value ? { subCategory: sub.value.id } : null;
  return {}; // all:整个曲库
});

/** 仅取 id 队列(不含元数据)。用于「N 首」计数与播放入队。 */
async function loadIds(): Promise<void> {
  const query = listQuery.value;
  songIds.value = query ? await repo.listIds(query) : [];
}

/** 取第 page 页(从 1 开始)列表内容,由服务端分页。 */
async function loadPage(page: number): Promise<PageResult<SongMeta>> {
  const query = listQuery.value;
  if (!query) return { items: [], total: 0, page, pageSize: PAGE_SIZE };
  return repo.listPage(query, { number: page, size: PAGE_SIZE });
}

/** 加载第一页数据 */
async function loadFirstPage(): Promise<void> {
  loadedPage.value = 0;
  hasMore.value = true;
  listSongs.value = [];

  const res = await loadPage(1);
  listSongs.value = res.items;
  loadedPage.value = 1;
  hasMore.value = listSongs.value.length < res.total;
}

/** 加载更多数据(下一页) */
async function loadMore(): Promise<void> {
  if (loadingMore.value || !hasMore.value) return;

  loadingMore.value = true;
  try {
    const res = await loadPage(loadedPage.value + 1);
    listSongs.value = [...listSongs.value, ...res.items];
    loadedPage.value += 1;
    // 以服务端 total 判定是否还有下一页,不再依赖本地 id 数组的切片长度
    hasMore.value = listSongs.value.length < res.total;
  } finally {
    loadingMore.value = false;
  }
}

/** 完整加载链路:元数据 → (id 队列 ‖ 第一页)。失败置 loadError(展示错误态
 * 而非误报「暂无音频」),成功自动清除;供 watch 与手动重试共用。
 * id 队列与列表内容互不依赖(listQuery 在 loadMeta 后即确定),故并行发出。 */
async function reload(): Promise<void> {
  initialLoading.value = true;
  loadError.value = false;
  try {
    await loadMeta();
    await Promise.all([loadIds(), loadFirstPage()]);
  } catch (err) {
    console.warn('歌单加载失败:', err);
    loadError.value = true;
  } finally {
    initialLoading.value = false;
  }
}

/** mode / subId / authorName 变化时重载(onLoad 改值即触发) */
watch([mode, subId, authorName, catId], () => { void reload(); });

/** 歌曲对象列表(按 id 异步取元数据,分页加载) */
const listSongs = ref<SongMeta[]>([]);

/** 触底加载更多 */
onReachBottom(() => {
  void loadMore();
});

/** 头部标题:sub 取子分类名,author 取作者名,cat 取大类名 */
const headerTitle = computed(() => {
  if (mode.value === 'author') return authorName.value;
  if (mode.value === 'cat') return catMeta.value?.name ?? '';
  if (mode.value === 'all') return '全部音频';
  return sub.value?.name ?? '';
});
/** 头部描述 */
const headerDesc = computed(() => {
  if (mode.value === 'author') return `${authorName.value} 的古诗作品`;
  if (mode.value === 'cat') return catMeta.value?.desc ?? '';
  if (mode.value === 'all') return '所有歌曲';
  return sub.value?.desc ?? '';
});
/** 作者模式:头部封面用朱砂方印 */
const isAuthor = computed(() => mode.value === 'author');
/** sub 模式:取第一首作品封面 */
const cover = computed(() => listSongs.value[0]?.cover);

/** 头部封面兜底色:作者用朱砂方印;其余按所属大类映射(映射集中在 CoverImage 导出) */
const coverVariant = computed<CoverVariant>(() => {
  if (mode.value === 'author') return 'seal';
  return coverVariantOf(theme.value);
});

onLoad((options) => {
  const author = options?.author;
  const subOpt = options?.sub;
  const catOpt = options?.cat;
  const allOpt = options?.all;
  if (typeof author === 'string' && author) {
    mode.value = 'author';
    authorName.value = author;
  } else if (typeof catOpt === 'string' && catOpt) {
    mode.value = 'cat';
    catId.value = catOpt;
  } else if (typeof allOpt === 'string' && allOpt) {
    mode.value = 'all';
  } else if (typeof subOpt === 'string' && subOpt) {
    mode.value = 'sub';
    subId.value = subOpt;
  } else {
    // 无任何有效参数:四个 ref 均未变化,watch 不会触发,手动兜底走一次加载链路
    void reload();
  }
});

/** 从指定位置播放当前列表 */
function playFrom(index: number) {
  if (songIds.value.length) player.playList(songIds.value, index);
}
/** 播放全部:以当前列表为队列从头播放,并跳转播放页(进入沉浸控制) */
function playAll() {
  if (!songIds.value.length) return;
  player.playList(songIds.value, 0);
  uni.navigateTo({ url: '/pages/player/index' });
}
</script>

<template>
  <view
    class="page"
    :class="{
      'page--children': theme === 'children',
      'page--poetry': theme === 'poetry',
      'page--classics': theme === 'classics',
      'page--story': theme === 'story',
    }"
  >
    <view class="header">
      <view class="header-cover">
        <CoverImage v-if="isAuthor" variant="seal" :placeholder="authorName.charAt(0)" />
        <CoverImage v-else :src="cover" :name="headerTitle" :variant="coverVariant" />
      </view>
      <view class="header-info">
        <text class="title">{{ headerTitle }}</text>
        <text class="desc">{{ headerDesc }}</text>
        <text class="count">{{ songIds.length }} 首</text>
      </view>
    </view>

    <view class="play-all" @click="playAll">▶ 播放全部({{ songIds.length }} 首)</view>

    <view class="song-list">
      <SongItem
        v-for="(song, i) in listSongs"
        :key="song.id"
        :song="song"
        :index="i"
        @play="playFrom(i)"
      />
    </view>

    <!-- 加载状态 -->
    <view v-if="loadingMore" class="loading-more">
      <text>加载中...</text>
    </view>
    <view v-else-if="!hasMore && listSongs.length > 0" class="no-more">
      <text>已加载全部 {{ listSongs.length }} 首</text>
    </view>

    <!-- 首屏加载 / 失败(可点击重试)/ 真空态三分支 -->
    <view v-if="initialLoading" class="empty">
      <text>加载中...</text>
    </view>
    <view v-else-if="loadError" class="empty" @click="reload()">
      <text>加载失败,点击重试</text>
    </view>
    <view v-else-if="listSongs.length === 0" class="empty">
      <text>该分类暂无音频</text>
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
.header {
  display: flex;
  align-items: center;
  padding: 24rpx;
}
.header-cover {
  width: 200rpx;
  height: 200rpx;
  flex-shrink: 0;
}
.header-info {
  flex: 1;
  min-width: 0;
  margin-left: 24rpx;
  display: flex;
  flex-direction: column;
}
.title {
  font-size: 36rpx;
  font-weight: bold;
  color: $text-main;
}
.desc {
  margin-top: 12rpx;
  font-size: 24rpx;
  color: $text-sub;
}
.count {
  margin-top: 12rpx;
  font-size: 24rpx;
  color: $text-sub;
}
.play-all {
  margin: 16rpx 24rpx 0;
  padding: 24rpx 0;
  text-align: center;
  color: #ffffff;
  font-size: 28rpx;
  background: $primary;
  border-radius: 999rpx;
}
.song-list {
  margin: 16rpx 16rpx 0;
  background: $bg-card;
  border-radius: 16rpx;
  overflow: hidden;
}
.empty {
  margin-top: 80rpx;
  text-align: center;
  color: $text-sub;
  font-size: 26rpx;
}
.loading-more,
.no-more {
  padding: 32rpx 0;
  text-align: center;
  color: $text-sub;
  font-size: 24rpx;
}

/* ===== 分类皮肤:按来源大类沿用首页风格(字面量 class,避免 scoped + 小程序丢哈希) ===== */
.page--children {
  background: linear-gradient(180deg, $children-bg-start, $children-bg-end);
}
.page--children .title {
  color: $children-text;
}
.page--children .desc,
.page--children .count {
  color: $children-text-sub;
}
.page--children .play-all {
  background: linear-gradient(135deg, $children-play-start, $children-play-end);
  box-shadow: 0 8rpx 20rpx rgba($children-accent, 0.35);
  font-weight: bold;
}
.page--children .empty,
.page--children .loading-more,
.page--children .no-more {
  color: $children-text-sub;
}

.page--poetry {
  background: linear-gradient(180deg, $poetry-paper, $poetry-paper-deep);
  font-family: 'KaiTi', 'STKaiti', '楷体', serif;
}
.page--poetry .title {
  color: $poetry-ink;
}
.page--poetry .desc,
.page--poetry .count {
  color: $poetry-ink-sub;
}
.page--poetry .play-all {
  background: $poetry-ink;
  color: $poetry-paper;
}
.page--poetry .empty,
.page--poetry .loading-more,
.page--poetry .no-more {
  color: $poetry-ink-sub;
}

.page--classics {
  background:
    repeating-linear-gradient(90deg, rgba($classics-accent, 0.05) 0 4rpx, transparent 4rpx 32rpx),
    linear-gradient(180deg, $classics-bg-start, $classics-bg-end);
  font-family: 'KaiTi', 'STKaiti', '楷体', serif;
}
.page--classics .title {
  color: $classics-text;
}
.page--classics .desc,
.page--classics .count {
  color: $classics-text-sub;
}
.page--classics .play-all {
  background: $classics-accent;
  color: $classics-bg-start;
}
.page--classics .empty,
.page--classics .loading-more,
.page--classics .no-more {
  color: $classics-text-sub;
}

.page--story {
  background:
    radial-gradient(circle at 86% 8%, rgba($story-moon, 0.18), transparent 30%),
    linear-gradient(180deg, $story-bg-start, $story-bg-end);
}
.page--story .title {
  color: $story-text;
}
.page--story .desc,
.page--story .count {
  color: $story-text-sub;
}
.page--story .play-all {
  background: linear-gradient(135deg, $story-play-start, $story-play-end);
  box-shadow: 0 8rpx 20rpx rgba($story-accent, 0.3);
  font-weight: bold;
}
.page--story .empty,
.page--story .loading-more,
.page--story .no-more {
  color: $story-text-sub;
}
.bottom-pad {
  height: 160rpx;
}
</style>
