import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { Song } from '@/types/song';
import { PlayMode } from '@/types/song';
import { getRepository } from '@/repository';
import { useHistoryStore } from '@/store/history';
import { createAudioManager } from '@/utils/audio';
import type { AudioManager } from '@/utils/audio';

/**
 * 播放器 store —— 全应用播放逻辑的单一数据源。
 *
 * 约定(见 CLAUDE.md 第 4 节):
 * - 通过 AudioManager(@/utils/audio)收敛底层播放器:App/小程序用 backgroundAudioManager
 *   (支持后台播放、锁屏控制、系统通知栏),H5 无该 API,降级为 innerAudioContext;
 * - 修改 title / singer / coverImgUrl / src 通过 loadSong 集中处理(setMeta + src);
 * - 监听器只绑定一次,避免重复回调;
 * - 进度跳转用 seek,UI 进度条拖动需自行节流(≥250ms)。
 *
 * 数据访问:歌曲信息通过 Repository(getRepository)异步获取,不直接 import 曲库数组,
 * 以便未来从「静态数组」平滑切换到「JSON / SQLite」数据源。
 *
 * 增强功能:播放错误提示、倍速播放、定时关闭(哄睡)、记录播放历史。
 */

/** 音频控制器(模块级单例;H5 为 innerAudioContext,App/小程序为背景音频管理器) */
let manager: AudioManager | null = null;
/** 监听器是否已绑定,避免重复绑定导致多次回调 */
let listenersBound = false;
/** 定时器句柄(模块级,避免重复绑定丢失) */
let timerId: ReturnType<typeof setInterval> | null = null;
/** 曲库数据源(模块级单例,统一歌曲查询入口) */
const repo = getRepository();
/** 加载序号:每次发起切歌自增,用于丢弃被取代的异步 getDetail 结果(防竞态) */
let loadSeq = 0;

/** 获取/创建音频控制器单例(平台差异收敛在 createAudioManager 内) */
function getManager(): AudioManager {
  if (!manager) manager = createAudioManager();
  return manager;
}

/** 可选倍速档位 */
const PLAYBACK_RATES = [0.75, 1, 1.25];

