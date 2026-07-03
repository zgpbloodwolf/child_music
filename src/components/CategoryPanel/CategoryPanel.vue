<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { listPoetryAuthors, poetryDynasties } from '@/data/poetry';
import type { Category } from '@/types/category';
import { getRepository } from '@/repository';
import { usePlayerStore } from '@/store/player';
import { PoetryViewMode } from '@/types/poetry';
import type { PoetryAuthor } from '@/types/poetry';
import type { SongMeta } from '@/types/song';
import PoetryHero from '@/components/PoetryHero/PoetryHero.vue';
import ChildrenHero from '@/components/ChildrenHero/ChildrenHero.vue';
import ClassicsHero from '@/components/ClassicsHero/ClassicsHero.vue';
import StoryHero from '@/components/StoryHero/StoryHero.vue';
import SegmentedTabs from '@/components/SegmentedTabs/SegmentedTabs.vue';
import CoverImage from '@/components/CoverImage/CoverImage.vue';
import type { CoverVariant } from '@/components/CoverImage/CoverImage.vue';

/**
 * 大类内容面板:首页分类 tab 切换时在首页内渲染某大类(也可被独立分类页复用)。
 * - children / classics / story:各自独立皮肤 + 专属 Hero(糖果 / 竹简 / 梦幻)
 * - poetry:书卷质感 + 「类型/作者」分段切换 + 双面板(布局一致)
 * 皮肤 class 一律用字面量对象(非字符串拼接),避免 scoped + 小程序端丢哈希失效。
 *
 * 各子类的歌曲列表 / 数量走 Repository 异步加载(分类结构静态、歌曲数据不进 bundle)。
 */
const props = defineProps<{ catId: string }>();
const player = usePlayerStore();
const repo = getRepository();

/** 古诗内容视图(仅 poetry 生效);catId 变化时由父级 :key 重建自动重置 */
const viewMode = ref<PoetryViewMode>(PoetryViewMode.BY_TYPE);

const cat = ref<Category | null>(null);
const isPoetry = computed(() => props.catId === 'poetry');

/** 各子类歌曲列表(subId → 列表),异步加载 */
const subList = ref<Record<string, SongMeta[]>>({});
/** 该大类歌曲总数 */
const totalCount = ref(0);
/** poetry 作者列表(异步) */
const authors = ref<PoetryAuthor[]>([]);
/** poetry 朝代标签(异步) */
const dynasties = ref<string[]>([]);

/** 加载某大类的各子类歌曲列表 + 总数;poetry 额外加载作者 / 朝代 */
async function loadCat(catId: string): Promise<void> {
  const cats = await repo.getCategories();
  const c = cats.find((x) => x.id === catId) ?? null;
  cat.value = c;
  if (!c) return;
  const lists = await Promise.all(c.subs.map((s) => repo.listBySub(s.id)));
  const map: Record<string, SongMeta[]> = {};
  let total = 0;
  c.subs.forEach((s, i) => {
    map[s.id] = lists[i];
    total += lists[i].length;
  });
  subList.value = map;
  totalCount.value = total;
  if (catId === 'poetry') {
    authors.value = await listPoetryAuthors();
    dynasties.value = await poetryDynasties();
  }
}

watch(() => props.catId, (id) => { void loadCat(id); }, { immediate: true });

const poetryTabs = [
  { value: PoetryViewMode.BY_TYPE, label: '按朝代 · 类型' },
  { value: PoetryViewMode.BY_AUTHOR, label: '按作者' },
];

/** 主题(=catId):驱动皮肤 class 与封面 variant */
const theme = computed(() => props.catId);
/** 子卡封面兜底色:按主题映射(儿歌糖果 / 三字经竹简 / 故事月光 / 古诗暖褐 / 其余默认) */
const coverVariant = computed<CoverVariant>(() => {
  const map: Record<string, CoverVariant> = {
    children: 'candy',
    poetry: 'warm',
    classics: 'bamboo',
    story: 'moon',
  };
  return map[props.catId] ?? 'primary';
});

/** 某子类的歌曲数(template 用) */
function subCount(subId: string): number {
  return subList.value[subId]?.length ?? 0;
}

/** 点子分类 → 歌单详情 */
function goSub(subId: string) {
  uni.navigateTo({ url: `/pages/playlist/index?sub=${subId}` });
}
/** 点作者 → 该作者的古诗作品(复用歌单详情页 ?author=) */
function goAuthor(author: string) {
  uni.navigateTo({ url: `/pages/playlist/index?author=${encodeURIComponent(author)}` });
}
/** 全部播放:以该大类所有音频为队列 */
function playAll() {
  const allIds = Object.values(subList.value).flat().map((s) => s.id);
  if (allIds.length) player.playList(allIds, 0);
}
</script>

