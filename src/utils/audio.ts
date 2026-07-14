/**
 * 统一音频控制器:抹平 backgroundAudioManager(App/小程序)与 innerAudioContext(H5)的平台差异。
 *
 * 背景(见 CLAUDE.md 第 4 节):主播放统一收敛到单一管理器,后台/锁屏能力仅 App/小程序具备。
 * - App / 微信小程序:用 uni.getBackgroundAudioManager(),支持后台播放、锁屏控制、系统通知栏
 *   (title / singer / coverImgUrl 驱动锁屏 / 通知栏显示)。
 * - H5:无 backgroundAudioManager(该 API 不实现),降级为 uni.createInnerAudioContext()
 *   (底层同为 HTMLAudioElement);H5 本就没有「后台 / 锁屏 / 系统通知栏」概念,通知栏元数据自动忽略。
 *
 * App 端本地音频的可播放性(打包后关键):正式包的 _www 资源打包在 apk 内未解压,原生播放器
 * (MediaPlayer)无法直接读取;调试基座因资源解压在真实文件系统才能播。故 App 端通过
 * resolvePlayableSrc 把 _www 下音频复制到 _doc(应用专属可读写真实文件目录),再用绝对路径
 * 喂给播放器。消费方(player store)在装载前 await resolvePlayableSrc,只依赖本接口、不感知平台差异。
 */

// #ifdef APP-PLUS
/** plus.io 文件操作所需的最小类型(Entry 仅声明用到的 getDirectory / copyTo) */
type PlusEntry = {
  getDirectory: (
    name: string,
    opt: { create: boolean; exclusive: boolean },
    ok: (entry: PlusEntry) => void,
    fail: (e: unknown) => void,
  ) => void;
  copyTo: (
    parent: PlusEntry,
    newName: string,
    ok: () => void,
    fail: (e: unknown) => void,
  ) => void;
};
type PlusIo = {
  resolveLocalFileSystemURL: (
    url: string,
    ok: (entry: PlusEntry) => void,
    fail: (e: unknown) => void,
  ) => void;
  convertLocalFileSystemURL?: (p: string) => string;
};
const getPlusIo = (): PlusIo | undefined =>
  (globalThis as { plus?: { io?: PlusIo } }).plus?.io;

/** 运行时缓存:已复制到 _doc 的文件,避免重复磁盘 IO(单曲循环 / 重播直接命中) */
const docCached = new Set<string>();

/** convertLocalFileSystemURL 安全包装;plus.io 不可用或异常时原样返回 */
const toAbs = (p: string): string => {
  const conv = getPlusIo()?.convertLocalFileSystemURL;
  try { return conv ? conv(p) : p; } catch { return p; }
};

/** 路径是否存在(resolveLocalFileSystemURL 成功即存在;plus.io 不可用判否) */
const pathExists = (path: string): Promise<boolean> =>
  new Promise((resolve) => {
    const io = getPlusIo();
    if (!io) return resolve(false);
    io.resolveLocalFileSystemURL(path, () => resolve(true), () => resolve(false));
  });

/** 确保 _doc 下某目录存在,从 _doc 逐级创建。path 形如 _doc/static/library/.../classic */
const ensureDocDir = (path: string): Promise<void> =>
  new Promise((resolve, reject) => {
    const io = getPlusIo();
    if (!io) return reject(new Error('plus.io 不可用'));
    io.resolveLocalFileSystemURL('_doc', (docEntry) => {
      const parts = path.replace(/^_doc\//, '').split('/').filter(Boolean);
      let cur = docEntry;
      let i = 0;
      const next = () => {
        if (i >= parts.length) { resolve(); return; }
        cur.getDirectory(
          parts[i],
          { create: true, exclusive: false },
          (e) => { cur = e; i += 1; next(); },
          (err) => reject(err),
        );
      };
      next();
    }, (err) => reject(err));
  });

/** 复制 srcPath 到 dstPath(均含 _www / _doc 前缀的相对路径) */
const copyIntoDoc = (srcPath: string, dstPath: string): Promise<void> =>
  new Promise((resolve, reject) => {
    const io = getPlusIo();
    if (!io) return reject(new Error('plus.io 不可用'));
    io.resolveLocalFileSystemURL(srcPath, (srcEntry) => {
      const dir = dstPath.slice(0, dstPath.lastIndexOf('/'));
      const name = dstPath.slice(dstPath.lastIndexOf('/') + 1);
      io.resolveLocalFileSystemURL(dir, (dirEntry) => {
        srcEntry.copyTo(dirEntry, name, () => resolve(), (err) => reject(err));
      }, (err) => reject(err));
    }, (err) => reject(err));
  });

/**
 * 把 _www 下本地音频复制到 _doc,返回 _doc 绝对路径供原生播放器读取。
 * 幂等:运行时缓存或磁盘已存在则跳过复制。非本地资源(网络 / 协议 / 非 static)原样返回。
 */
const toPlayable = async (url: string): Promise<string> => {
  if (!url || /^(https?:|file:|wtfile:|_doc)/.test(url)) return url;
  if (!url.startsWith('/static/') && !url.startsWith('static/')) return url;
  const rel = url.replace(/^\/+/, '');               // static/library/.../x.mp3
  const dstPath = `_doc/${rel}`;
  if (!docCached.has(dstPath)) {
    if (!(await pathExists(dstPath))) {
      await ensureDocDir(dstPath.slice(0, dstPath.lastIndexOf('/')));
      await copyIntoDoc(`_www/${rel}`, dstPath);
    }
    docCached.add(dstPath);
  }
  return toAbs(dstPath);
};
// #endif

/** 统一音频控制器契约:取两者公共能力,叠加平台无关的 setMeta / resolvePlayableSrc */
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
  /**
   * 把音频源解析为当前平台可直接播放的真实路径(异步)。
   * App 端:把 _www 下本地音频复制到 _doc 并返回绝对路径(正式包 apk 内 _www 资源原生播放器无法直读)。
   * H5 / 小程序:原样返回(平台自身可解析相对路径)。
   * 消费方在装载前 await,再把结果赋给 src。
   */
  resolvePlayableSrc(url: string): Promise<string>;
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
    // H5 webview 自身可解析 /static 相对路径,无需转换
    resolvePlayableSrc: (u: string) => Promise.resolve(u),
  };
  // #endif

  // #ifdef APP-PLUS || MP-WEIXIN
  const m = uni.getBackgroundAudioManager();

  /**
   * 封面路径归一化(同步):backgroundAudioManager 是原生播放器,不会自动解析 /static/...。
   * 仅做 convertLocalFileSystemURL 转换(封面图小,不复制);网络 / 协议 / 小程序原样返回。
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
    resolvePlayableSrc: (u: string) => {
      // #ifdef APP-PLUS
      return toPlayable(u);
      // #endif
      // #ifndef APP-PLUS
      return Promise.resolve(u); // 小程序不在目标端,原样返回
      // #endif
    },
  };
  // #endif
}
