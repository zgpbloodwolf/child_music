<script setup lang="ts">
import { computed } from 'vue';

/**
 * 古诗书卷头部:竖排书签(逐字堆叠)+ 副标题 + 朝代标签 + 右上朱砂方印。纯展示。
 * 竖排采用 flex column 逐字堆叠(不用 writing-mode),保证 H5/App/小程序三端一致。
 */
const props = withDefaults(
  defineProps<{
    /** 主标题(竖排书签逐字堆叠),如「古诗」 */
    title: string;
    /** 副标题文案 */
    subtitle: string;
    /** 朝代标签列表,如 ['唐','宋'] */
    dynasties?: string[];
    /** 右上角朱砂方印文字 */
    sealText?: string;
  }>(),
  {
    dynasties: () => [],
    sealText: '诗',
  },
);

/** 标题拆成单字数组,用于逐字纵向堆叠 */
const titleChars = computed(() => Array.from(props.title));
</script>

<template>
  <view class="hero">
    <!-- 竖排书签:逐字堆叠 -->
    <view class="scroll">
      <text v-for="(ch, i) in titleChars" :key="i" class="scroll-char">{{ ch }}</text>
    </view>
    <!-- 副标题 + 朝代标签 -->
    <view class="hero-info">
      <text class="hero-sub">{{ subtitle }}</text>
      <view v-if="dynasties.length" class="dynasties">
        <text v-for="(d, i) in dynasties" :key="i" class="dynasty">{{ d }}</text>
      </view>
    </view>
    <!-- 右上朱砂方印 -->
    <view class="seal">{{ sealText }}</view>
  </view>
</template>

<style scoped lang="scss">
.hero {
  position: relative;
  display: flex;
  align-items: stretch;
  gap: 28rpx;
  padding: 44rpx 32rpx 28rpx;
}
.scroll {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32rpx 20rpx;
  background: $poetry-card;
  border: 2rpx solid $poetry-paper-deep;
  border-radius: 8rpx;
  box-shadow: $poetry-shadow;
}
.scroll-char {
  font-size: 56rpx;
  font-weight: bold;
  color: $poetry-ink;
  line-height: 1.4;
  letter-spacing: 4rpx;
}
.hero-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.hero-sub {
  font-size: 36rpx;
  font-weight: 600;
  color: $poetry-ink;
  letter-spacing: 2rpx;
}
.dynasties {
  margin-top: 24rpx;
  display: flex;
  gap: 16rpx;
}
.dynasty {
  font-size: 24rpx;
  color: $poetry-cinnabar;
  border: 2rpx solid $poetry-cinnabar;
  padding: 4rpx 20rpx;
  border-radius: 4rpx;
  background: rgba($poetry-cinnabar, 0.06);
}
.seal {
  position: absolute;
  top: 36rpx;
  right: 36rpx;
  width: 80rpx;
  height: 80rpx;
  border-radius: 8rpx;
  background: $poetry-cinnabar;
  color: $poetry-card;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 44rpx;
  font-weight: bold;
  box-shadow: 0 4rpx 12rpx rgba($poetry-cinnabar, 0.35);
  transform: rotate(-6deg);
}
</style>
