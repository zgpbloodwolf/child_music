<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { getRepository } from '@/repository';
import { usePlayerStore } from '@/store/player';
import { useHistoryStore } from '@/store/history';
import SongItem from '@/components/SongItem/SongItem.vue';
import MiniPlayer from '@/components/MiniPlayer/MiniPlayer.vue';
import CoverImage from '@/components/CoverImage/CoverImage.vue';
import CategoryPanel from '@/components/CategoryPanel/CategoryPanel.vue';
import type { SongMeta } from '@/types/song';

/**
 * 首页(按原型交互):顶栏 + 分类 tab(本页切换内容) + 内容区 + 迷你播放条。
 * - 「全部」:banner + 最近播放 + 全部音频
 * - 某大类:交给 CategoryPanel 组件渲染(代码功能拆分)
 */
const player = usePlayerStore();
const history = useHistoryStore();
const { recent } = storeToRefs(history);
const repo = getRepository();

/** 分类 tab:全部 + 四大类(异步加载),点击本页切换内容(不跳转) */
const tabs = ref<Array<{ id: string; name: string }>>([{ id: 'all', name: '全部' }]);
const currentTab = ref('all');

/** 全部音频(异步加载) */
const allSongs = ref<SongMeta[]>([]);
/** 全部音频 id 列表(作为点击播放时的默认队列) */
const allIds = computed(() => allSongs.value.map((s) => s.id));
const loadingAll = ref(false);

onMounted(async () => {
  loadingAll.value = true;
  const [cats, all] = await Promise.all([repo.getCategories(), repo.listAll()]);
  tabs.value = [{ id: 'all', name: '全部' }, ...cats.map((c) => ({ id: c.id, name: c.name }))];
  allSongs.value = all;
  loadingAll.value = false;
});

/** 点击歌曲:以全部音频为队列播放 */
function play(song: SongMeta) {
  player.playSong(song.id, allIds.value);
}

/** 全部播放:以全部音频为队列,从第一首开始 */
function playAll() {
  if (allIds.value.length) player.playList(allIds.value, 0);
}

/** 跳转搜索页 */
function goSearch() {
  uni.navigateTo({ url: '/pages/search/index' });
}
</script>

<template>
  <view class="page">
    <!-- 顶栏:应用名 + 搜索图标 -->
    <view class="topbar">
      <text class="app-name">启蒙音频</text>
      <text class="search-ico" @click="goSearch">🔍</text>
    </view>

    <!-- 分类 tab:本页切换内容(按原型) -->
    <scroll-view scroll-x class="tabs" :show-scrollbar="false">
      <view
        v-for="t in tabs"
        :key="t.id"
        class="tab-item"
        :class="{ active: t.id === currentTab }"
        @click="currentTab = t.id"
      >{{ t.name }}</view>
    </scroll-view>

    <!-- 内容区:全部 -->
    <view v-if="currentTab === 'all'">
      <!-- Banner 精选推荐 -->
      <view class="banner">
        <view class="banner-text">
          今日推荐
          <text class="banner-sub">经典儿歌合集 · 适合 0-6 岁</text>
        </view>
      </view>

      <!-- 最近播放(来自 history store) -->
      <view v-if="recent.length" class="section">
        <text class="section-title">最近播放</text>
        <scroll-view scroll-x class="h-scroll" :show-scrollbar="false">
          <view
            v-for="s in recent"
            :key="s.id"
            class="recent-card"
            @click="play(s)"
          >
            <view class="recent-cover">
              <CoverImage :src="s.cover" :name="s.name" />
            </view>
            <text class="recent-name">{{ s.name }}</text>
          </view>
        </scroll-view>
      </view>

      <!-- 全部音频(无序号,按原型) -->
      <view class="section">
        <view class="all-head">
          <text class="section-title">全部音频</text>
          <text class="play-all" @click="playAll">▶ 播放全部({{ allSongs.length }} 首)</text>
        </view>
        <view class="song-list">
          <SongItem
            v-for="song in allSongs"
            :key="song.id"
            :song="song"
            @play="play(song)"
          />
        </view>
      </view>
    </view>

    <!-- 内容区:某大类(由 CategoryPanel 渲染,:key 切换时重建以重置内部状态) -->
    <CategoryPanel v-else :cat-id="currentTab" :key="currentTab" />

    <view class="bottom-pad" />
    <MiniPlayer />
  </view>
</template>

<style scoped lang="scss">
.page {
  min-height: 100vh;
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16rpx 24rpx 8rpx;
}
.app-name {
  font-size: 40rpx;
  font-weight: bold;
  color: $text-main;
}
.search-ico {
  font-size: 40rpx;
  color: $text-main;
}
.tabs {
  white-space: nowrap;
  padding: 8rpx 24rpx 16rpx;
}
.tab-item {
  display: inline-block;
  margin-right: 44rpx;
  font-size: 30rpx;
  color: $text-sub;
  position: relative;
  padding: 4rpx 0;
}
.tab-item.active {
  color: $text-main;
  font-weight: bold;
  font-size: 32rpx;
}
.tab-item.active::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: -6rpx;
  transform: translateX(-50%);
  width: 40rpx;
  height: 6rpx;
  background: $primary;
  border-radius: 4rpx;
}
.banner {
  margin: 8rpx 24rpx 0;
  height: 264rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, $primary-light, $primary);
  display: flex;
  align-items: center;
  padding: 0 44rpx;
  box-shadow: $shadow-card;
}
.banner-text {
  color: #ffffff;
  font-size: 40rpx;
  font-weight: bold;
  line-height: 1.4;
}
.banner-sub {
  display: block;
  margin-top: 12rpx;
  font-size: 24rpx;
  font-weight: normal;
  opacity: 0.92;
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
/* 「全部音频」标题行:标题在左、播放全部在右(裸 .section-title 不受影响) */
.all-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 0 24rpx;
  margin-bottom: 20rpx;
}
.all-head .section-title {
  padding: 0;
  margin: 0;
}
.play-all {
  font-size: 26rpx;
  color: $primary;
}
.h-scroll {
  white-space: nowrap;
  padding: 0 16rpx;
}
.recent-card {
  display: inline-block;
  width: 140rpx;
  margin: 0 8rpx;
  vertical-align: top;
}
.recent-cover {
  width: 140rpx;
  height: 140rpx;
}
.recent-name {
  display: block;
  margin-top: 12rpx;
  font-size: 24rpx;
  color: $text-main;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.song-list {
  margin: 0 16rpx;
  background: $bg-card;
  border-radius: 24rpx;
  overflow: hidden;
}
.bottom-pad {
  height: 160rpx;
}
</style>
