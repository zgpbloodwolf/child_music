<script setup lang="ts">
import { ref } from 'vue';
import { useAuthStore } from '@/store/auth';
import { currentMember } from '@/store/memberPrefs';

/**
 * 账号管理页:账号信息展示 + 自助修改资料(昵称/头像)+ 自助修改密码 + 退出登录。
 * 登录账号(username)由管理员统一管理,不开放自改;切换账号 = 退出后重新登录。
 */
const auth = useAuthStore();
const current = currentMember;

// ===== 编辑资料 =====
/** 预设头像(emoji,与后端 avatar 字段约定一致:单个字符,展示用) */
const AVATAR_CHOICES = ['⭐', '🐱', '🦊', '🐼', '🐰', '🐯', '🦁', '🦄', '🐳', '🚀', '🌈', '🌻', '🍀', '🎈', '🎸'];
/** 默认头像(当前账号未设置头像时选用) */
const DEFAULT_AVATAR = '⭐';

/** 资料表单:初值取当前账号(未设置头像时默认 ⭐) */
const profileForm = ref({
  name: current.value?.name ?? '',
  avatar: current.value?.avatar || DEFAULT_AVATAR,
});
const profileSaving = ref(false);

/** 保存资料:昵称必填;成功后 currentMember 由 store 更新,我的页头部自动刷新 */
async function saveProfile() {
  const name = profileForm.value.name.trim();
  if (!name) {
    uni.showToast({ title: '昵称不能为空', icon: 'none' });
    return;
  }
  if (profileSaving.value) return;
  profileSaving.value = true;
  try {
    await auth.updateProfile({ name, avatar: profileForm.value.avatar });
    uni.showToast({ title: '已保存', icon: 'none' });
  } catch (err) {
    uni.showToast({ title: err instanceof Error ? err.message : '保存失败', icon: 'none' });
  } finally {
    profileSaving.value = false;
  }
}

// ===== 修改密码 =====
/** 密码长度约束(与后端 check_password 一致:4-64 位) */
const PASSWORD_MIN = 4;
const PASSWORD_MAX = 64;

const pwdForm = ref({ oldPassword: '', newPassword: '', confirm: '' });
const pwdSaving = ref(false);

/** 修改密码:前端先做基础校验,旧密码错误等由后端校验并经 toast 提示 */
async function savePassword() {
  const { oldPassword, newPassword, confirm } = pwdForm.value;
  if (!oldPassword || !newPassword || !confirm) {
    uni.showToast({ title: '请填写完整', icon: 'none' });
    return;
  }
  if (newPassword.length < PASSWORD_MIN || newPassword.length > PASSWORD_MAX) {
    uni.showToast({ title: `新密码需为 ${PASSWORD_MIN}-${PASSWORD_MAX} 位`, icon: 'none' });
    return;
  }
  if (newPassword !== confirm) {
    uni.showToast({ title: '两次输入的新密码不一致', icon: 'none' });
    return;
  }
  if (pwdSaving.value) return;
  pwdSaving.value = true;
  try {
    await auth.changePassword(oldPassword, newPassword);
    pwdForm.value = { oldPassword: '', newPassword: '', confirm: '' };
    uni.showToast({ title: '密码已修改', icon: 'none' });
  } catch (err) {
    // RequestError.message 已带后端中文提示(如「旧密码不正确」)
    uni.showToast({ title: err instanceof Error ? err.message : '修改失败', icon: 'none' });
  } finally {
    pwdSaving.value = false;
  }
}

/** 退出登录:回登录页,可用其他账号登录 */
function logout() {
  uni.showModal({
    title: '退出登录?',
    content: '退出后需用账号密码重新登录',
    confirmColor: '#e64340',
    success: (res) => {
      if (res.confirm) auth.logout();
    },
  });
}
</script>

