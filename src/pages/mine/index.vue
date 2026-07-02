<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { useLibraryStore } from '@/store/library';
import { usePlayerStore } from '@/store/player';
import SongItem from '@/components/SongItem/SongItem.vue';
import MiniPlayer from '@/components/MiniPlayer/MiniPlayer.vue';
import type { SongMeta } from '@/types/song';

/** 我的页:展示「我喜欢的音乐」(本地持久化收藏) */
const library = useLibraryStore();
const player = usePlayerStore();
const { likedSongs } = storeToRefs(library);

/** 点击歌曲:以收藏列表为队列播放 */
function play(song: SongMeta) {
  player.playSong(song.id, likedSongs.value.map((s) => s.id));
}
</script>

<template>
  <view class="page">
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
.bottom-pad {
  height: 160rpx;
}
</style>