<template>
  <view
    v-if="cat"
    class="panel"
    :class="{
      'panel--children': theme === 'children',
      'panel--poetry': theme === 'poetry',
      'panel--classics': theme === 'classics',
      'panel--story': theme === 'story',
    }"
  >
    <!-- ===== 头部:各大类专属 ===== -->
    <ChildrenHero v-if="theme === 'children'" :name="cat.name" :desc="cat.desc" />
    <ClassicsHero v-else-if="theme === 'classics'" :name="cat.name" :desc="cat.desc" />
    <StoryHero v-else-if="theme === 'story'" :name="cat.name" :desc="cat.desc" />
    <PoetryHero
      v-else-if="theme === 'poetry'"
      title="古诗"
      subtitle="唐诗宋词 · 启蒙经典"
      :dynasties="dynasties"
      seal-text="诗"
    />
    <view v-else class="cat-hero">
      <view class="cat-hero-icon">{{ cat.icon }}</view>
      <view class="cat-hero-info">
        <text class="cat-hero-name">{{ cat.name }}</text>
        <text class="cat-hero-desc">{{ cat.desc }}</text>
      </view>
    </view>

    <!-- 播放全部(各主题用 modifier 控制配色) -->
    <view
      class="play-all"
      :class="{
        'play-all--candy': theme === 'children',
        'play-all--ink': theme === 'poetry',
        'play-all--bamboo': theme === 'classics',
        'play-all--moon': theme === 'story',
      }"
      @click="playAll"
    >▶ 全部播放({{ totalCount }} 首)</view>

    <!-- ===== 古诗:类型/作者双面板 ===== -->
    <template v-if="isPoetry">
      <SegmentedTabs v-model="viewMode" :items="poetryTabs" tone="poetry" />

      <!-- 类型面板 -->
      <view v-if="viewMode === PoetryViewMode.BY_TYPE" class="sub-grid">
        <view
          v-for="sub in cat.subs"
          :key="sub.id"
          class="sub-card sub-card--paper"
          @click="goSub(sub.id)"
        >
          <view class="sub-cover">
            <CoverImage variant="warm" :placeholder="sub.icon || sub.name.charAt(0)" />
          </view>
          <text class="sub-name sub-name--ink">{{ sub.name }}</text>
          <text class="sub-count sub-count--ink">{{ subCount(sub.id) }} 首</text>
        </view>
      </view>

      <!-- 作者面板(与类型面板同布局) -->
      <view v-else class="sub-grid">
        <view
          v-for="a in authors"
          :key="a.name"
          class="sub-card sub-card--paper"
          @click="goAuthor(a.name)"
        >
          <view class="sub-cover">
            <CoverImage variant="seal" :placeholder="a.name.charAt(0)" />
          </view>
          <text class="sub-name sub-name--ink">{{ a.name }}</text>
          <text class="sub-count sub-count--ink">{{ a.count }} 首</text>
        </view>
      </view>
    </template>

    <!-- ===== 其他大类:按类型浏览(单视图) ===== -->
    <view v-else class="section">
      <text class="section-title">按类型浏览</text>
      <view class="sub-grid">
        <view
          v-for="sub in cat.subs"
          :key="sub.id"
          class="sub-card"
          @click="goSub(sub.id)"
        >
          <view class="sub-cover">
            <CoverImage :variant="coverVariant" :placeholder="sub.icon || sub.name.charAt(0)" />
          </view>
          <text class="sub-name">{{ sub.name }}</text>
          <text class="sub-count">{{ subCount(sub.id) }} 首</text>
        </view>
      </view>
    </view>
  </view>
</template>

<style scoped lang="scss">
.panel {
  padding-bottom: 16rpx;
}
.cat-hero {
  display: flex;
  align-items: center;
  padding: 32rpx 24rpx 24rpx;
}
.cat-hero-icon {
  width: 140rpx;
  height: 140rpx;
  border-radius: 28rpx;
  background: linear-gradient(135deg, $primary-light, $primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 64rpx;
  box-shadow: $shadow-card;
}
.cat-hero-info {
  margin-left: 28rpx;
  flex: 1;
  display: flex;
  flex-direction: column;
}
.cat-hero-name {
  font-size: 44rpx;
  font-weight: bold;
  color: $text-main;
}
.cat-hero-desc {
  margin-top: 12rpx;
  font-size: 26rpx;
  color: $text-sub;
}
.play-all {
  margin: 8rpx 24rpx 0;
  padding: 24rpx 0;
  text-align: center;
  color: #ffffff;
  font-size: 28rpx;
  background: $primary;
  border-radius: 999rpx;
}
.section {
  margin-top: 36rpx;
}
.section-title {
  display: block;
  padding: 0 24rpx;
  margin-bottom: 20rpx;
  font-size: 32rpx;
  font-weight: bold;
  color: $text-main;
}
.sub-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24rpx;
  padding: 0 24rpx;
}
.sub-card {
  background: $bg-card;
  border-radius: 24rpx;
  padding: 24rpx;
  box-shadow: $shadow-card;
}
/* 封面容器:纯尺寸,渐变/圆角由 CoverImage 按 variant 自管 */
.sub-cover {
  width: 100%;
  height: 180rpx;
}
.sub-name {
  display: block;
  margin-top: 16rpx;
  font-size: 28rpx;
  font-weight: 600;
  color: $text-main;
}
.sub-count {
  display: block;
  margin-top: 6rpx;
  font-size: 22rpx;
  color: $text-sub;
}

