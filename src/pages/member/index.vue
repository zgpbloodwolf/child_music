<script setup lang="ts">
import { ref, computed } from 'vue';
import { useAuthStore } from '@/store/auth';
import { currentMember } from '@/store/memberPrefs';
import MemberAvatar from '@/components/MemberAvatar/MemberAvatar.vue';

/**
 * 账号管理页(系统设置风格的分组列表):账号概览(昵称即时预览)
 * + 账号信息分组(头像弹窗选择/上传、昵称行内编辑、登录账号只读)
 * + 安全分组(修改密码入口 → 底部弹窗)+ 退出登录。
 * 头像(预设 emoji / 相册上传)选完即时生效;昵称走「保存昵称」按钮。
 * 登录账号(username)由管理员统一管理,不开放自改;切换账号 = 退出后重新登录。
 */
const auth = useAuthStore();
const current = currentMember;

// ===== 昵称(表单编辑,保存按钮提交) =====
const profileForm = ref({ name: current.value?.name ?? '' });
/** 已保存基线:与表单比较得出「有无未保存改动」,无改动时禁用保存、不发无效请求 */
const profileBaseline = ref(current.value?.name ?? '');
const profileDirty = computed(() => profileForm.value.name.trim() !== profileBaseline.value);
const profileSaving = ref(false);

/** 保存昵称:成功后 currentMember 由 store 更新,我的页头部与本页概览自动刷新 */
async function saveProfile() {
  const name = profileForm.value.name.trim();
  if (!name) {
    uni.showToast({ title: '昵称不能为空', icon: 'none' });
    return;
  }
  if (profileSaving.value || !profileDirty.value) return;
  profileSaving.value = true;
  try {
    await auth.updateProfile({ name });
    profileForm.value.name = name; // 回写 trim 后的值,保证基线与输入框一致
    profileBaseline.value = name;
    uni.showToast({ title: '已保存', icon: 'none' });
  } catch (err) {
    uni.showToast({ title: err instanceof Error ? err.message : '保存失败', icon: 'none' });
  } finally {
    profileSaving.value = false;
  }
}

// ===== 头像(选完即时生效,不随「保存昵称」) =====
/** 预设头像(emoji,与后端 avatar 字段约定一致:单个字符,展示用) */
const AVATAR_CHOICES = ['⭐', '🐱', '🦊', '🐼', '🐰', '🐯', '🦁', '🦄', '🐳', '🚀', '🌈', '🌻', '🍀', '🎈', '🎸'];

/** 头像选择弹窗(概览卡头像与「头像」行两个入口共用) */
const showAvatarSheet = ref(false);
/** 头像提交中(emoji 直选与上传共用,防重复提交) */
const avatarSaving = ref(false);

/** 选预设 emoji:立即提交生效 */
async function applyAvatar(emoji: string) {
  if (avatarSaving.value) return;
  avatarSaving.value = true;
  try {
    await auth.updateProfile({ avatar: emoji });
    uni.showToast({ title: '头像已更新', icon: 'none' });
    showAvatarSheet.value = false;
  } catch (err) {
    uni.showToast({ title: err instanceof Error ? err.message : '更新失败', icon: 'none' });
  } finally {
    avatarSaving.value = false;
  }
}

/**
 * 从相册选图上传自定义头像。取压缩档(头像展示无需原图,减小上传体积);
 * 用户取消选择(fail 回调)静默;格式/大小限制由后端校验并经 toast 提示。
 */
function chooseAndUpload() {
  if (avatarSaving.value) return;
  uni.chooseImage({
    count: 1,
    sizeType: ['compressed'],
    success: async (res) => {
      const path = res.tempFilePaths[0];
      if (!path || avatarSaving.value) return;
      avatarSaving.value = true;
      try {
        await auth.uploadAvatar(path);
        uni.showToast({ title: '头像已更新', icon: 'none' });
        showAvatarSheet.value = false;
      } catch (err) {
        uni.showToast({ title: err instanceof Error ? err.message : '上传失败', icon: 'none' });
      } finally {
        avatarSaving.value = false;
      }
    },
  });
}

