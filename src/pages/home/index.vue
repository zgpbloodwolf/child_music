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
 * - 「全部」:banner + 最近播放 + 推荐歌曲(按分类懒加载)
 * - 某大类:交给 CategoryPanel 组件渲染(代码功能拆分)
 *
 * 优化:启动时只加载分类树,不一次性加载全部歌曲,避免网络慢时超时。
 */
const player = usePlayerStore();
const history = useHistoryStore();
const { recent } = storeToRefs(history);
const repo = getRepository();

/** 分类 tab:全部 + 四大类(异步加载),点击本页切换内容(不跳转) */
const tabs = ref<Array<{ id: string; name: string }>>([{ id: 'all', name: '全部' }]);
const currentTab = ref('all');

/** 推荐歌曲(按分类懒加载,首页只展示前几首) */
const recommendSongs = ref<SongMeta[]>([]);
const loadingRecommend = ref(false);

onMounted(async () => {
  // 只加载分类树,不加载全部歌曲
  const cats = await repo.getCategories();
  tabs.value = [{ id: 'all', name: '全部' }, ...cats.map((c) => ({ id: c.id, name: c.name }))];
  // 加载第一个分类的歌曲作为推荐
  if (cats.length > 0) {
    loadRecommend(cats[0].id);
  }
});

/** 懒加载推荐歌曲(只加载当前分类前6首) */
async function loadRecommend(catId: string) {
  loadingRecommend.value = true;
  try {
    const songs = await repo.listByCategory(catId);
    recommendSongs.value = songs.slice(0, 6);
  } catch (err) {
    console.warn('加载推荐歌曲失败:', err);
  } finally {
    loadingRecommend.value = false;
  }
}

/** 点击歌曲:以推荐歌曲为队列播放 */
function play(song: SongMeta) {
  const ids = recommendSongs.value.map((s) => s.id);
  player.playSong(song.id, ids);
}

/** 跳转到全部音频歌单页(展示完整列表) */
function goAllSongs() {
  uni.navigateTo({ url: '/pages/playlist/index?all=1' });
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

      <!-- 推荐歌曲(首页仅展示前6首,点击「全部歌曲」跳转歌单页看全部) -->
      <view class="section">
        <view class="all-head">
          <text class="section-title">推荐歌曲</text>
          <text class="play-all" @click="goAllSongs">全部歌曲</text>
        </view>
        <view v-if="loadingRecommend" class="loading">
          <text>加载中...</text>
        </view>
        <view v-else class="song-list">
          <SongItem
            v-for="song in recommendSongs"
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
.loading {
  text-align: center;
  padding: 40rpx;
  color: $text-sub;
}
.bottom-pad {
  height: 160rpx;
}
</style>
