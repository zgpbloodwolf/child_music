<script setup lang="ts">
import { useAuthStore } from '@/store/auth';
import { currentMember } from '@/store/memberPrefs';

/**
 * 账号页:只展示当前登录账号与退出登录。
 * 账号由管理员在后台统一创建/删除,App 内不开号、看不到其他账号;
 * 切换账号 = 退出登录后用对应账号重新登录。
 */

const auth = useAuthStore();
const current = currentMember;

/** 退出登录:回登录页,可用其他账号登录 */
function logout() {
  uni.showModal({
    title: '退出登录?',
    content: '退出后需用账号密码重新登录',
    success: (res) => {
      if (res.confirm) auth.logout();
    },
  });
}
</script>

<template>
  <view class="page">
    <view v-if="current" class="member-card">
      <text class="avatar">{{ current.avatar || '⭐' }}</text>
      <view class="member-info">
        <text class="name">{{ current.name }}</text>
        <text class="username">账号:{{ current.username || '未设置' }}</text>
      </view>
      <text class="check">当前</text>
    </view>

    <view class="tip">
      <text>每个账号的收藏和播放记录各自独立、多设备同步</text>
      <text>如需开通新账号或找回密码,请联系管理员</text>
    </view>

    <view class="logout-entry" @click="logout">
      <text class="logout-text">退出登录</text>
    </view>

    <view class="foot-tip">
      <text>切换账号请退出后重新登录</text>
    </view>
  </view>
</template>

<style scoped lang="scss">
.page {
  min-height: 100vh;
  padding: 24rpx 16rpx;
}
.member-card {
  display: flex;
  align-items: center;
  padding: 32rpx 24rpx;
  background: $bg-card;
  border-radius: 16rpx;
  box-shadow: $shadow-card;
}
.avatar {
  width: 80rpx;
  font-size: 48rpx;
  text-align: center;
  flex-shrink: 0;
}
.member-info {
  margin-left: 20rpx;
  display: flex;
  flex-direction: column;
}
.name {
  font-size: 30rpx;
  color: $text-main;
  font-weight: bold;
}
.username {
  margin-top: 4rpx;
  font-size: 22rpx;
  color: $text-disable;
}
.check {
  margin-left: auto;
  color: #ff8c42;
  font-size: 24rpx;
}
.tip {
  margin-top: 24rpx;
  padding: 0 8rpx;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
  font-size: 24rpx;
  color: $text-sub;
}
.logout-entry {
  margin-top: 40rpx;
  padding: 28rpx 24rpx;
  background: $bg-card;
  border-radius: 16rpx;
  text-align: center;
  box-shadow: $shadow-card;

  &:active {
    background: $uni-bg-color-hover;
  }
}
.logout-text {
  color: #e64340;
  font-size: 30rpx;
}
.foot-tip {
  margin-top: 40rpx;
  text-align: center;
  font-size: 22rpx;
  color: $text-disable;
}
</style>
