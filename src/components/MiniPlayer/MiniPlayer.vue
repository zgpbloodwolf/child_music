<script setup lang="ts">
import { usePlayerStore } from '@/store/player';
import CoverImage from '@/components/CoverImage/CoverImage.vue';

/**
 * 底部迷你播放条:仅当有歌曲装载时显示。
 * 点击整体跳转播放页;播放/下一首按钮单独 stop 冒泡。
 */
const player = usePlayerStore();

function goPlayer() {
  uni.navigateTo({ url: '/pages/player/index' });
}
</script>

<template>
  <view v-if="player.hasCurrent" class="mini-player" @click="goPlayer">
    <view class="cover-wrap">
      <CoverImage :src="player.currentSong?.cover" :name="player.currentSong?.name" />
    </view>
    <view class="info">
      <text class="name">{{ player.currentSong?.name }}</text>
      <text class="sub">{{ player.currentSong?.artist }}</text>
    </view>
    <view class="ctrl">
      <view class="btn" @click.stop="player.togglePlay()">
        {{ player.isPlaying ? '❚❚ 暂停' : '▶ 播放' }}
      </view>
      <view class="btn" @click.stop="player.playNext()">⏭</view>
    </view>
  </view>
</template>

<style scoped lang="scss">
.mini-player {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 100rpx; /* 避让 tabBar 高度 */
  display: flex;
  align-items: center;
  margin: 0 16rpx;
  padding: 12rpx 20rpx;
  background: $bg-card;
  border-radius: 16rpx;
  box-shadow: $shadow-card;
  z-index: 100;
}
.cover-wrap {
  width: 72rpx;
  height: 72rpx;
  flex-shrink: 0;
}
.info {
  flex: 1;
  min-width: 0;
  margin-left: 16rpx;
}
.name {
  display: block;
  font-size: 28rpx;
  color: $text-main;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sub {
  display: block;
  margin-top: 4rpx;
  font-size: 22rpx;
  color: $text-sub;
}
.ctrl {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.btn {
  margin-left: 16rpx;
  padding: 10rpx 20rpx;
  font-size: 24rpx;
  color: $primary;
  border: 1rpx solid $primary;
  border-radius: 999rpx;
}
</style>