<template>
  <view class="page">
    <!-- 渐变账号卡(与「我的」页头部同风格) -->
    <view v-if="current" class="member-card">
      <view class="avatar-ring">
        <text class="avatar">{{ current.avatar || '⭐' }}</text>
      </view>
      <view class="member-info">
        <text class="name">{{ current.name }}</text>
        <text class="username">{{ current.username ? `账号 ${current.username}` : '未设置账号' }}</text>
      </view>
      <view class="now-badge">
        <text class="now-text">当前</text>
      </view>
    </view>

    <!-- 编辑资料 -->
    <view class="card">
      <text class="card-title">编辑资料</text>
      <view class="field">
        <text class="field-label">头像</text>
        <view class="avatar-grid">
          <view
            v-for="a in AVATAR_CHOICES"
            :key="a"
            class="avatar-option"
            :class="{ active: a === profileForm.avatar }"
            @click="profileForm.avatar = a"
          >
            <text class="avatar-option-text">{{ a }}</text>
          </view>
        </view>
      </view>
      <view class="field">
        <view class="field-head">
          <text class="field-label">昵称</text>
          <text class="field-tip">{{ profileForm.name.length }}/64</text>
        </view>
        <input
          v-model="profileForm.name"
          class="input"
          type="text"
          placeholder="请输入昵称"
          placeholder-class="input-placeholder"
          :maxlength="64"
        >
      </view>
      <view class="btn" :class="{ disabled: profileSaving }" @click="saveProfile">
        <text class="btn-text">{{ profileSaving ? '保存中…' : '保存修改' }}</text>
      </view>
    </view>

    <!-- 修改密码 -->
    <view class="card">
      <text class="card-title">修改密码</text>
      <view class="field">
        <text class="field-label">旧密码</text>
        <input
          v-model="pwdForm.oldPassword"
          class="input"
          password
          placeholder="请输入旧密码"
          placeholder-class="input-placeholder"
        >
      </view>
      <view class="field">
        <text class="field-label">新密码</text>
        <input
          v-model="pwdForm.newPassword"
          class="input"
          password
          :placeholder="`请输入新密码(${PASSWORD_MIN}-${PASSWORD_MAX} 位)`"
          placeholder-class="input-placeholder"
        >
      </view>
      <view class="field">
        <text class="field-label">确认新密码</text>
        <input
          v-model="pwdForm.confirm"
          class="input"
          password
          placeholder="请再次输入新密码"
          placeholder-class="input-placeholder"
        >
      </view>
      <view class="btn" :class="{ disabled: pwdSaving }" @click="savePassword">
        <text class="btn-text">{{ pwdSaving ? '提交中…' : '修改密码' }}</text>
      </view>
    </view>

    <view class="tip">
      <text>每个账号的收藏和播放记录各自独立、多设备同步</text>
      <text>登录账号由管理员管理,如需更换请联系管理员</text>
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
  padding: 24rpx 24rpx 60rpx;
}
/* ===== 渐变账号卡 ===== */
.member-card {
  display: flex;
  align-items: center;
  padding: 36rpx 32rpx;
  background: linear-gradient(135deg, $primary-light, $primary);
  border-radius: 28rpx;
  box-shadow: $shadow-card;
}
.avatar-ring {
  width: 112rpx;
  height: 112rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.28);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.avatar {
  width: 96rpx;
  height: 96rpx;
  border-radius: 50%;
  background: #ffffff;
  font-size: 52rpx;
  text-align: center;
  line-height: 96rpx;
}
.member-info {
  flex: 1;
  min-width: 0;
  margin-left: 24rpx;
  display: flex;
  flex-direction: column;
}
.name {
  font-size: 34rpx;
  font-weight: bold;
  color: #ffffff;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.username {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.82);
}
.now-badge {
  margin-left: 16rpx;
  padding: 8rpx 20rpx;
  background: rgba(255, 255, 255, 0.24);
  border-radius: 999rpx;
  flex-shrink: 0;
}
.now-text {
  font-size: 22rpx;
  color: #ffffff;
}
/* ===== 表单卡片(编辑资料 / 修改密码共用) ===== */
.card {
  margin-top: 24rpx;
  padding: 32rpx 28rpx;
  background: $bg-card;
  border-radius: 28rpx;
  box-shadow: $shadow-card;
}
.card-title {
  display: block;
  font-size: 30rpx;
  font-weight: bold;
  color: $text-main;
}
.field {
  margin-top: 32rpx;
}
.field-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.field-label {
  display: block;
  font-size: 24rpx;
  color: $text-sub;
}
.field-tip {
  font-size: 22rpx;
  color: $text-disable;
}
.avatar-grid {
  margin-top: 20rpx;
  margin-right: -20rpx; /* 抵消末列多余间距,保持网格对齐 */
  display: flex;
  flex-wrap: wrap;
}
.avatar-option {
  width: 96rpx;
  height: 96rpx;
  margin: 0 20rpx 20rpx 0;
  border: 2rpx solid transparent;
  border-radius: 22rpx;
  background: $uni-bg-color-grey;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.12s ease;

  &.active {
    border-color: $primary;
    background: #ffffff;
    box-shadow: 0 0 0 6rpx $primary-soft;
    transform: scale(1.05);
  }
}
.avatar-option-text {
  font-size: 44rpx;
}
.input {
  margin-top: 16rpx;
  padding: 22rpx 24rpx;
  background: #ffffff;
  border: 2rpx solid $divider;
  border-radius: 18rpx;
  font-size: 28rpx;
  color: $text-main;
}
.input-placeholder {
  color: $text-disable;
}
.btn {
  margin-top: 40rpx;
  height: 88rpx;
  background: linear-gradient(135deg, $primary-light, $primary);
  border-radius: 999rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8rpx 24rpx rgba(255, 140, 66, 0.32);

  &:active {
    opacity: 0.85;
  }
  &.disabled {
    opacity: 0.5;
  }
}
.btn-text {
  color: #ffffff;
  font-size: 30rpx;
  font-weight: bold;
}
/* ===== 提示与退出 ===== */
.tip {
  margin-top: 28rpx;
  padding: 0 12rpx;
  display: flex;
  flex-direction: column;
  gap: 10rpx;
  font-size: 24rpx;
  color: $text-sub;
}
.logout-entry {
  margin-top: 40rpx;
  padding: 30rpx 0;
  background: $bg-card;
  border-radius: 28rpx;
  text-align: center;
  box-shadow: $shadow-card;

  &:active {
    background: $uni-bg-color-hover;
  }
}
.logout-text {
  color: $danger;
  font-size: 30rpx;
}
.foot-tip {
  margin-top: 36rpx;
  text-align: center;
  font-size: 22rpx;
  color: $text-disable;
}
</style>
