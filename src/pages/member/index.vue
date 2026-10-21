<script setup lang="ts">
import { ref } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import { storeToRefs } from 'pinia';
import { useMemberStore } from '@/store/member';
import { useAuthStore } from '@/store/auth';
import { currentMember, MEMBER_AVATARS, type MemberInfo } from '@/store/memberPrefs';

/**
 * 成员账号管理:列出全部账号、创建新账号、长按删除。
 * 切换账号不在这里 —— 退出登录后用对应账号重新登录即可。
 */

const memberStore = useMemberStore();
const auth = useAuthStore();
const { members } = storeToRefs(memberStore);
const current = currentMember;

/** 是否处于「添加账号」展开态 */
const adding = ref(false);
const newUsername = ref('');
const newPassword = ref('');
const newName = ref('');
const newAvatar = ref<string>(MEMBER_AVATARS[0]);
const submitting = ref(false);

// 每次进入页面刷新列表(其他端可能增删过)
onShow(() => {
  void memberStore.refresh().catch(() => {
    uni.showToast({ title: '获取账号列表失败,请检查网络', icon: 'none' });
  });
});

/** 创建成员账号(创建后不切换,各账号用各自密码登录) */
async function addMember() {
  const user = newUsername.value.trim();
  const pass = newPassword.value;
  const name = newName.value.trim();
  if (!user || !pass || !name) {
    uni.showToast({ title: '请填写账号、密码和昵称', icon: 'none' });
    return;
  }
  if (pass.length < 4) {
    uni.showToast({ title: '密码至少 4 位', icon: 'none' });
    return;
  }
  if (submitting.value) return;
  submitting.value = true;
  try {
    await memberStore.create(user, pass, name, newAvatar.value);
    newUsername.value = '';
    newPassword.value = '';
    newName.value = '';
    adding.value = false;
    uni.showToast({ title: '已创建,该成员可登录了', icon: 'none' });
  } catch (err) {
    const code = (err as { statusCode?: number }).statusCode;
    const msg = code === 409
      ? '该账号已被使用'
      : code === 400
        ? '账号格式不符(2-24 位字母/数字/下划线/中文)'
        : '创建失败,请检查网络';
    uni.showToast({ title: msg, icon: 'none' });
  } finally {
    submitting.value = false;
  }
}

/** 长按删除账号(连同其云端收藏/历史;当前登录账号由后端拒绝) */
function removeMember(member: MemberInfo) {
  if (current.value?.id === member.id) {
    uni.showToast({ title: '不能删除当前登录的账号', icon: 'none' });
    return;
  }
  uni.showModal({
    title: `删除「${member.name}」?`,
    content: '该账号的收藏与播放记录将一并删除,不可恢复',
    confirmColor: '#e64340',
    success: (res) => {
      if (res.confirm) void memberStore.remove(member.id).catch(() => {
        uni.showToast({ title: '删除失败,请重试', icon: 'none' });
      });
    },
  });
}

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
    <view class="tip">
      <text>每个成员一个账号,收藏和播放记录各自独立、多设备同步</text>
    </view>

    <view class="member-list">
      <view
        v-for="m in members"
        :key="m.id"
        class="member-row"
        :class="{ active: current?.id === m.id }"
        @longpress="removeMember(m)"
      >
        <text class="avatar">{{ m.avatar || '⭐' }}</text>
        <view class="member-info">
          <text class="name">{{ m.name }}</text>
          <text class="username">账号:{{ m.username || '未设置' }}</text>
        </view>
        <text v-if="current?.id === m.id" class="check">当前</text>
      </view>

      <view v-if="members.length === 0" class="empty">
        <text>还没有成员账号</text>
      </view>
    </view>

    <!-- 添加账号 -->
    <view v-if="!adding" class="add-entry" @click="adding = true">
      <text class="avatar add-icon">＋</text>
      <text class="name">添加成员账号</text>
    </view>
    <view v-else class="add-form">
      <view class="avatar-picker">
        <text
          v-for="a in MEMBER_AVATARS"
          :key="a"
          class="avatar-option"
          :class="{ picked: newAvatar === a }"
          @click="newAvatar = a"
        >{{ a }}</text>
      </view>
      <input
        v-model="newUsername"
        class="field"
        :maxlength="24"
        placeholder="登录账号(字母/数字/下划线/中文)"
      />
      <input
        v-model="newPassword"
        class="field"
        :maxlength="64"
        :password="true"
        placeholder="登录密码(至少 4 位)"
      />
      <input
        v-model="newName"
        class="field"
        :maxlength="12"
        placeholder="昵称(如:爸爸 / 老大)"
        confirm-type="done"
        @confirm="addMember"
      />
      <view class="form-actions">
        <button class="btn ghost" size="mini" @click="adding = false">取消</button>
        <button class="btn primary" size="mini" :disabled="submitting" @click="addMember">创建账号</button>
      </view>
    </view>

    <view class="logout-entry" @click="logout">
      <text class="logout-text">退出登录</text>
    </view>

    <view class="foot-tip">
      <text>长按账号可删除 · 切换账号请退出后重新登录</text>
    </view>
  </view>
</template>

<style scoped lang="scss">
.page {
  min-height: 100vh;
  padding: 24rpx 16rpx;
}
.tip {
  padding: 0 8rpx 20rpx;
  font-size: 24rpx;
  color: $text-sub;
}
.member-list {
  background: $bg-card;
  border-radius: 16rpx;
  overflow: hidden;
  box-shadow: $shadow-card;
}
.member-row {
  display: flex;
  align-items: center;
  padding: 24rpx;

  &:active {
    background: $uni-bg-color-hover;
  }
  &.active .name {
    color: #ff8c42;
    font-weight: bold;
  }
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
.empty {
  padding: 48rpx 24rpx;
  text-align: center;
  font-size: 26rpx;
  color: $text-sub;
}
.add-entry {
  margin-top: 24rpx;
  display: flex;
  align-items: center;
  padding: 28rpx 24rpx;
  background: $bg-card;
  border-radius: 16rpx;
  box-shadow: $shadow-card;

  &:active {
    background: $uni-bg-color-hover;
  }
}
.add-icon {
  color: #ff8c42;
  font-weight: bold;
}
.add-form {
  margin-top: 24rpx;
  padding: 24rpx;
  background: $bg-card;
  border-radius: 16rpx;
  box-shadow: $shadow-card;
}
.avatar-picker {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}
.avatar-option {
  width: 88rpx;
  height: 88rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 44rpx;
  border-radius: 50%;
  background: $bg-page;

  &.picked {
    background: rgba(255, 140, 66, 0.18);
    box-shadow: 0 0 0 3rpx #ff8c42;
  }
}
.field {
  margin-top: 20rpx;
  padding: 20rpx 24rpx;
  background: $bg-page;
  border-radius: 12rpx;
  font-size: 28rpx;
}
.form-actions {
  margin-top: 24rpx;
  display: flex;
  justify-content: flex-end;
  gap: 20rpx;
}
.btn.primary {
  background: #ff8c42;
  color: #ffffff;
}
.btn.ghost {
  background: transparent;
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