// ===== 修改密码 =====
/** 密码长度约束(与后端 check_password 一致:4-64 位) */
const PASSWORD_MIN = 4;
const PASSWORD_MAX = 64;

/** 密码弹窗:低频操作收敛为入口 + 弹窗,打开时重置表单避免残留上次输入 */
const showPwdSheet = ref(false);
const pwdForm = ref({ oldPassword: '', newPassword: '', confirm: '' });
const pwdSaving = ref(false);

function openPwdSheet() {
  pwdForm.value = { oldPassword: '', newPassword: '', confirm: '' };
  showPwdSheet.value = true;
}

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
    showPwdSheet.value = false;
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
    <!-- 账号概览:大头像(带编辑角标)+ 昵称即时预览/账号 -->
    <view v-if="current" class="member-card">
      <view class="avatar-wrap" @click="showAvatarSheet = true">
        <view class="avatar-ring">
          <MemberAvatar :avatar="current.avatar" :size="96" />
        </view>
        <view class="avatar-edit">
          <text class="avatar-edit-ico">✏️</text>
        </view>
      </view>
      <view class="member-info">
        <text class="name">{{ profileForm.name.trim() || '未命名' }}</text>
        <text class="username">{{ current.username ? `账号 ${current.username}` : '未设置账号' }}</text>
      </view>
    </view>

    <!-- 账号信息:分组列表(label 左 / 值右,与系统设置页一致) -->
    <text class="group-title">账号信息</text>
    <view class="group">
      <view class="cell" @click="showAvatarSheet = true">
        <text class="cell-label">头像</text>
        <MemberAvatar class="cell-avatar" :avatar="current?.avatar || ''" :size="64" />
        <view class="chevron" />
      </view>
      <view class="cell">
        <text class="cell-label">昵称</text>
        <input
          v-model="profileForm.name"
          class="cell-field"
          type="text"
          placeholder="请输入昵称"
          placeholder-class="cell-placeholder"
          :maxlength="64"
        >
      </view>
      <view class="cell cell-static">
        <text class="cell-label">登录账号</text>
        <text class="cell-value">{{ current?.username || '未设置' }}</text>
      </view>
    </view>
    <view
      class="btn"
      :class="{ disabled: profileSaving || !profileDirty }"
      @click="saveProfile"
    >
      <text class="btn-text">{{ profileSaving ? '保存中…' : '保存昵称' }}</text>
    </view>

    <!-- 安全 -->
    <text class="group-title">安全</text>
    <view class="group">
      <view class="cell" @click="openPwdSheet">
        <text class="cell-label">修改密码</text>
        <view class="chevron" />
      </view>
    </view>

    <!-- 退出登录(危险操作,二次确认) -->
    <view class="logout-entry" @click="logout">
      <text class="logout-text">退出登录</text>
    </view>

    <view class="foot-tip">
      <text>收藏与播放记录按账号独立保存、多设备同步</text>
      <text>登录账号由管理员统一管理,如需更换请联系管理员</text>
    </view>

    <!-- 头像选择弹窗:上传自定义图或选预设 emoji,选完即时生效 -->
    <view v-if="showAvatarSheet" class="sheet-mask" @click="showAvatarSheet = false">
      <view class="sheet" @click.stop>
        <view class="sheet-bar" />
        <text class="sheet-title">选择头像</text>
        <!-- 自定义上传:选图即传,后端落盘并即时生效 -->
        <view class="upload-entry" @click="chooseAndUpload">
          <view class="upload-ico">
            <text class="upload-ico-text">🖼️</text>
          </view>
          <view class="upload-info">
            <text class="upload-title">上传自定义头像</text>
            <text class="upload-sub">从相册选择 · jpg/png/webp · 不超过 2MB</text>
          </view>
          <view class="chevron" />
        </view>
        <text class="grid-label">或选择预设头像</text>
        <view class="avatar-grid">
          <view
            v-for="a in AVATAR_CHOICES"
            :key="a"
            class="avatar-option"
            :class="{ active: a === current?.avatar }"
            @click="applyAvatar(a)"
          >
            <text class="avatar-option-text">{{ a }}</text>
          </view>
        </view>
        <view class="sheet-safe" />
      </view>
    </view>

    <!-- 修改密码弹窗:校验沿用原逻辑,成功后自动关闭 -->
    <view v-if="showPwdSheet" class="sheet-mask" @click="showPwdSheet = false">
      <view class="sheet" @click.stop>
        <view class="sheet-bar" />
        <text class="sheet-title">修改密码</text>
        <view class="pwd-form">
          <input
            v-model="pwdForm.oldPassword"
            class="pwd-field"
            :password="true"
            placeholder="旧密码"
            placeholder-class="pwd-placeholder"
          >
          <input
            v-model="pwdForm.newPassword"
            class="pwd-field"
            :password="true"
            :placeholder="`新密码(${PASSWORD_MIN}-${PASSWORD_MAX} 位)`"
            placeholder-class="pwd-placeholder"
          >
          <input
            v-model="pwdForm.confirm"
            class="pwd-field"
            :password="true"
            placeholder="再次输入新密码"
            placeholder-class="pwd-placeholder"
            confirm-type="done"
            @confirm="savePassword"
          >
        </view>
        <view class="sheet-btn" :class="{ disabled: pwdSaving }" @click="savePassword">
          <text class="sheet-btn-text">{{ pwdSaving ? '提交中…' : '确认修改' }}</text>
        </view>
        <view class="sheet-safe" />
      </view>
    </view>
  </view>
