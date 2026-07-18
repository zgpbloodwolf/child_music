<script setup lang="ts">
import { usePlayerStore } from '@/store/player';
import { isTabBarPage } from '@/utils/page';
import CoverImage from '@/components/CoverImage/CoverImage.vue';

/**
 * 底部迷你播放条:仅当有歌曲装载时显示。
 * 点击整体跳转播放页;上一首/播放/下一首按钮单独 stop 冒泡。
 * bottom 按当前页类型动态偏移:tabBar 页避让 tabBar,普通页贴底 + 安全区呼吸边距。
 */
const player = usePlayerStore();

/**
 * 一次性求值(组件实例与页面绑定,同页内路由不变,无需响应式):
 * tabBar 页避让 tabBar(100rpx,三端已验证);普通页贴底,16rpx 与左右 margin 一致。
 */
const bottomOffset = isTabBarPage() ? '100rpx' : 'calc(16rpx + env(safe-area-inset-bottom))';

function goPlayer() {
  uni.navigateTo({ url: '/pages/player/index' });
}
</script>

<template>
  <view v-if="player.hasCurrent" class="mini-player" :style="{ bottom: bottomOffset }" @click="goPlayer">
    <view class="cover-wrap">
      <CoverImage :src="player.currentSong?.cover" :name="player.currentSong?.name" />
    </view>
    <view class="info">
      <text class="name">{{ player.currentSong?.name }}</text>
      <text class="sub">{{ player.currentSong?.artist }}</text>
    </view>
    <view class="ctrl">
      <view class="btn" @click.stop="player.playPrev()">⏮</view>
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
