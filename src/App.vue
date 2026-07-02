<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app';
import { usePlayerStore } from '@/store/player';
import { warmupRepository } from '@/repository';

onLaunch(() => {
  // 应用启动时绑定播放器全局监听器(仅绑定一次,见 CLAUDE.md 第 4 节)
  usePlayerStore().init();
  // 预热曲库到内存(JsonCatalogRepository fetch songs.json);查询会自动等待预热完成
  void warmupRepository();
});
</script>

<style lang="scss">
/* 全局页面基础样式(非 scoped,作用于所有页面) */
page {
  background-color: $bg-page;
  color: $text-main;
  font-size: 28rpx;
}
</style>
