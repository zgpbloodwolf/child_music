<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { usePlayerStore } from '@/store/player';
import { useLibraryStore } from '@/store/library';
import { getRepository } from '@/repository';
import { parseLyric, type LyricLine } from '@/utils/lyric';
import { formatTime } from '@/utils/format';
import { PlayMode } from '@/types/song';
import type { SongMeta } from '@/types/song';
import CoverImage from '@/components/CoverImage/CoverImage.vue';

/**
 * 播放页:圆形旋转封面、歌词同步、进度、控制、收藏、倍速、定时关闭、加载/错误提示。
 * 右上角「播放列表」入口可弹出当前队列,点选切歌。自定义导航栏(navigationStyle: custom),深色沉浸式背景。
 */
const player = usePlayerStore();
const library = useLibraryStore();
const repo = getRepository();
const {
  currentSong, isPlaying, isLoading, currentTime, duration, playMode,
  error, playbackRate, timerRemaining, timerActive,
  playlist, currentIndex,
} = storeToRefs(player);

const statusBarHeight = ref<number>(uni.getSystemInfoSync().statusBarHeight || 20);

const lyricLines = computed<LyricLine[]>(() =>
  currentSong.value?.lyric ? parseLyric(currentSong.value.lyric) : [],
);
const hasLyric = computed(() => lyricLines.value.length > 0);
const activeLine = computed(() => {
  const t = currentTime.value;
  let idx = -1;
  for (let i = 0; i < lyricLines.value.length; i++) {
    if (lyricLines.value[i].time <= t) idx = i;
    else break;
  }
  return idx;
});
const scrollInto = computed(() => (activeLine.value >= 0 ? `line-${activeLine.value}` : ''));
const liked = computed(() => (currentSong.value ? library.isLiked(currentSong.value.id) : false));

const playModeText = computed(() => {
  switch (playMode.value) {
    case PlayMode.LOOP_ONE: return '单曲';
    case PlayMode.RANDOM: return '随机';
    default: return '顺序';
  }
});
const rateText = computed(() => (playbackRate.value === 1 ? '1.0x' : `${playbackRate.value}x`));
const timerText = computed(() => (timerActive.value ? formatTime(timerRemaining.value) : '定时'));

// 进度条:拖动用本地值,松手才 seek
const dragging = ref(false);
const dragValue = ref(0);
const displayTime = computed(() => (dragging.value ? dragValue.value : currentTime.value));
interface SliderEvent { detail: { value: number } }
function onChanging(e: SliderEvent) { dragging.value = true; dragValue.value = e.detail.value; }
function onChange(e: SliderEvent) { player.seek(e.detail.value); dragging.value = false; }

function toggleLike() {
  if (currentSong.value) library.toggleLike(currentSong.value.id);
}
function goBack() { uni.navigateBack(); }

/** 定时关闭:弹出时长选择 */
function openTimer() {
  uni.showActionSheet({
    itemList: ['15 分钟', '30 分钟', '45 分钟', '60 分钟', '取消定时'],
    success: (res) => {
      const minutes = [15, 30, 45, 60];
      if (res.tapIndex < 4) {
        player.startTimer(minutes[res.tapIndex]);
        uni.showToast({ title: `将在 ${minutes[res.tapIndex]} 分钟后停止`, icon: 'none' });
      } else {
        player.cancelTimer();
        uni.showToast({ title: '已取消定时', icon: 'none' });
      }
    },
  });
}

// ===== 播放列表弹层 =====
/** 弹层是否展开 */
const showQueue = ref(false);
/** 当前队列对应的歌曲元数据(仅展示用);playlist 整体更换时才重新拉取,切歌不触发 */
const queueSongs = ref<SongMeta[]>([]);
watch(playlist, async (ids) => {
  queueSongs.value = ids.length ? await repo.listByIds(ids) : [];
}, { immediate: true });
/** 弹层展开时自动滚到当前播放项 */
const queueScrollInto = computed(() =>
  showQueue.value && currentIndex.value >= 0 ? `queue-${currentIndex.value}` : '',
);
/** 点选队列项切歌(不关闭弹层,便于连续切歌;当前项随之高亮) */
function playQueueAt(i: number) {
  player.playQueueIndex(i);
}
</script>

