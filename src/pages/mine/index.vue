<script setup lang="ts">
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
 * 我的页:渐变账号头部 + 最近播放 + 我喜欢的(可取消收藏/播放全部)+ 设置组。
 * 最近播放来自 history store(按账号隔离、云端同步),此前无页面完整展示。
 */
const library = useLibraryStore();
const history = useHistoryStore();
const player = usePlayerStore();
const { likedIds, likedSongs } = storeToRefs(library);
const { recent } = storeToRefs(history);
// 当前登录账号(登录后必有)
const member = currentMember;

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
function showAbout() {
  const v = getAppVersion();
  uni.showModal({
    title: '启蒙音频',
    content: v ? `当前版本:v${v}` : '当前为开发版本',
    showCancel: false,
    confirmText: '知道了',
  });
}
</script>

<template>
  <view class="page">
    <!-- 渐变账号头部:头像/昵称/账号/数据统计,点击进账号管理 -->
    <view class="hero" @click="goAccount">
      <view class="avatar-wrap">
        <text class="avatar">{{ member?.avatar || '⭐' }}</text>
      </view>
      <view class="hero-info">
        <text class="name">{{ member?.name || '未登录' }}</text>
        <text class="account">账号:{{ member?.username || '未设置' }}</text>
        <view class="stats">
          <text class="stat">♥ 收藏 {{ likedSongs.length }} 首</text>
          <text class="stat-dot">·</text>
          <text class="stat">最近播放 {{ recent.length }} 首</text>
        </view>
      </view>
      <text class="hero-arrow">›</text>
    </view>

    <!-- 最近播放(无历史时整块隐藏) -->
    <view v-if="recent.length" class="section">
      <view class="section-head">
        <text class="section-title">最近播放</text>
        <text class="head-action" @click="confirmClearHistory">清空</text>
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
        <text class="section-title">我喜欢的<text class="count">{{ likedSongs.length }} 首</text></text>
        <text v-if="likedSongs.length" class="head-action" @click="playAllLiked">▶ 播放全部</text>
      </view>
      <view v-if="likedSongs.length" class="song-list">
        <SongItem
          v-for="song in likedSongs"
          :key="song.id"
          :song="song"
          @play="playLiked(song)"
        >
          <template #extra>
            <text class="like-btn" @click.stop="library.toggleLike(song.id)">♥</text>
          </template>
        </SongItem>
      </view>
      <view v-else class="empty">
        <text>还没有收藏的歌曲</text>
        <text class="empty-sub">播放页点击 ♥ 即可收藏</text>
      </view>
    </view>

    <!-- 设置组 -->
    <view class="settings">
      <view class="cell" @click="goAccount">
        <text class="cell-icon">👤</text>
        <text class="cell-label">账号管理</text>
        <text class="cell-sub">昵称 / 头像 / 密码</text>
        <text class="cell-arrow">›</text>
      </view>
      <view class="cell" @click="checkAppUpdateManual">
        <text class="cell-icon">🔄</text>
        <text class="cell-label">检查更新</text>
        <text class="cell-arrow">›</text>
      </view>
      <view class="cell" @click="showAbout">
        <text class="cell-icon">ℹ️</text>
        <text class="cell-label">关于</text>
        <text class="cell-arrow">›</text>
      </view>
    </view>

    <view class="bottom-pad" />
    <MiniPlayer />
  </view>
</template>

<style scoped lang="scss">
.page {
  min-height: 100vh;
}
/* ===== 渐变账号头部(与首页 banner 同风格) ===== */
.hero {
  margin: 24rpx 16rpx 0;
  padding: 36rpx 32rpx;
  background: linear-gradient(135deg, $primary-light, $primary);
  border-radius: 24rpx;
  box-shadow: $shadow-card;
  display: flex;
  align-items: center;

  &:active {
    opacity: 0.92;
  }
}
.avatar-wrap {
  width: 104rpx;
  height: 104rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.avatar {
  font-size: 56rpx;
}
.hero-info {
  flex: 1;
  min-width: 0;
  margin-left: 24rpx;
  display: flex;
  flex-direction: column;
}
.name {
  font-size: 34rpx;
  font-weight: bold;
  color: #ffffff;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.account {
  margin-top: 6rpx;
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.78);
}
.stats {
  margin-top: 12rpx;
  display: flex;
  align-items: center;
}
.stat {
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.92);
}
.stat-dot {
  margin: 0 12rpx;
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.6);
}
.hero-arrow {
  margin-left: 12rpx;
  font-size: 40rpx;
  color: rgba(255, 255, 255, 0.85);
}
/* ===== 内容区块(标题行样式参照首页) ===== */
.section {
  margin-top: 36rpx;
}
.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 0 24rpx;
  margin-bottom: 20rpx;
}
.section-title {
  font-size: 32rpx;
  font-weight: bold;
  color: $text-main;
}
.count {
  margin-left: 12rpx;
  font-size: 24rpx;
  font-weight: normal;
  color: $text-sub;
}
.head-action {
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
.like-btn {
  padding: 8rpx;
  font-size: 36rpx;
  color: $primary;
}
.empty {
  padding: 80rpx 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  color: $text-sub;
  font-size: 26rpx;
}
.empty-sub {
  margin-top: 16rpx;
  font-size: 24rpx;
  color: $text-disable;
}
/* ===== 设置组 ===== */
.settings {
  margin: 36rpx 16rpx 0;
  background: $bg-card;
  border-radius: 24rpx;
  overflow: hidden;
  box-shadow: $shadow-card;
}
.cell {
  display: flex;
  align-items: center;
  padding: 28rpx 24rpx;

  &:active {
    background: $uni-bg-color-hover;
  }
  & + .cell {
    border-top: 1rpx solid $divider;
  }
}
.cell-icon {
  width: 48rpx;
  font-size: 32rpx;
  text-align: center;
  flex-shrink: 0;
}
.cell-label {
  margin-left: 16rpx;
  font-size: 28rpx;
  color: $text-main;
}
.cell-sub {
  margin-left: auto;
  margin-right: 8rpx;
  font-size: 22rpx;
  color: $text-disable;
}
.cell-arrow {
  font-size: 32rpx;
  color: $text-sub;
}
.bottom-pad {
  height: 160rpx;
}
</style>
