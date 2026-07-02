<script setup lang="ts">
import { computed } from 'vue';
import type { SongMeta } from '@/types/song';
import CoverImage from '@/components/CoverImage/CoverImage.vue';

/**
 * 歌曲列表项:序号(可选) + 封面 + 歌名 + 歌手/专辑,点击触发 play。
 * 通过 #extra 插槽可追加操作(如收藏按钮)。
 * 注:列表项只需展示用元数据 SongMeta(不含音频地址 / 歌词)。
 */
const props = defineProps<{
  song: SongMeta;
  /** 序号(0 基,传入则在封面左侧显示;不传则不显示,用于区分歌单详情 vs 首页/我的等列表) */
  index?: number;
}>();
const emit = defineEmits<{ (e: 'play'): void }>();

const subtitle = computed(() =>
  props.song.album ? `${props.song.artist} - ${props.song.album}` : props.song.artist,
);
</script>

<template>
  <view class="song-item" @click="emit('play')">
    <text v-if="index !== undefined" class="song-idx">{{ index + 1 }}</text>
    <view class="cover-wrap">
      <CoverImage :src="song.cover" :name="song.name" />
    </view>
    <view class="info">
      <text class="name">{{ song.name }}</text>
      <text class="sub">{{ subtitle }}</text>
    </view>
    <view class="extra">
      <slot name="extra" />
    </view>
  </view>
</template>

<style scoped lang="scss">
.song-item {
  display: flex;
  align-items: center;
  padding: 16rpx 24rpx;
  background: $bg-card;

  &:active {
    background: $uni-bg-color-hover;
  }
}
.song-idx {
  width: 48rpx;
  flex-shrink: 0;
  text-align: center;
  color: $text-disable;
  font-size: 28rpx;
}
.cover-wrap {
  width: 88rpx;
  height: 88rpx;
  flex-shrink: 0;
}
.info {
  flex: 1;
  min-width: 0;
  margin-left: 20rpx;
  display: flex;
  flex-direction: column;
}
.name {
  font-size: 30rpx;
  color: $text-main;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.sub {
  margin-top: 6rpx;
  font-size: 24rpx;
  color: $text-sub;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.extra {
  flex-shrink: 0;
  margin-left: 16rpx;
}
</style>