<template>
  <view class="player-page" :style="{ paddingTop: statusBarHeight + 'px' }">
    <view class="nav">
      <text class="nav-back" @click="goBack">↓</text>
    </view>

    <!-- 圆形旋转封面 + 加载指示 -->
    <view class="disc-wrap">
      <view class="disc" :class="{ paused: !isPlaying }">
        <CoverImage :src="currentSong?.cover" :name="currentSong?.name" />
      </view>
      <view v-if="isLoading" class="loading">加载中…</view>
    </view>

    <!-- 名称 / 作者 + 收藏 -->
    <view class="meta">
      <view class="meta-info">
        <text class="name">{{ currentSong?.name || '未在播放' }}</text>
        <text class="artist">{{ currentSong?.artist }}</text>
      </view>
      <text class="like-btn" :class="{ active: liked }" @click="toggleLike">{{ liked ? '♥' : '♡' }}</text>
    </view>

    <!-- 错误提示 -->
    <view v-if="error" class="error-tip">
      <text>{{ error }}</text>
    </view>

    <!-- 歌词区 -->
    <view class="lyric-wrap">
      <scroll-view v-if="hasLyric" scroll-y class="lyric-scroll" :scroll-into-view="scrollInto" scroll-with-animation>
        <view class="lyric-pad" />
        <view
          v-for="(line, i) in lyricLines"
          :id="`line-${i}`"
          :key="i"
          class="lyric-line"
          :class="{ active: i === activeLine }"
        >{{ line.text }}</view>
        <view class="lyric-pad" />
      </scroll-view>
      <view v-else class="no-lyric"><text>暂无歌词</text></view>
    </view>

    <!-- 进度条 -->
    <view class="progress">
      <text class="time">{{ formatTime(displayTime) }}</text>
      <slider
        class="slider"
        :value="displayTime"
        :min="0"
        :max="duration > 0 ? duration : 1"
        :step="1"
        :block-size="16"
        active-color="#ff8c42"
        background-color="rgba(255,255,255,0.2)"
        block-color="#ffffff"
        @changing="onChanging"
        @change="onChange"
      />
      <text class="time">{{ formatTime(duration) }}</text>
    </view>

    <!-- 次级控制:倍速 / 定时(增强功能,模式已并入主控制行) -->
    <view class="sub-controls">
      <text class="sub-btn" @click="player.cyclePlaybackRate()">{{ rateText }}</text>
      <text class="sub-btn" @click="openTimer">{{ timerText }}</text>
    </view>

    <!-- 主控制:左组(模式/上一首) · 中央播放暂停 · 右组(下一首/列表),播放键左右对称居中 -->
    <view class="main-controls">
      <view class="ctrl-side ctrl-side--left">
        <text class="ctrl" @click="player.togglePlayMode()">{{ playModeText }}</text>
        <text class="ctrl" @click="player.playPrev()">⏮</text>
      </view>
      <view class="play" @click="player.togglePlay()">{{ isPlaying ? '❚❚' : '▶' }}</view>
      <view class="ctrl-side ctrl-side--right">
        <text class="ctrl" @click="player.playNext()">⏭</text>
        <text class="ctrl ctrl-queue" @click="showQueue = true">☰</text>
      </view>
    </view>

    <!-- 播放列表弹层:点击遮罩关闭,点项切歌(不关闭,便于连续切歌) -->
    <view v-if="showQueue" class="queue-mask" @click="showQueue = false">
      <view class="queue-sheet" @click.stop>
        <view class="queue-header">
          <text class="queue-title">播放列表</text>
          <text class="queue-count">{{ queueSongs.length }} 首</text>
          <text class="queue-close" @click="showQueue = false">✕</text>
        </view>
        <scroll-view scroll-y class="queue-scroll" :scroll-into-view="queueScrollInto" scroll-with-animation>
          <view
            v-for="(s, i) in queueSongs"
            :id="`queue-${i}`"
            :key="s.id"
            class="queue-item"
            :class="{ active: i === currentIndex }"
            @click="playQueueAt(i)"
          >
            <text class="queue-idx">{{ i === currentIndex ? '▶' : i + 1 }}</text>
            <view class="queue-info">
              <text class="queue-name">{{ s.name }}</text>
              <text class="queue-sub">{{ s.artist }}</text>
            </view>
          </view>
          <view v-if="!queueSongs.length" class="queue-empty"><text>播放列表为空</text></view>
        </scroll-view>
      </view>
    </view>
  </view>
</template>