/* ===== 古诗·书卷皮肤(仅 .panel--poetry) ===== */
.panel--poetry {
  background: linear-gradient(180deg, $poetry-paper, $poetry-paper-deep);
  font-family: 'KaiTi', 'STKaiti', '楷体', serif;
}
.panel--poetry .sub-cover {
  background: transparent;
  border-radius: 12rpx;
}
.play-all--ink {
  background: $poetry-ink;
  color: $poetry-paper;
}
.sub-card--paper {
  background: $poetry-card;
  border: 2rpx solid $poetry-paper-deep;
  box-shadow: $poetry-shadow;
}
.sub-name--ink {
  color: $poetry-ink;
}
.sub-count--ink {
  color: $poetry-ink-sub;
}

/* ===== 儿歌·糖果皮肤(仅 .panel--children) ===== */
.panel--children {
  background: linear-gradient(180deg, $children-bg-start, $children-bg-end);
}
.panel--children .sub-card {
  background: $children-card;
  border: 2rpx solid $children-card-border;
  border-radius: 32rpx;
  box-shadow: $children-shadow;
}
.panel--children .sub-name {
  color: $children-text;
  font-weight: bold;
}
.panel--children .sub-count {
  color: $children-text-sub;
}
.panel--children .section-title {
  position: relative;
  padding-left: 36rpx;
  color: $children-text;
}
.panel--children .section-title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 24rpx;
  height: 24rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, $children-rainbow-1, $children-rainbow-3 60%, $children-rainbow-4);
}
.play-all--candy {
  background: linear-gradient(135deg, $children-play-start, $children-play-end);
  box-shadow: 0 8rpx 20rpx rgba($children-accent, 0.35);
  font-weight: bold;
}

/* ===== 三字经·竹简皮肤(仅 .panel--classics) ===== */
.panel--classics {
  background:
    repeating-linear-gradient(90deg, rgba($classics-accent, 0.05) 0 4rpx, transparent 4rpx 32rpx),
    linear-gradient(180deg, $classics-bg-start, $classics-bg-end);
  font-family: 'KaiTi', 'STKaiti', '楷体', serif;
}
.panel--classics .sub-card {
  background: $classics-card;
  border: 2rpx solid $classics-card-border;
  border-radius: 12rpx;
  box-shadow: $classics-shadow;
}
.panel--classics .sub-name {
  color: $classics-text;
  letter-spacing: 2rpx;
}
.panel--classics .sub-count {
  color: $classics-text-sub;
}
.panel--classics .section-title {
  position: relative;
  padding-left: 28rpx;
  color: $classics-text;
}
.panel--classics .section-title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 8rpx;
  height: 32rpx;
  background: $classics-accent;
  border-radius: 4rpx;
}
.play-all--bamboo {
  background: $classics-accent;
  color: $classics-bg-start;
}

/* ===== 故事·梦幻皮肤(仅 .panel--story,浅色版) ===== */
.panel--story {
  background:
    radial-gradient(circle at 86% 8%, rgba($story-moon, 0.18), transparent 30%),
    linear-gradient(180deg, $story-bg-start, $story-bg-end);
}
.panel--story .sub-card {
  background: $story-card;
  border: 2rpx solid $story-card-border;
  border-radius: 28rpx;
  box-shadow: $story-shadow;
}
.panel--story .sub-name {
  color: $story-text;
}
.panel--story .sub-count {
  color: $story-text-sub;
}
.panel--story .section-title {
  position: relative;
  padding-left: 36rpx;
  color: $story-text;
}
.panel--story .section-title::before {
  content: '✦';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  color: $story-accent;
  font-size: 28rpx;
}
.play-all--moon {
  background: linear-gradient(135deg, $story-play-start, $story-play-end);
  box-shadow: 0 8rpx 20rpx rgba($story-accent, 0.3);
  font-weight: bold;
}
</style>