</template>

<style scoped lang="scss">
/* 底部安全区留白:H5 已验证;App/微信小程序 env() 同样支持,未真机复验 */
.page {
  min-height: 100vh;
  padding: 24rpx 24rpx calc(40rpx + env(safe-area-inset-bottom));
}
/* ===== 账号概览卡(与「我的」页头部同风格) ===== */
.member-card {
  display: flex;
  align-items: center;
  padding: 36rpx 32rpx;
  background: linear-gradient(135deg, $primary-light, $primary);
  border-radius: 28rpx;
  box-shadow: $shadow-card;
}
.avatar-wrap {
  position: relative;
  flex-shrink: 0;

  &:active .avatar-ring {
    opacity: 0.85;
  }
}
.avatar-ring {
  width: 112rpx;
  height: 112rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.22);
  box-shadow: 0 8rpx 24rpx rgba(0, 0, 0, 0.10); /* 头像柔光,与渐变卡分层 */
  display: flex;
  align-items: center;
  justify-content: center;
}
/* 编辑角标:提示头像可点击更换 */
.avatar-edit {
  position: absolute;
  right: -6rpx;
  bottom: -6rpx;
  width: 40rpx;
  height: 40rpx;
  border-radius: 50%;
  background: #ffffff;
  border: 2rpx solid $bg-page;
  box-shadow: 0 4rpx 10rpx rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
}
.avatar-edit-ico {
  font-size: 20rpx;
  line-height: 1;
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
/* ===== 分组列表(设置页风格) ===== */
.group-title {
  display: block;
  margin: 36rpx 12rpx 16rpx;
  font-size: 24rpx;
  color: $text-sub;
}
.group {
  background: $bg-card;
  border-radius: 28rpx;
  overflow: hidden;
  box-shadow: $shadow-card;
}
.cell {
  display: flex;
  align-items: center;
  padding: 24rpx 28rpx;

  &:active {
    background: $uni-bg-color-hover;
  }
  /* 只读行(登录账号)不给按压反馈,区分可交互行 */
  &.cell-static:active {
    background: transparent;
  }
  & + .cell {
    border-top: 1rpx solid $divider;
  }
}
.cell-label {
  font-size: 28rpx;
  color: $text-main;
}
.cell-value {
  margin-left: auto;
  font-size: 26rpx;
  color: $text-sub;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
/* 头像行右侧预览(尺寸/圆形由 MemberAvatar 组件负责,此处只管推到行尾) */
.cell-avatar {
  margin-left: auto;
}
.cell-field {
  flex: 1;
  margin-left: 32rpx;
  text-align: right;
  font-size: 28rpx;
  color: $text-main;
}
.cell-placeholder {
  color: $text-disable;
}
/* 保存按钮:有未保存改动才可用(dirty 检测见 script) */
.btn {
  margin-top: 24rpx;
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
    box-shadow: none;
  }
}
.btn-text {
  color: #ffffff;
  font-size: 30rpx;
  font-weight: bold;
}
/* ===== 退出登录 ===== */
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
/* ===== 底部说明 ===== */
.foot-tip {
  margin-top: 32rpx;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
  text-align: center;
  font-size: 22rpx;
  color: $text-disable;
}
/* ===== 底部弹窗(mask + 上滑面板) =====
   动画用 CSS 关键帧在插入时播放:小程序端不支持 <transition> 组件,关闭为即时收起 */
.sheet-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: $uni-bg-color-mask;
  z-index: 999;
  display: flex;
  align-items: flex-end;
  animation: sheet-fade 0.2s ease;
}
.sheet {
  width: 100%;
  background: $bg-card;
  border-radius: 32rpx 32rpx 0 0;
  padding: 16rpx 40rpx 0;
  animation: sheet-up 0.25s ease;
}
.sheet-bar {
  width: 72rpx;
  height: 8rpx;
  border-radius: 999rpx;
  background: $divider;
  margin: 8rpx auto 0;
}
.sheet-title {
  display: block;
  margin-top: 24rpx;
  text-align: center;
  font-size: 30rpx;
  font-weight: bold;
  color: $text-main;
}
/* 弹窗底部安全区留白(同 .page 注释) */
.sheet-safe {
  height: calc(24rpx + env(safe-area-inset-bottom));
}
/* 自定义上传入口(弹窗顶部) */
.upload-entry {
  margin-top: 28rpx;
  display: flex;
  align-items: center;
  padding: 20rpx 24rpx;
  background: $bg-page;
  border-radius: 20rpx;

  &:active {
    opacity: 0.8;
  }
}
.upload-ico {
  width: 64rpx;
  height: 64rpx;
  border-radius: 16rpx;
  background: $primary-soft;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.upload-ico-text {
  font-size: 32rpx;
}
.upload-info {
  flex: 1;
  min-width: 0;
  margin-left: 20rpx;
  display: flex;
  flex-direction: column;
}
.upload-title {
  font-size: 28rpx;
  color: $text-main;
}
.upload-sub {
  margin-top: 6rpx;
  font-size: 22rpx;
  color: $text-disable;
}
.grid-label {
  display: block;
  margin: 28rpx 4rpx 0;
  font-size: 22rpx;
  color: $text-sub;
}
/* 头像网格(5 列) */
.avatar-grid {
  margin-top: 20rpx;
  margin-right: -24rpx; /* 抵消末列多余间距,保持网格对齐 */
  display: flex;
  flex-wrap: wrap;
}
.avatar-option {
  width: 104rpx;
  height: 104rpx;
  margin: 0 24rpx 24rpx 0;
  border: 2rpx solid transparent;
  border-radius: 24rpx;
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
  font-size: 48rpx;
}
/* 密码表单 */
.pwd-form {
  margin-top: 32rpx;
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}
.pwd-field {
  padding: 24rpx 28rpx;
  background: $bg-page;
  border-radius: 16rpx;
  font-size: 28rpx;
  color: $text-main;
}
.pwd-placeholder {
  color: $text-disable;
}
.sheet-btn {
  margin-top: 32rpx;
  height: 88rpx;
  background: linear-gradient(135deg, $primary-light, $primary);
  border-radius: 999rpx;
  display: flex;
  align-items: center;
  justify-content: center;

  &:active {
    opacity: 0.85;
  }
  &.disabled {
    opacity: 0.5;
  }
}
.sheet-btn-text {
  color: #ffffff;
  font-size: 30rpx;
  font-weight: bold;
}
/* ===== 通用箭头(CSS 绘制,与「我的」页同款) ===== */
.chevron {
  width: 16rpx;
  height: 16rpx;
  border-right: 3rpx solid $text-disable;
  border-bottom: 3rpx solid $text-disable;
  transform: rotate(-45deg);
  flex-shrink: 0;
  margin-left: 16rpx;
}
@keyframes sheet-fade {
  from {
    opacity: 0;
  }
}
@keyframes sheet-up {
  from {
    transform: translateY(100%);
  }
}
</style>