<style scoped lang="scss">
.player-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden; /* 固定一屏,禁止整页滚动;歌词区靠内部 scroll-view 自行滚动 */
  background: $player-bg;
  padding-bottom: calc(40rpx + env(safe-area-inset-bottom));
}
.nav {
  height: 80rpx;
  display: flex;
  align-items: center;
  padding: 0 24rpx;
}
.nav-back {
  font-size: 44rpx;
  color: #ffffff;
}
.disc-wrap {
  position: relative;
  display: flex;
  justify-content: center;
  margin: 20rpx 0 30rpx;
}
.disc {
  width: 420rpx;
  height: 420rpx;
  border-radius: 50%;
  overflow: hidden;
  box-shadow: 0 10rpx 40rpx rgba(0, 0, 0, 0.4);
  animation: spin 12s linear infinite;
}
.disc.paused {
  animation-play-state: paused;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.loading {
  position: absolute;
  bottom: -40rpx;
  color: rgba(255, 255, 255, 0.7);
  font-size: 24rpx;
}
.meta {
  display: flex;
  align-items: center;
  padding: 0 48rpx;
}
.meta-info {
  flex: 1;
  min-width: 0;
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
.artist {
  margin-top: 8rpx;
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.6);
}
.like-btn {
  font-size: 48rpx;
  color: rgba(255, 255, 255, 0.6);
}
.like-btn.active {
  color: $primary;
}
.error-tip {
  margin: 16rpx 48rpx 0;
  padding: 12rpx 20rpx;
  background: rgba(255, 77, 79, 0.2);
  border: 1rpx solid rgba(255, 77, 79, 0.5);
  border-radius: 12rpx;
  color: #ffd0d0;
  font-size: 24rpx;
  text-align: center;
}
.lyric-wrap {
  flex: 1;
  margin: 24rpx 0;
  height: 300rpx;
}
.lyric-scroll {
  height: 100%;
}
.lyric-pad {
  height: 120rpx;
}
.lyric-line {
  padding: 14rpx 48rpx;
  font-size: 28rpx;
  color: rgba(255, 255, 255, 0.4);
  text-align: center;
}
.lyric-line.active {
  color: #ffffff;
  font-size: 30rpx;
  font-weight: bold;
}
.no-lyric {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.4);
}
.progress {
  display: flex;
  align-items: center;
  padding: 0 24rpx;
  margin-top: 16rpx;
}
.time {
  width: 90rpx;
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.7);
  text-align: center;
}
.slider {
  flex: 1;
  margin: 0 8rpx;
}
.sub-controls {
  display: flex;
  justify-content: space-around;
  padding: 24rpx 48rpx 0;
}
.sub-btn {
  padding: 10rpx 24rpx;
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.85);
  border: 1rpx solid rgba(255, 255, 255, 0.4);
  border-radius: 999rpx;
}
.main-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 30rpx 40rpx 0;
}
/* 左右两组各 flex:1 等宽,使中央播放键严格水平居中 */
.ctrl-side {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 56rpx;
}
.ctrl-side--left {
  justify-content: flex-start;
}
.ctrl-side--right {
  justify-content: flex-end;
}
.ctrl {
  color: #ffffff;
  font-size: 26rpx;
}
/* 列表入口图标:与 ⏮⏭ 同行,字号略大以平衡 hamburger 笔画 */
.ctrl-queue {
  font-size: 40rpx;
}
.play {
  width: 120rpx;
  height: 120rpx;
  line-height: 120rpx;
  text-align: center;
  border-radius: 50%;
  background: $primary;
  color: #ffffff;
  font-size: 28rpx;
}

/* ===== 播放列表弹层(自绘,跨端安全:不用 inset,scroll-view 固定高度) ===== */
.queue-mask {
  position: fixed;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 200;
}
.queue-sheet {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(28, 28, 32, 0.97);
  border-radius: 24rpx 24rpx 0 0;
  padding-bottom: env(safe-area-inset-bottom);
}
.queue-header {
  display: flex;
  align-items: center;
  padding: 28rpx 32rpx 20rpx;
}
.queue-title {
  font-size: 32rpx;
  font-weight: bold;
  color: #ffffff;
}
.queue-count {
  margin-left: 16rpx;
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.5);
}
.queue-close {
  margin-left: auto;
  font-size: 32rpx;
  color: rgba(255, 255, 255, 0.7);
}
.queue-scroll {
  height: 56vh;
}
.queue-item {
  display: flex;
  align-items: center;
  padding: 20rpx 32rpx;
}
.queue-item.active {
  background: rgba(255, 140, 66, 0.12);
}
.queue-idx {
  width: 56rpx;
  flex-shrink: 0;
  text-align: center;
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.5);
}
.queue-item.active .queue-idx {
  color: $primary;
}
.queue-info {
  flex: 1;
  min-width: 0;
  margin-left: 16rpx;
  display: flex;
  flex-direction: column;
}
.queue-name {
  font-size: 28rpx;
  color: rgba(255, 255, 255, 0.85);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.queue-item.active .queue-name {
  color: $primary;
  font-weight: bold;
}
.queue-sub {
  margin-top: 4rpx;
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.45);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.queue-empty {
  padding: 80rpx 0;
  text-align: center;
  color: rgba(255, 255, 255, 0.4);
  font-size: 26rpx;
}
</style>
