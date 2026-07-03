/**
 * 统一音频控制器:抹平 backgroundAudioManager(App/小程序)与 innerAudioContext(H5)的平台差异。
 *
 * 背景(见 CLAUDE.md 第 4 节):主播放统一收敛到单一管理器,后台/锁屏能力仅 App/小程序具备。
 * - App / 微信小程序:用 uni.getBackgroundAudioManager(),支持后台播放、锁屏控制、系统通知栏
 *   (title / singer / coverImgUrl 驱动锁屏 / 通知栏显示)。
 * - H5:无 backgroundAudioManager(该 API 不实现),降级为 uni.createInnerAudioContext()
 *   (底层同为 HTMLAudioElement);H5 本就没有「后台 / 锁屏 / 系统通知栏」概念,通知栏元数据自动忽略。
 *
 * 消费方(player store)只依赖本接口,不感知平台差异。
 */

/** 统一音频控制器契约:取两者公共能力,叠加一个平台无关的 setMeta */
export interface AudioManager {
  /** 音频源(设置后配合 play 起播) */
  src: string;
  /** 倍速 */
  playbackRate: number;
  /** 时长,单位秒(只读,加载后有效) */
  readonly duration: number;
  /** 当前播放位置,单位秒(只读) */
  readonly currentTime: number;
  /** 播放 / 暂停 / 跳转 */
  play(): void;
  pause(): void;
  seek(sec: number): void;
  /** 事件回调注册(消费方控制注册时机,通常仅绑一次) */
  onPlay(cb: () => void): void;
  onPause(cb: () => void): void;
  onStop(cb: () => void): void;
  onCanplay(cb: () => void): void;
  onTimeUpdate(cb: () => void): void;
  onEnded(cb: () => void): void;
  onWaiting(cb: () => void): void;
  onError(cb: (err: unknown) => void): void;
  /**
   * 设置系统通知栏元数据(标题 / 作者 / 封面)。
   * 仅 App / 小程序背景音频生效(驱动锁屏 / 通知栏显示);H5 无此能力,自动忽略。
   */
  setMeta(meta: { title: string; singer: string; cover: string }): void;
}

/** 创建当前平台的音频控制器 */
export function createAudioManager(): AudioManager {
  // #ifdef H5
  const ctx = uni.createInnerAudioContext();
  return {
    get src() { return ctx.src; },
    set src(v: string) { ctx.src = v; },
    get playbackRate() { return ctx.playbackRate ?? 1; },
    set playbackRate(v: number) { ctx.playbackRate = v; },
    get duration() { return ctx.duration ?? 0; },
    get currentTime() { return ctx.currentTime ?? 0; },
    play: () => ctx.play(),
    pause: () => ctx.pause(),
    seek: (sec: number) => ctx.seek(sec),
    onPlay: (cb) => ctx.onPlay(cb),
    onPause: (cb) => ctx.onPause(cb),
    onStop: (cb) => ctx.onStop(cb),
    onCanplay: (cb) => ctx.onCanplay(cb),
    onTimeUpdate: (cb) => ctx.onTimeUpdate(cb),
    onEnded: (cb) => ctx.onEnded(cb),
    onWaiting: (cb) => ctx.onWaiting(cb),
    onError: (cb) => ctx.onError(cb),
    // H5 无系统通知栏 / 锁屏,元数据忽略
    setMeta: () => { /* no-op */ },
  };
  // #endif

  // #ifdef APP-PLUS || MP-WEIXIN
  const m = uni.getBackgroundAudioManager();

  /**
   * 原生资源路径归一化:backgroundAudioManager 是原生播放器,不会自动解析项目相对路径
   * /static/...(那是 webview 的约定)。App 端需转成 _www 下绝对路径,否则触发 onError
   * (errCode -5,无法打开数据源)。网络地址 / 协议路径 / 小程序端原样返回。
   */
  const norm = (u: string): string => {
    if (!u) return u;
    // #ifdef APP-PLUS
    if (/^(https?:|file:|wtfile:|_www)/.test(u)) return u;
    if (u.startsWith('/static/') || u.startsWith('static/')) {
      const rel = u.replace(/^\/+/, '');
      const conv = (globalThis as {
        plus?: { io?: { convertLocalFileSystemURL?: (p: string) => string } };
      }).plus?.io?.convertLocalFileSystemURL;
      if (conv) {
        try { return conv(`_www/${rel}`); } catch { /* 转换失败降级为 _www 相对路径 */ }
      }
      return `_www/${rel}`;
    }
    // #endif
    return u;
  };

  return {
    get src() { return m.src; },
    set src(v: string) { m.src = norm(v); },
    get playbackRate() { return m.playbackRate ?? 1; },
    set playbackRate(v: number) { m.playbackRate = v; },
    get duration() { return m.duration ?? 0; },
    get currentTime() { return m.currentTime ?? 0; },
    play: () => m.play(),
    pause: () => m.pause(),
    seek: (sec: number) => m.seek(sec),
    onPlay: (cb) => m.onPlay(cb),
    onPause: (cb) => m.onPause(cb),
    onStop: (cb) => m.onStop(cb),
    onCanplay: (cb) => m.onCanplay(cb),
    onTimeUpdate: (cb) => m.onTimeUpdate(cb),
    onEnded: (cb) => m.onEnded(cb),
    onWaiting: (cb) => m.onWaiting(cb),
    onError: (cb) => m.onError(cb),
    setMeta: ({ title, singer, cover }) => {
      m.title = title;
      m.singer = singer;
      m.coverImgUrl = norm(cover);
    },
  };
  // #endif
}
