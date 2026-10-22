<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { useLibraryStore } from '@/store/library';
import { usePlayerStore } from '@/store/player';
import { currentMember } from '@/store/memberPrefs';
import SongItem from '@/components/SongItem/SongItem.vue';
import MiniPlayer from '@/components/MiniPlayer/MiniPlayer.vue';
import type { SongMeta } from '@/types/song';
import { checkAppUpdateManual } from '@/utils/appUpdate';

/** 我的页:展示「我喜欢的音乐」(按登录账号隔离;云端同步) */
const library = useLibraryStore();
const player = usePlayerStore();
const { likedSongs } = storeToRefs(library);
// 当前登录账号(登录后必有)
const member = currentMember;

/** 点击歌曲:以收藏列表为队列播放 */
function play(song: SongMeta) {
  player.playSong(song.id, likedSongs.value.map((s) => s.id));
}

/** 前往账号页(当前登录账号信息与退出登录) */
function goMember() {
  uni.navigateTo({ url: '/pages/member/index' });
}
</script>

<template>
  <view class="page">
    <view class="member-entry" @click="goMember">
      <text class="member-avatar">{{ member?.avatar || '👤' }}</text>
      <view class="member-text">
        <text class="member-name">{{ member?.name || '未登录' }}</text>
        <text v-if="member?.username" class="member-account">账号:{{ member.username }}</text>
      </view>
      <text class="member-sub">账号信息</text>
      <text class="update-arrow">›</text>
    </view>

    <view class="header">
      <text class="title">我喜欢的</text>
      <text class="count">{{ likedSongs.length }} 首</text>
    </view>

    <view v-if="likedSongs.length" class="song-list">
      <SongItem
        v-for="song in likedSongs"
        :key="song.id"
        :song="song"
        @play="play(song)"
      />
    </view>

    <view v-else class="empty">
      <text>还没有收藏的歌曲</text>
      <text class="empty-sub">播放页点击 ♥ 即可收藏</text>
    </view>

    <view class="update-entry" @click="checkAppUpdateManual">
      <text class="update-label">检查更新</text>
      <text class="update-arrow">›</text>
    </view>

    <view class="bottom-pad" />
    <MiniPlayer />
  </view>
</template>

<style scoped lang="scss">
.page {
  min-height: 100vh;
}
.member-entry {
  margin: 24rpx 16rpx 0;
  padding: 24rpx;
  background: $bg-card;
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  box-shadow: $shadow-card;

  &:active {
    background: $uni-bg-color-hover;
  }
}
.member-avatar {
  font-size: 44rpx;
  width: 72rpx;
  text-align: center;
}
.member-text {
  margin-left: 16rpx;
  display: flex;
  flex-direction: column;
}
.member-name {
  font-size: 30rpx;
  font-weight: bold;
  color: $text-main;
}
.member-account {
  margin-top: 4rpx;
  font-size: 22rpx;
  color: $text-disable;
}
.member-sub {
  margin-left: auto;
  margin-right: 12rpx;
  font-size: 22rpx;
  color: $text-disable;
}
.header {
  display: flex;
  align-items: baseline;
  padding: 32rpx 24rpx 16rpx;
}
.title {
  font-size: 36rpx;
  font-weight: bold;
  color: $text-main;
}
.count {
  margin-left: 16rpx;
  font-size: 24rpx;
  color: $text-sub;
}
.song-list {
  margin: 0 16rpx;
  background: $bg-card;
  border-radius: 16rpx;
  overflow: hidden;
}
.empty {
  margin-top: 120rpx;
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
.update-entry {
  margin: 16rpx 16rpx 0;
  padding: 28rpx 24rpx;
  background: $bg-card;
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: $shadow-card;
}
.update-label {
  font-size: 28rpx;
  color: $text-main;
}
.update-arrow {
  font-size: 32rpx;
  color: $text-sub;
}
.bottom-pad {
  height: 160rpx;
}
</style>
