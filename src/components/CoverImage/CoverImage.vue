<script lang="ts">
/** 封面色块风格(仅无图兜底时生效);导出供 CategoryPanel / playlist 按主题映射复用 */
export type CoverVariant = 'primary' | 'seal' | 'warm' | 'candy' | 'bamboo' | 'moon';
</script>

<script setup lang="ts">
import { ref, computed } from 'vue';

/**
 * 封面图组件:有图显示图片,无图或加载失败时用渐变色块 + 文字兜底。
 * 尺寸由父级容器控制,本组件填满父级。
 * - variant: 兜底色块风格(默认 primary 暖橙;古诗类型卡用 warm 暖褐、作者卡用 seal 朱砂)
 * - placeholder: 显式指定兜底文字,优先于 name 首字
 */
const props = defineProps<{
  src?: string;
  name?: string;
  variant?: CoverVariant;
  placeholder?: string;
}>();

const failed = ref(false);
const showImg = computed(() => Boolean(props.src) && !failed.value);
/** 兜底文字:placeholder 优先,否则取 name 首字,再否则音符占位 */
const initial = computed(() => props.placeholder || (props.name ? props.name.charAt(0) : '♪'));
/** 非默认风格时输出的修饰类(用于切换兜底渐变色) */
const variantClass = computed(() =>
  props.variant && props.variant !== 'primary' ? `cover--${props.variant}` : '',
);

function onError() {
  failed.value = true;
}
</script>

<template>
  <view class="cover" :class="variantClass">
    <image
      v-if="showImg"
      class="cover-img"
      :src="src"
      mode="aspectFill"
      @error="onError"
    />
    <view v-else class="cover-fallback">{{ initial }}</view>
  </view>
</template>

<style scoped lang="scss">
.cover {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: 12rpx;
  background: linear-gradient(135deg, $primary-light, $primary);
}
/* 古诗·类型卡:暖褐封面 */
.cover--warm {
  background: linear-gradient(135deg, $poetry-warm-light, $poetry-warm);
}
/* 古诗·作者卡:朱砂方印 */
.cover--seal {
  background: linear-gradient(135deg, $poetry-cinnabar-light, $poetry-cinnabar);
}
/* 儿歌·糖果封面(粉橙黄,圆角更大) */
.cover--candy {
  background: linear-gradient(135deg, $children-cover-start, $children-cover-end);
  border-radius: 14rpx;
}
/* 三字经·竹简封面(竹青墨绿,方角) */
.cover--bamboo {
  background: linear-gradient(135deg, $classics-cover-start, $classics-cover-end);
  border-radius: 4rpx;
}
/* 故事·月光封面(暖黄,圆角) */
.cover--moon {
  background: linear-gradient(135deg, $story-cover-start, $story-cover-end);
  border-radius: 16rpx;
}
.cover-img {
  width: 100%;
  height: 100%;
  display: block;
}
.cover-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-weight: bold;
}
</style>
