<script setup lang="ts">
import { ref, watch } from 'vue';
import { getRepository } from '@/repository';
import { usePlayerStore } from '@/store/player';
import SongItem from '@/components/SongItem/SongItem.vue';
import MiniPlayer from '@/components/MiniPlayer/MiniPlayer.vue';
import type { SongMeta } from '@/types/song';

/**
 * 搜索页:在内置曲库中按歌名 / 歌手 / 专辑本地搜索。
 * 通过 Repository 异步搜索(为未来大数据量 / SQLite 全文索引预留)。
 */
const player = usePlayerStore();
const repo = getRepository();
const keyword = ref('');
const results = ref<SongMeta[]>([]);
const searching = ref(false);

/** 关键词变化时异步搜索(空关键词清空结果) */
watch(keyword, async (kw) => {
  const trimmed = (kw ?? '').trim();
  if (!trimmed) { results.value = []; return; }
  searching.value = true;
  results.value = await repo.search(trimmed);
  searching.value = false;
});

/** 点击搜索结果:以当前结果列表为队列播放 */
function play(song: SongMeta) {
  player.playSong(song.id, results.value.map((s) => s.id));
}
</script>

<template>
  <view class="page">
    <view class="search-wrap">
      <input
        class="search-input"
        v-model="keyword"
        placeholder="搜索歌曲 / 歌手 / 专辑"
        confirm-type="search"
      />
    </view>

    <!-- 搜索结果(按原型带「搜索结果(N)」标题,列表项无序号) -->
    <view v-if="keyword && results.length" class="result-section">
      <text class="section-title">搜索结果({{ results.length }})</text>
      <view class="song-list">
        <SongItem
          v-for="song in results"
          :key="song.id"
          :song="song"
          @play="play(song)"
        />
      </view>
    </view>

    <view v-else-if="keyword && !results.length" class="empty">
      <text>没有找到相关歌曲</text>
    </view>

    <view v-else class="empty">
      <text>输入关键词搜索内置曲库</text>
    </view>

    <!-- 给底部悬浮播放栏预留滚动空间 -->
    <view class="bottom-pad" />
    <MiniPlayer />
  </view>
</template>

<style scoped lang="scss">
.page {
  min-height: 100vh;
}
.search-wrap {
  padding: 16rpx;
}
.search-input {
  width: 100%;
  box-sizing: border-box;
  padding: 18rpx 24rpx;
  font-size: 28rpx;
  color: $text-main;
  background: $bg-card;
  border-radius: 999rpx;
}
.result-section {
  padding: 0 16rpx;
}
.section-title {
  display: block;
  padding: 8rpx 8rpx 16rpx;
  font-size: 28rpx;
  font-weight: bold;
  color: $text-main;
}
.song-list {
  background: $bg-card;
  border-radius: 16rpx;
  overflow: hidden;
}
.empty {
  margin-top: 120rpx;
  text-align: center;
  color: $text-sub;
  font-size: 26rpx;
}
.bottom-pad {
  height: 160rpx;
}
</style>
