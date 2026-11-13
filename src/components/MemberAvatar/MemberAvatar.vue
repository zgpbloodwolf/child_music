<script setup lang="ts">
import { ref, computed, watch } from 'vue';

/**
 * 成员头像:兼容两种形态 —— 预设 emoji(白底圆内单字符)与上传图片(URL 圆形裁剪)。
 * avatar 值来自 member 数据:emoji 原样透传;图片是后端拼好的完整 URL
 * (见服务端 avatar_out,与歌曲封面同口径,含静态资源令牌)。
 * 图片加载失败(文件被清理/网络异常)回退默认 emoji,不出现裂图。
 */
const props = withDefaults(defineProps<{
  /** 头像值:emoji 字符或图片完整 URL;空串按无头像处理 */
  avatar: string;
  /** 头像直径(rpx) */
  size?: number;
}>(), { size: 96 });

/** 是否为上传图片形态(完整 http URL) */
const isImage = computed(() => /^https?:\/\//.test(props.avatar));
/** 图片加载失败标记(回退 emoji;切换头像源时重置) */
const failed = ref(false);
watch(() => props.avatar, () => { failed.value = false; });
/** emoji 展示值(空串回退默认 ⭐) */
const emoji = computed(() => props.avatar || '⭐');
</script>

<template>
  <view class="ma" :style="{ width: size + 'rpx', height: size + 'rpx' }">
    <image
      v-if="isImage && !failed"
      class="ma-img"
      :src="avatar"
      mode="aspectFill"
      @error="failed = true"
    />
    <text v-else class="ma-emoji" :style="{ fontSize: Math.round(size * 0.55) + 'rpx' }">{{ emoji }}</text>
  </view>
</template>

<style scoped lang="scss">
.ma {
  border-radius: 50%;
  background: #ffffff;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.ma-img {
  width: 100%;
  height: 100%;
}
.ma-emoji {
  line-height: 1;
}
</style>
