<script setup lang="ts">
import { ref } from 'vue';
import { useAuthStore } from '@/store/auth';

/**
 * 登录页:账号 + 密码登录。不开放注册 —— 账号统一由管理员在后台创建,
 * 使用者拿到管理员下发的账号密码后在此登录。
 */

const auth = useAuthStore();

const username = ref('');
const password = ref('');
const submitting = ref(false);

async function doLogin() {
  const user = username.value.trim();
  if (!user || !password.value) {
    uni.showToast({ title: '请输入账号和密码', icon: 'none' });
    return;
  }
  if (submitting.value) return;
  submitting.value = true;
  uni.showLoading({ title: '登录中', mask: true });
  try {
    await auth.login(user, password.value);
    uni.hideLoading();
    uni.reLaunch({ url: '/pages/home/index' });
  } catch (err) {
    uni.hideLoading();
    const msg = (err as { statusCode?: number }).statusCode === 401
      ? '账号或密码错误'
      : '登录失败,请检查网络';
    uni.showToast({ title: msg, icon: 'none' });
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <view class="page">
    <view class="hero">
      <text class="logo">🎵</text>
      <text class="title">启蒙音频</text>
      <text class="sub">输入账号密码开始使用</text>
    </view>

    <view class="form">
      <input
        v-model="username"
        class="field"
        :maxlength="24"
        placeholder="账号"
        confirm-type="next"
      />
      <input
        v-model="password"
        class="field"
        :maxlength="64"
        :password="true"
        placeholder="密码"
        confirm-type="done"
        @confirm="doLogin()"
      />

      <button
        class="submit"
        :disabled="submitting"
        @click="doLogin()"
      >登 录</button>
    </view>

    <view class="foot-tip">
      <text>账号由管理员在后台创建 · 如需开通或找回密码请联系管理员</text>
    </view>
  </view>
</template>

<style scoped lang="scss">
.page {
  min-height: 100vh;
  padding: 0 60rpx;
  display: flex;
  flex-direction: column;
}
.hero {
  margin-top: 200rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.logo {
  font-size: 96rpx;
  line-height: 1;
}
.title {
  margin-top: 24rpx;
  font-size: 44rpx;
  font-weight: bold;
  color: $text-main;
}
.sub {
  margin-top: 12rpx;
  font-size: 26rpx;
  color: $text-sub;
}
.form {
  margin-top: 96rpx;
}
.field {
  margin-bottom: 24rpx;
  padding: 24rpx 28rpx;
  background: $bg-card;
  border-radius: 16rpx;
  font-size: 30rpx;
  box-shadow: $shadow-card;
}
.submit {
  margin-top: 16rpx;
  background: #ff8c42;
  color: #ffffff;
  font-size: 32rpx;
  border-radius: 16rpx;

  &[disabled] {
    opacity: 0.6;
  }
}
.foot-tip {
  margin-top: auto;
  padding: 48rpx 0 64rpx;
  text-align: center;
  font-size: 22rpx;
  color: $text-disable;
}
</style>