export const usePlayerStore = defineStore('player', () => {
  const useHistory = useHistoryStore();

  // ===== 状态 =====
  const playlist = ref<string[]>([]);
  const currentIndex = ref(-1);
  const currentSong = ref<Song | null>(null);
  const isPlaying = ref(false);
  const isLoading = ref(false);
  const duration = ref(0);
  const currentTime = ref(0);
  const playMode = ref<PlayMode>(PlayMode.SEQUENCE);
  /** 播放错误信息(null 表示无错误) */
  const error = ref<string | null>(null);
  /** 当前倍速 */
  const playbackRate = ref<number>(1);
  /** 定时关闭:设定的分钟数(0 表示未设定) */
  const timerMinutes = ref(0);
  /** 定时关闭:剩余秒数 */
  const timerRemaining = ref(0);

  // ===== 计算属性 =====
  const hasCurrent = computed(() => currentSong.value !== null);
  /** 定时是否生效中 */
  const timerActive = computed(() => timerRemaining.value > 0);

  /** 绑定全局监听器(仅绑定一次) */
  function bindListeners() {
    if (listenersBound) return;
    const m = getManager();

    m.onPlay(() => {
      isPlaying.value = true;
      isLoading.value = false;
      error.value = null;
      if (m.duration) duration.value = m.duration;
    });
    m.onPause(() => { isPlaying.value = false; });
    m.onStop(() => { isPlaying.value = false; });
    m.onCanplay(() => {
      isLoading.value = false;
      if (m.duration) duration.value = m.duration;
    });
    m.onTimeUpdate(() => {
      currentTime.value = m.currentTime || 0;
      if (m.duration) duration.value = m.duration;
    });
    m.onEnded(() => { handleEnded(); });
    m.onWaiting(() => { isLoading.value = true; });
    m.onError((err: unknown) => {
      console.error('音频播放出错:', err);
      error.value = '音频加载失败,请检查音频资源是否已放入 static/audio/';
      isLoading.value = false;
      isPlaying.value = false;
    });

    listenersBound = true;
  }

  /** 装载某首歌到控制器(设置元数据 + src 并触发播放) */
  function loadSong(song: Song) {
    const m = getManager();
    m.setMeta({ title: song.name, singer: song.artist, cover: song.cover });
    m.src = song.src;
    m.playbackRate = playbackRate.value; // 切歌后保持当前倍速
    currentSong.value = song;
    currentTime.value = 0;
    isLoading.value = true;
    error.value = null;
    // 记录播放历史(最近播放 / 继续听)
    useHistory.add(song.id);
    // 显式触发播放:innerAudioContext / H5 端设 src 不会自动起播,需手动 play
    m.play();
  }

  /** 播放结束:依据播放模式决定下一步 */
  function handleEnded() {
    switch (playMode.value) {
      case PlayMode.LOOP_ONE:
        // 单曲循环重播:已有 detail,直接装载;递增 loadSeq 使任何 pending 的旧请求失效
        if (currentSong.value) { loadSeq++; loadSong(currentSong.value); }
        break;
      case PlayMode.RANDOM:
        playRandom();
        break;
      case PlayMode.SEQUENCE:
      default:
        playNext(true);
        break;
    }
  }

  /**
   * 切到队列指定索引并播放(内部方法,异步)。
   * 通过 repo.getDetail 取完整歌曲信息后再装载。loadSeq 防竞态:
   * 快速切歌时,被取代的旧请求完成后会被丢弃,避免覆盖最新状态。
   */
  async function playAtIndex(index: number) {
    const len = playlist.value.length;
    if (len === 0 || index < 0 || index >= len) return;
    currentIndex.value = index;
    const seq = ++loadSeq;
    const song = await repo.getDetail(playlist.value[index]);
    if (seq !== loadSeq) return; // 已被更新的切歌取代,丢弃本次结果
    if (song) loadSong(song);
  }

  /**
   * 播放指定歌曲,并以 list 作为播放队列。
   * @param id 要播放的歌曲 id
   * @param list 播放队列(id 数组);id 不在队列中时会置顶并入队
   */
  function playSong(id: string, list: string[]) {
    bindListeners();
    playlist.value = [...list];
    let idx = playlist.value.indexOf(id);
    if (idx < 0) {
      playlist.value.unshift(id);
      idx = 0;
    }
    void playAtIndex(idx);
  }

  /** 播放整个队列,从 startIndex 开始 */
  function playList(list: string[], startIndex = 0) {
    bindListeners();
    if (list.length === 0) return;
    playlist.value = [...list];
    const index = Math.min(Math.max(startIndex, 0), list.length - 1);
    void playAtIndex(index);
  }

  function play() {
    const m = getManager();
    if (currentSong.value && !m.src) {
      loadSong(currentSong.value);
      return;
    }
    m.play();
  }
  function pause() { getManager().pause(); }
  function togglePlay() { isPlaying.value ? pause() : play(); }

  function playPrev() {
    if (playlist.value.length === 0) return;
    bindListeners();
    if (playMode.value === PlayMode.RANDOM) { playRandom(); return; }
    let index = currentIndex.value - 1;
    if (index < 0) index = playlist.value.length - 1;
    void playAtIndex(index);
  }
  function playNext(isAuto = false) {
    if (playlist.value.length === 0) return;
    bindListeners();
    if (playMode.value === PlayMode.RANDOM) { playRandom(); return; }
    let index = currentIndex.value + 1;
    if (index >= playlist.value.length) {
      if (isAuto) { isPlaying.value = false; return; }
      index = 0;
    }
    void playAtIndex(index);
  }
  function playRandom() {
    const len = playlist.value.length;
    if (len === 0) return;
    if (len === 1) { void playAtIndex(0); return; }
    let index = currentIndex.value;
    while (index === currentIndex.value) {
      index = Math.floor(Math.random() * len);
    }
    void playAtIndex(index);
  }

  function togglePlayMode() {
    const order: PlayMode[] = [PlayMode.SEQUENCE, PlayMode.LOOP_ONE, PlayMode.RANDOM];
    const cur = order.indexOf(playMode.value);
    playMode.value = order[(cur + 1) % order.length];
  }

  function seek(sec: number) {
    getManager().seek(sec);
    currentTime.value = sec;
  }

  // ===== 倍速 =====
  function setPlaybackRate(rate: number) {
    playbackRate.value = rate;
    getManager().playbackRate = rate;
  }
  /** 循环切换倍速:0.75 → 1 → 1.25 → 0.75 */
  function cyclePlaybackRate() {
    const idx = PLAYBACK_RATES.indexOf(playbackRate.value);
    const next = PLAYBACK_RATES[(idx + 1) % PLAYBACK_RATES.length];
    setPlaybackRate(next);
  }

  // ===== 定时关闭(哄睡)=====
  /** 开启定时关闭(到点自动暂停) */
  function startTimer(minutes: number) {
    cancelTimer();
    timerMinutes.value = minutes;
    timerRemaining.value = minutes * 60;
    timerId = setInterval(() => {
      if (timerRemaining.value <= 1) {
        pause();
        cancelTimer();
        uni.showToast({ title: '定时关闭,已停止播放', icon: 'none' });
        return;
      }
      timerRemaining.value -= 1;
    }, 1000);
  }
  /** 取消定时 */
  function cancelTimer() {
    if (timerId) { clearInterval(timerId); timerId = null; }
    timerRemaining.value = 0;
    timerMinutes.value = 0;
  }

  function init() { bindListeners(); }

  return {
    // 状态
    playlist, currentIndex, currentSong, isPlaying, isLoading,
    duration, currentTime, playMode, error, playbackRate,
    timerMinutes, timerRemaining, timerActive, hasCurrent,
    // actions
    init, playSong, playList, play, pause, togglePlay,
    playPrev, playNext, togglePlayMode, seek,
    setPlaybackRate, cyclePlaybackRate, startTimer, cancelTimer,
  };
});
