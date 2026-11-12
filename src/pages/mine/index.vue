<script setup lang="ts">
import { ref, computed } from 'vue';
import { onReachBottom } from '@dcloudio/uni-app';
import { storeToRefs } from 'pinia';
import { useLibraryStore } from '@/store/library';
import { useHistoryStore } from '@/store/history';
import { usePlayerStore } from '@/store/player';
import { currentMember } from '@/store/memberPrefs';
import SongItem from '@/components/SongItem/SongItem.vue';
import MiniPlayer from '@/components/MiniPlayer/MiniPlayer.vue';
import CoverImage from '@/components/CoverImage/CoverImage.vue';
import { checkAppUpdateManual } from '@/utils/appUpdate';
import type { SongMeta } from '@/types/song';

/**
 * 我的页:沉浸式渐变头部(custom 导航)+ 悬浮统计卡 + 最近播放 + 我喜欢的 + 设置组。
 * 最近播放来自 history store(按账号隔离、云端同步),此前无页面完整展示。
 */
const library = useLibraryStore();
const history = useHistoryStore();
const player = usePlayerStore();
const { likedIds, likedSongs } = storeToRefs(library);
const { recent } = storeToRefs(history);

// ===== 「我喜欢的」分批渲染:收藏量大(数百首)时一次挂载全部会卡,触底续展 =====
/** 每批渲染条数(与歌单页 PAGE_SIZE 一致) */
const LIKED_STEP = 30;
/** 当前已渲染条数(likedSongs 的前缀切片) */
const likedShown = ref(LIKED_STEP);
/** 实际渲染的收藏切片 */
const shownLikedSongs = computed(() => likedSongs.value.slice(0, likedShown.value));

onReachBottom(() => {
  if (likedShown.value < likedSongs.value.length) {
    likedShown.value = Math.min(likedShown.value + LIKED_STEP, likedSongs.value.length);
  }
});
// 当前登录账号(登录后必有)
const member = currentMember;

/** 状态栏高度:本页 custom 导航(渐变延伸到状态栏),需自行为状态栏留白 */
const statusBarHeight = uni.getWindowInfo().statusBarHeight || 20;

/** 点击最近播放:以最近播放列表为队列(与首页同口径,播完不串台) */
function playRecent(song: SongMeta) {
  player.playSong(song.id, recent.value.map((s) => s.id));
}

/** 点击收藏歌曲:以收藏列表为队列播放 */
function playLiked(song: SongMeta) {
  player.playSong(song.id, likedSongs.value.map((s) => s.id));
}

/** 播放全部收藏(从第一首开始) */
function playAllLiked() {
  if (!likedIds.value.length) return;
  player.playList(likedIds.value);
}

/** 清空播放历史(二次确认) */
function confirmClearHistory() {
  uni.showModal({
    title: '清空播放历史?',
    content: '清空后不可恢复',
    confirmColor: '#e64340',
    success: (res) => {
      if (res.confirm) {
        history.clear();
        uni.showToast({ title: '已清空', icon: 'none' });
      }
    },
  });
}

/** 前往账号管理页(资料/密码修改与退出登录) */
function goAccount() {
  uni.navigateTo({ url: '/pages/member/index' });
}

/** 当前 App 版本号(App 端取运行时 versionName;H5/小程序无版本概念,回退空) */
function getAppVersion(): string {
  // #ifdef APP-PLUS
  try {
    const info = uni.getSystemInfoSync() as { appVersion?: unknown };
    if (typeof info.appVersion === 'string' && info.appVersion) return info.appVersion;
  } catch { /* 取不到按无版本处理 */ }
  return '';
  // #endif
  // #ifndef APP-PLUS
  return '';
  // #endif
}

/** 关于弹窗:应用名 + 版本 */
/** 版本号只求值一次(关于弹窗与设置行副标题共用) */
const APP_VERSION = getAppVersion();

function showAbout() {
  uni.showModal({
    title: '启蒙音频',
    content: APP_VERSION ? `当前版本:v${APP_VERSION}` : '当前为开发版本',
    showCancel: false,
    confirmText: '知道了',
  });
}

/** 设置组条目(icon 为 emoji,统一放在主色浅底圆角容器里保持视觉一致) */
interface SettingItem {
  icon: string;
  label: string;
  sub?: string;
  run: () => void;
}
const settings: SettingItem[] = [
  { icon: '👤', label: '账号管理', sub: '昵称 · 头像 · 密码', run: goAccount },
  { icon: '🔄', label: '检查更新', sub: '检测新版本', run: checkAppUpdateManual },
  { icon: 'ℹ️', label: '关于启蒙音频', sub: APP_VERSION ? `v${APP_VERSION}` : '开发版', run: showAbout },
];
</script>

