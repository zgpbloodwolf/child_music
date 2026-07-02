<script setup lang="ts">
/**
 * 儿歌糖果头部:彩虹圆角图标(线性多色带,不用 conic-gradient 保三端兼容)
 * + 漂浮音符 + 标题/描述 + 年龄标签。纯展示。
 */
withDefaults(
  defineProps<{
    /** 大类名,如「儿歌」 */
    name: string;
    /** 描述文案 */
    desc: string;
    /** 年龄标签,默认 0-3 / 3-6 岁 */
    ageTags?: string[];
    /** 图标(emoji),默认 🎵 */
    icon?: string;
  }>(),
  {
    ageTags: () => ['0-3 岁', '3-6 岁'],
    icon: '🎵',
  },
);
</script>

<template>
  <view class="hero">
    <!-- 漂浮音符装饰(纯装饰,不拦截点击) -->
    <view class="bubble bubble--1">♪</view>
    <view class="bubble bubble--2">♫</view>
    <!-- 彩虹圆角图标 -->
    <view class="hero-icon">{{ icon }}</view>
    <!-- 标题 + 描述 + 年龄标签 -->
    <view class="hero-info">
      <text class="hero-name">{{ name }}</text>
      <text class="hero-desc">{{ desc }}</text>
      <view v-if="ageTags.length" class="age-tags">
        <text v-for="(t, i) in ageTags" :key="i" class="age-tag">{{ t }}</text>
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
  padding: 40rpx 32rpx 28rpx;
}
/* 彩虹图标:linear-gradient 多色带模拟彩虹(规避 conic-gradient,三端一致) */
.hero-icon {
  width: 140rpx;
  height: 140rpx;
  border-radius: 48rpx;
  background: linear-gradient(
    135deg,
    $children-rainbow-1 0%,
    $children-rainbow-2 25%,
    $children-rainbow-3 50%,
    $children-rainbow-4 75%,
    $children-rainbow-5 100%
  );
  border: 6rpx solid #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 64rpx;
  box-shadow: 0 12rpx 24rpx rgba($children-rainbow-1, 0.35);
}
.hero-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.hero-name {
  font-size: 44rpx;
  font-weight: 800;
  color: $children-text;
  letter-spacing: 2rpx;
}
.hero-desc {
  margin-top: 10rpx;
  font-size: 26rpx;
  color: $children-text-sub;
}
.age-tags {
  margin-top: 20rpx;
  display: flex;
  gap: 16rpx;
}
.age-tag {
  font-size: 24rpx;
  font-weight: 600;
  color: $children-accent;
  background: rgba($children-accent, 0.12);
  padding: 6rpx 24rpx;
  border-radius: 999rpx;
}
/* 漂浮音符 */
.bubble {
  position: absolute;
  font-weight: bold;
  pointer-events: none;
}
.bubble--1 {
  top: 16rpx;
  right: 36rpx;
  font-size: 44rpx;
  color: rgba($children-rainbow-1, 0.6);
}
.bubble--2 {
  top: 84rpx;
  right: 108rpx;
  font-size: 30rpx;
  color: rgba($children-rainbow-4, 0.6);
}
</style>
