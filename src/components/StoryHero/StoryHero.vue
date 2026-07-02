<script setup lang="ts">
/**
 * 故事梦幻头部:发光月亮(radial-gradient + 光晕)+ 星点 + 标题/描述 + 体裁标签。纯展示。
 * 浅色版:淡紫底、深紫字、月亮黄点缀。
 */
withDefaults(
  defineProps<{
    /** 大类名,如「故事」 */
    name: string;
    /** 描述文案 */
    desc: string;
    /** 体裁标签,默认寓言/童话/成语/神话 */
    tags?: string[];
    /** 图标(emoji),默认 🌙 */
    icon?: string;
  }>(),
  {
    tags: () => ['寓言', '童话', '成语', '神话'],
    icon: '🌙',
  },
);
</script>

<template>
  <view class="hero">
    <!-- 星点装饰 -->
    <view class="star star--1">✦</view>
    <view class="star star--2">✦</view>
    <!-- 发光月亮 -->
    <view class="moon">{{ icon }}</view>
    <!-- 标题 + 描述 + 标签 -->
    <view class="hero-info">
      <text class="hero-name">{{ name }}</text>
      <text class="hero-desc">{{ desc }}</text>
      <view class="tags">
        <text v-for="(t, i) in tags" :key="i" class="tag">{{ t }}</text>
      </view>
    </view>
  </view>
</template>

<style scoped lang="scss">
.hero {
  position: relative;
  display: flex;
  align-items: center;
  gap: 28rpx;
  padding: 44rpx 32rpx 32rpx;
}
/* 发光月亮 */
.moon {
  width: 140rpx;
  height: 140rpx;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, $story-moon-light, $story-moon);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 64rpx;
  box-shadow: 0 0 40rpx rgba($story-moon, 0.55);
}
.hero-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.hero-name {
  font-size: 44rpx;
  font-weight: bold;
  color: $story-text;
  letter-spacing: 2rpx;
}
.hero-desc {
  margin-top: 10rpx;
  font-size: 26rpx;
  color: $story-text-sub;
}
.tags {
  margin-top: 20rpx;
  display: flex;
  gap: 16rpx;
  flex-wrap: wrap;
}
.tag {
  font-size: 24rpx;
  color: $story-tag-text;
  border: 2rpx solid $story-tag-border;
  padding: 4rpx 20rpx;
  border-radius: 999rpx;
  background: rgba($story-moon, 0.1);
}
/* 星点装饰 */
.star {
  position: absolute;
  color: $story-accent;
  pointer-events: none;
}
.star--1 {
  top: 24rpx;
  right: 48rpx;
  font-size: 28rpx;
}
.star--2 {
  top: 84rpx;
  right: 124rpx;
  font-size: 20rpx;
}
</style>