<template>
  <view class="page">
    <!-- 沉浸式渐变头部:标题 + 用户信息,点击进账号管理 -->
    <view class="hero" :style="{ paddingTop: statusBarHeight + 12 + 'px' }">
      <text class="nav-title">我的</text>
      <view class="user-row" @click="goAccount">
        <view class="avatar-ring">
          <text class="avatar">{{ member?.avatar || '⭐' }}</text>
        </view>
        <view class="user-info">
          <text class="name">{{ member?.name || '未登录' }}</text>
          <text class="account">{{ member?.username ? `账号 ${member.username}` : '未设置账号' }}</text>
        </view>
        <view class="chevron chevron-light" />
      </view>
    </view>

    <!-- 悬浮统计卡:压在渐变头部下缘 -->
    <view class="stats-card">
      <view class="stat">
        <text class="stat-num">{{ likedSongs.length }}</text>
        <text class="stat-label">收藏歌曲</text>
      </view>
      <view class="stat-sep" />
      <view class="stat">
        <text class="stat-num">{{ recent.length }}</text>
        <text class="stat-label">最近播放</text>
      </view>
    </view>

    <!-- 最近播放(无历史时整块隐藏) -->
    <view v-if="recent.length" class="section">
      <view class="section-head">
        <text class="section-title">最近播放</text>
        <text class="clear-btn" @click="confirmClearHistory">清空</text>
      </view>
      <scroll-view scroll-x class="h-scroll" :show-scrollbar="false">
        <view
          v-for="s in recent"
          :key="s.id"
          class="recent-card"
          @click="playRecent(s)"
        >
          <view class="recent-cover">
            <CoverImage :src="s.cover" :name="s.name" />
          </view>
          <text class="recent-name">{{ s.name }}</text>
        </view>
      </scroll-view>
    </view>

    <!-- 我喜欢的 -->
    <view class="section">
      <view class="section-head">
        <view class="title-wrap">
          <text class="section-title">我喜欢的</text>
          <text class="count">{{ likedSongs.length }} 首</text>
        </view>
        <view v-if="likedSongs.length" class="play-all" @click="playAllLiked">
          <view class="play-tri" />
          <text class="play-all-text">播放全部</text>
        </view>
      </view>
      <view v-if="likedSongs.length" class="song-list">
        <SongItem
          v-for="song in shownLikedSongs"
          :key="song.id"
          :song="song"
          @play="playLiked(song)"
        >
          <template #extra>
            <view class="like-hit" @click.stop="library.toggleLike(song.id)">
              <text class="like-icon">♥</text>
            </view>
          </template>
        </SongItem>
        <view v-if="likedShown < likedSongs.length" class="more-hint">
          <text>上拉显示更多(已显示 {{ likedShown }} / {{ likedSongs.length }} 首)</text>
        </view>
      </view>
      <view v-else class="empty">
        <view class="empty-icon">
          <text class="empty-heart">♥</text>
        </view>
        <text class="empty-title">还没有收藏的歌曲</text>
        <text class="empty-sub">播放页点击 ♥ 即可收藏</text>
      </view>
    </view>

    <!-- 设置组 -->
    <view class="settings">
      <view
        v-for="item in settings"
        :key="item.label"
        class="cell"
        @click="item.run"
      >
        <view class="cell-icon">
          <text class="cell-icon-text">{{ item.icon }}</text>
        </view>
        <text class="cell-label">{{ item.label }}</text>
        <text v-if="item.sub" class="cell-sub">{{ item.sub }}</text>
        <view class="chevron" />
      </view>
    </view>

    <view class="bottom-pad" />
    <MiniPlayer />
  </view>
</template>

