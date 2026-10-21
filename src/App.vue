<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app';
import { usePlayerStore } from '@/store/player';
import { useAuthStore } from '@/store/auth';
import { warmupRepository } from '@/repository';
import { checkAppUpdate } from '@/utils/appUpdate';
import { getAuthToken } from '@/utils/authToken';

onLaunch(() => {
  // 登录门禁:无会话令牌直接进登录页,其余初始化全部延后(避免无谓的 401 请求)
  if (!getAuthToken()) {
    uni.reLaunch({ url: '/pages/login/index' });
    return;
  }
  // 应用启动时绑定播放器全局监听器(仅绑定一次,见 CLAUDE.md 第 4 节;纯本地绑定,无网络请求)
  usePlayerStore().init();
  // 启动校验:确认令牌仍有效、账号未被删(失效时 request 层统一踢回登录页)。
  // 校验通过后才预热/查更新 —— 令牌失效时这两步不白发请求
  void useAuthStore().ensureValid().then((ok) => {
    if (!ok) return;
    // 预热 Repository(当前 ApiCatalogRepository:触发分类树请求建立连接);查询会自动等待预热完成
    void warmupRepository();
    // 启动后异步检查整包更新(失败静默,不阻断启动;H5/小程序为 no-op,App 端 24h 节流)
    void checkAppUpdate();
  });
});
</script>

<style lang="scss">
/* 全局页面基础样式(非 scoped,作用于所有页面) */
page {
  background-color: $bg-page;
  color: $text-main;
  font-size: 28rpx;
  /* 关闭页面滚到边界时的橡皮筋回弹,避免手机滑动时整个页面跟着晃动(H5 / 小程序端生效) */
  overscroll-behavior: none;
}
</style>
