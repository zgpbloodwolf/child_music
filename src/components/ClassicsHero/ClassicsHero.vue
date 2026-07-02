<script setup lang="ts">
/**
 * 三字经竹简头部:竹简组(几片竖向竹简横向并排,每片刻一字,不用 writing-mode 保三端一致)
 * + 标题/描述 + 蒙学/国学子标签。纯展示。
 */
withDefaults(
  defineProps<{
    /** 大类名,如「三字经」 */
    name: string;
    /** 描述文案 */
    desc: string;
    /** 竹简刻字(每字一片),默认「人之初」 */
    slipChars?: string[];
    /** 子标签,默认蒙学/国学 */
    tags?: string[];
  }>(),
  {
    slipChars: () => ['人', '之', '初'],
    tags: () => ['蒙学', '国学'],
  },
);
</script>

<template>
  <view class="hero">
    <!-- 竹简组:每片刻一字,横向并排 -->
    <view class="bamboo-scroll">
      <view v-for="(ch, i) in slipChars" :key="i" class="bamboo-slip">
        <text class="slip-char">{{ ch }}</text>
      </view>
    </view>
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
  display: flex;
  align-items: stretch;
  gap: 24rpx;
  padding: 40rpx 32rpx 28rpx;
  background: linear-gradient(180deg, rgba($classics-accent, 0.1), rgba($classics-accent, 0));
  border-bottom: 2rpx dashed rgba($classics-accent, 0.3);
}
/* 竹简组:横向并排 */
.bamboo-scroll {
  display: flex;
  gap: 10rpx;
}
/* 单片竹简:竖向窄条 */
.bamboo-slip {
  width: 56rpx;
  padding: 24rpx 0;
  border-radius: 8rpx;
  background: linear-gradient(180deg, $classics-slip-start, $classics-slip-end);
  border: 2rpx solid $classics-slip-border;
  box-shadow: inset 0 0 6rpx rgba(120, 100, 50, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
}
.slip-char {
  font-size: 40rpx;
  font-weight: bold;
  color: $classics-slip-text;
}
.hero-info {
  margin-left: 8rpx;
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.hero-name {
  font-size: 44rpx;
  font-weight: bold;
  color: $classics-text;
  letter-spacing: 4rpx;
}
.hero-desc {
  margin-top: 12rpx;
  font-size: 26rpx;
  color: $classics-text-sub;
  letter-spacing: 2rpx;
}
.tags {
  margin-top: 20rpx;
  display: flex;
  gap: 16rpx;
}
.tag {
  font-size: 24rpx;
  color: $classics-text-sub;
  border: 2rpx solid $classics-accent;
  padding: 4rpx 20rpx;
  border-radius: 4rpx;
  background: rgba($classics-accent, 0.08);
}
</style>