<style scoped lang="scss">
/* ===== 沉浸式渐变头部 ===== */
.hero {
  background: linear-gradient(165deg, $primary-light, $primary);
  padding-bottom: 84rpx; /* 底部留白供统计卡叠压 */
}
.nav-title {
  display: block;
  padding: 12rpx 32rpx 8rpx;
  font-size: 34rpx;
  font-weight: bold;
  color: #ffffff;
}
.user-row {
  margin: 20rpx 32rpx 0;
  display: flex;
  align-items: center;

  &:active .avatar-ring,
  &:active .name,
  &:active .account {
    opacity: 0.85;
  }
}
.avatar-ring {
  width: 116rpx;
  height: 116rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.28);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.avatar {
  width: 100rpx;
  height: 100rpx;
  border-radius: 50%;
  background: #ffffff;
  font-size: 56rpx;
  text-align: center;
  line-height: 100rpx;
}
.user-info {
  flex: 1;
  min-width: 0;
  margin-left: 28rpx;
  display: flex;
  flex-direction: column;
}
.name {
  font-size: 36rpx;
  font-weight: bold;
  color: #ffffff;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.account {
  margin-top: 10rpx;
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.82);
}
/* ===== 悬浮统计卡 ===== */
.stats-card {
  margin: -56rpx 24rpx 0;
  padding: 32rpx 0;
  background: $bg-card;
  border-radius: 28rpx;
  box-shadow: $shadow-card;
  display: flex;
  align-items: center;
}
.stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.stat-num {
  font-size: 44rpx;
  font-weight: bold;
  color: $text-main;
  line-height: 1.1;
}
.stat-label {
  margin-top: 8rpx;
  font-size: 24rpx;
  color: $text-sub;
}
.stat-sep {
  width: 1rpx;
  height: 56rpx;
  background: $divider;
}
/* ===== 内容区块通用 ===== */
.section {
  margin-top: 48rpx;
}
.section-head {
  display: flex;
  align-items: center;
  padding: 0 32rpx 24rpx;
}
.title-wrap {
  display: flex;
  align-items: baseline;
}
.section-title {
  font-size: 34rpx;
  font-weight: bold;
  color: $text-main;
}
.count {
  margin-left: 14rpx;
  font-size: 24rpx;
  color: $text-sub;
}
.clear-btn {
  margin-left: auto;
  padding: 8rpx 16rpx;
  font-size: 24rpx;
  color: $text-sub;

  &:active {
    color: $danger;
  }
}
/* ===== 最近播放横滑 ===== */
.h-scroll {
  white-space: nowrap;
  padding: 0 32rpx;
}
.recent-card {
  display: inline-block;
  width: 152rpx;
  margin-right: 24rpx;
  vertical-align: top;

  &:active .recent-cover {
    opacity: 0.85;
  }
}
.recent-cover {
  width: 152rpx;
  height: 152rpx;
  border-radius: 20rpx;
  overflow: hidden;
  box-shadow: 0 6rpx 16rpx rgba(0, 0, 0, 0.08);
}
.recent-name {
  display: block;
  margin-top: 14rpx;
  font-size: 24rpx;
  color: $text-main;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* ===== 我喜欢的 ===== */
.play-all {
  margin-left: auto;
  display: flex;
  align-items: center;
  padding: 12rpx 28rpx;
  border: 2rpx solid $primary;
  border-radius: 999rpx;

  &:active {
    background: $primary-soft;
  }
}
.play-tri {
  width: 0;
  height: 0;
  border-top: 9rpx solid transparent;
  border-bottom: 9rpx solid transparent;
  border-left: 14rpx solid $primary;
  margin-right: 12rpx;
}
.play-all-text {
  font-size: 24rpx;
  color: $primary;
}
.song-list {
  margin: 0 24rpx;
  background: $bg-card;
  border-radius: 28rpx;
  overflow: hidden;
  box-shadow: $shadow-card;
}
.like-hit {
  width: 76rpx;
  height: 76rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;

  &:active .like-icon {
    transform: scale(0.8);
    opacity: 0.6;
  }
}
.like-icon {
  font-size: 34rpx;
  color: $primary;
  transition: transform 0.12s ease, opacity 0.12s ease;
}
.more-hint {
  padding: 20rpx 0;
  text-align: center;
  font-size: 22rpx;
  color: $text-disable;
}
.empty {
  padding: 100rpx 0 60rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.empty-icon {
  width: 120rpx;
  height: 120rpx;
  border-radius: 50%;
  background: $primary-soft;
  display: flex;
  align-items: center;
  justify-content: center;
}
.empty-heart {
  font-size: 52rpx;
  color: $primary-light;
}
.empty-title {
  margin-top: 28rpx;
  font-size: 28rpx;
  color: $text-main;
}
.empty-sub {
  margin-top: 12rpx;
  font-size: 24rpx;
  color: $text-disable;
}
/* ===== 设置组 ===== */
.settings {
  margin: 48rpx 24rpx 0;
  background: $bg-card;
  border-radius: 28rpx;
  overflow: hidden;
  box-shadow: $shadow-card;
}
.cell {
  display: flex;
  align-items: center;
  padding: 28rpx 28rpx;

  &:active {
    background: $uni-bg-color-hover;
  }
  & + .cell {
    border-top: 1rpx solid $divider;
  }
}
.cell-icon {
  width: 64rpx;
  height: 64rpx;
  border-radius: 18rpx;
  background: $primary-soft;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.cell-icon-text {
  font-size: 32rpx;
}
.cell-label {
  margin-left: 24rpx;
  font-size: 28rpx;
  color: $text-main;
}
.cell-sub {
  margin-left: auto;
  margin-right: 16rpx;
  font-size: 22rpx;
  color: $text-disable;
}
/* ===== 通用箭头(CSS 绘制,替代字符 ›) ===== */
.chevron {
  width: 16rpx;
  height: 16rpx;
  border-right: 3rpx solid $text-disable;
  border-bottom: 3rpx solid $text-disable;
  transform: rotate(-45deg);
  flex-shrink: 0;

  &.chevron-light {
    border-color: rgba(255, 255, 255, 0.85);
  }
}
.bottom-pad {
  height: 160rpx;
}
</style>
