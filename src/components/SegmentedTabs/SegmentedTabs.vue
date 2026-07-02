<script setup lang="ts">
/**
 * 分段切换标签(通用):单选高亮 + v-model。纯 UI 控件,不耦合业务。
 * tone 切换选中色调:primary(主色橙,默认)/ poetry(朱砂),色值内部用 $ 变量,不散落。
 */
const props = withDefaults(
  defineProps<{
    /** 可选项 */
    items: { value: string; label: string }[];
    /** 当前选中值(支持 v-model) */
    modelValue: string;
    /** 选中色调 */
    tone?: 'primary' | 'poetry';
  }>(),
  { tone: 'primary' },
);

const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>();

/** 点击某项,值变化时向外抛 update */
function pick(item: { value: string }) {
  if (item.value !== props.modelValue) emit('update:modelValue', item.value);
}
</script>

<template>
  <view class="seg-tabs" :class="`seg-tabs--${tone}`">
    <view
      v-for="item in items"
      :key="item.value"
      class="seg-tab"
      :class="{ active: item.value === modelValue }"
      @click="pick(item)"
    >{{ item.label }}</view>
  </view>
</template>

<style scoped lang="scss">
.seg-tabs {
  display: flex;
  gap: 56rpx;
  padding: 8rpx 32rpx 24rpx;
}
.seg-tab {
  position: relative;
  font-size: 30rpx;
  color: $text-sub;
  padding: 4rpx 0;
}
.seg-tab.active {
  color: $primary;
  font-weight: bold;
}
.seg-tab.active::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: -12rpx;
  transform: translateX(-50%);
  width: 40rpx;
  height: 6rpx;
  background: $primary;
  border-radius: 4rpx;
}
/* 古诗朱砂色调 */
.seg-tabs--poetry .seg-tab.active {
  color: $poetry-cinnabar;
}
.seg-tabs--poetry .seg-tab.active::after {
  background: $poetry-cinnabar;
}
</style>
