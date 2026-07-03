<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import { songsOfAuthor } from '@/data/poetry';
import type { SubCategory, Category } from '@/types/category';
import { getRepository } from '@/repository';
import { usePlayerStore } from '@/store/player';
import SongItem from '@/components/SongItem/SongItem.vue';
import CoverImage from '@/components/CoverImage/CoverImage.vue';
import type { CoverVariant } from '@/components/CoverImage/CoverImage.vue';
import type { SongMeta } from '@/types/song';

/**
 * 歌单详情页:支持两种来源(互斥)
 * - ?sub=xx    按子分类(如「唐诗」)渲染该子分类下音频
 * - ?author=xx 按作者(如「李白」)渲染该作者在 poetry 大类下的作品
 * 页面背景/标题/按钮按来源大类沿用分类皮肤,与首页分类区连贯(不断皮)。
 */
type ListMode = 'sub' | 'author' | 'cat';

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

/** 加载分类元数据(sub + theme);loadIds 依赖 sub,需先完成 */
async function loadMeta(): Promise<void> {
  if (mode.value === 'sub') {
    sub.value = await repo.findSub(subId.value);
    theme.value = (await repo.categoryIdOfSub(subId.value)) ?? '';
  } else if (mode.value === 'cat') {
    sub.value = null;
    const cats = await repo.getCategories();
    catMeta.value = cats.find((c) => c.id === catId.value) ?? null;
    theme.value = catId.value;
  } else {
    sub.value = null;
    theme.value = 'poetry';
  }
}

async function loadIds(): Promise<void> {
  if (mode.value === 'author') {
    songIds.value = await songsOfAuthor(authorName.value);
  } else if (mode.value === 'cat') {
    songIds.value = (await repo.listByCategory(catId.value)).map((s) => s.id);
  } else if (sub.value) {
    songIds.value = (await repo.listBySub(sub.value.id)).map((s) => s.id);
  } else {
    songIds.value = [];
  }
}

/** mode / subId / authorName 变化时先加载分类元数据,再加载歌曲 id(onLoad 改值即触发) */
watch([mode, subId, authorName, catId], async () => {
  await loadMeta();
  void loadIds();
});

/** 歌曲对象列表(按 id 异步取元数据) */
const listSongs = ref<SongMeta[]>([]);
watch(songIds, async (newIds) => {
  listSongs.value = await repo.listByIds(newIds);
});

/** 头部标题:sub 取子分类名,author 取作者名,cat 取大类名 */
const headerTitle = computed(() => {
  if (mode.value === 'author') return authorName.value;
  if (mode.value === 'cat') return catMeta.value?.name ?? '';
  return sub.value?.name ?? '';
});
/** 头部描述 */
const headerDesc = computed(() => {
  if (mode.value === 'author') return `${authorName.value} 的古诗作品`;
  if (mode.value === 'cat') return catMeta.value?.desc ?? '';
  return sub.value?.desc ?? '';
});
/** 作者模式:头部封面用朱砂方印 */
const isAuthor = computed(() => mode.value === 'author');
/** sub 模式:取第一首作品封面 */
const cover = computed(() => listSongs.value[0]?.cover);

/** 头部封面兜底色:作者用朱砂方印;子分类按所属大类映射(theme 为上方 ref) */
const coverVariant = computed<CoverVariant>(() => {
  if (mode.value === 'author') return 'seal';
  const map: Record<string, CoverVariant> = {
    children: 'candy',
    poetry: 'warm',
    classics: 'bamboo',
    story: 'moon',
  };
  return map[theme.value] ?? 'primary';
});

onLoad((options) => {
  const author = options?.author;
  const subOpt = options?.sub;
  const catOpt = options?.cat;
  if (typeof author === 'string' && author) {
    mode.value = 'author';
    authorName.value = author;
  } else if (typeof catOpt === 'string' && catOpt) {
    mode.value = 'cat';
    catId.value = catOpt;
  } else if (typeof subOpt === 'string' && subOpt) {
    mode.value = 'sub';
    subId.value = subOpt;
  }
});

/** 从指定位置播放当前列表 */
function playFrom(index: number) {
  if (songIds.value.length) player.playList(songIds.value, index);
}
/** 播放全部 */
function playAll() {
  if (songIds.value.length) player.playList(songIds.value, 0);
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
        <text class="count">{{ listSongs.length }} 首</text>
      </view>
    </view>

    <view class="play-all" @click="playAll">▶ 播放全部({{ listSongs.length }} 首)</view>

    <view class="song-list">
      <SongItem
        v-for="(song, i) in listSongs"
        :key="song.id"
        :song="song"
        :index="i"
        @play="playFrom(i)"
      />
    </view>

    <view v-if="listSongs.length === 0" class="empty">
      <text>该分类暂无音频</text>
    </view>
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
.page--children .empty {
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
.page--poetry .empty {
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
.page--classics .empty {
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
.page--story .empty {
  color: $story-text-sub;
}
</style>
