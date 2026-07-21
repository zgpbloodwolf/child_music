/**
 * App 整包更新(APK 下载安装):仅 Android 端真正生效。
 *
 * 设计要点(见 CLAUDE.md 第 4、6 节):
 * - plus.runtime / plus.downloader 仅 App 端存在,全部用 #ifdef APP-PLUS 包裹;
 *   H5 / 小程序编译期被剔除为 no-op,导入本模块调用 checkAppUpdate 即静默返回。
 * - iOS 虽属 APP-PLUS,但整包侧载不可行:运行时按 uni.getSystemInfoSync().platform
 *   判定,仅弹窗提示「请通过应用商店更新」,不触发下载。
 * - plus API 用 (globalThis as { plus?: {...} }).plus?.xxx 安全取值 + 内联最小类型,
 *   不依赖外部 @types(沿用 src/utils/audio.ts 的范式)。
 * - 不引入 store:线性流程无共享状态,仅用 uni.setStorageSync 存「跳过的版本号」
 *   与「上次检查时间戳」(范式见 src/store/library.ts)。
 * - 所有失败均不阻断应用启动:自动检查静默,手动检查(我的页入口)给 toast 反馈。
 */
import { request, RequestError } from '@/utils/request';
import type { VersionInfo } from '@/types/version';

/** 本地 storage key:用户点「稍后」跳过的版本号(versionCode) */
const SKIPPED_VERSION_KEY = 'update_skipped_version';
/** 本地 storage key:上次自动检查的时间戳(ms) */
const LAST_CHECK_KEY = 'update_last_check_ts';
/** 自动检查最小间隔(ms),默认 24 小时,避免每次启动都打扰用户 */
const AUTO_CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000;

/** 防重入标志:避免启动自动检查与「我的」页手动检查并发触发 */
let isChecking = false;

/**
 * versionCode 数值比对:返回 latest - current,正数表示有新版本。
 * 入参若非有限数(NaN 等)兜底为 0,宁可漏更新也不抛异常阻断流程。
 */
export function compareVersionCode(current: number, latest: number): number {
  const a = Number.isFinite(current) ? current : 0;
  const b = Number.isFinite(latest) ? latest : 0;
  return b - a;
}

/** 拉取最新版本信息(复用统一请求封装,返回裸 VersionInfo) */
function fetchLatestVersion(): Promise<VersionInfo> {
  return request<VersionInfo>({ url: '/api/version/latest', method: 'GET', timeout: 8000 });
}

// #ifdef APP-PLUS
/** plus.runtime 最小类型(仅声明本模块用到的成员) */
interface PlusRuntimeProperty {
  /** 当前 APK 的 versionCode(字符串,如 "100",与 manifest.json 一致) */
  versionCode: string;
}
interface PlusRuntime {
  /** 读取当前应用信息(含 versionCode) */
  getProperty: (cb: (info: PlusRuntimeProperty) => void) => void;
  /** 安装本地 APK:force=false 走系统安装器 UI */
  install: (
    path: string,
    options: { force: boolean },
    successCb: () => void,
    failedCb: (e: unknown) => void,
  ) => void;
}

/** plus.downloader 最小类型 */
interface PlusDownloadTask {
  state: 'connected' | 'downloading' | 'success' | 'failed';
  downloadedSize: number;
  totalSize: number;
  /** 下载完成后的本地文件路径 */
  filename: string;
  /** 监听下载状态变化(用于刷新进度) */
  addEventListener: (type: 'stateChanged', cb: (task: PlusDownloadTask, status: number) => void) => void;
  /** 开始下载 */
  start: () => void;
}
interface PlusDownloader {
  createDownload: (
    url: string,
    options: { filename?: string },
    completedCb?: (task: PlusDownloadTask, status: number) => void,
  ) => PlusDownloadTask;
}

interface PlusRoot {
  runtime?: PlusRuntime;
  downloader?: PlusDownloader;
}

/** 安全取得 globalThis.plus(运行时可能未注入) */
function getPlus(): PlusRoot | undefined {
  return (globalThis as { plus?: PlusRoot }).plus;
}

/** 读取本地 versionCode(同步;失败回退 0)。
 * 用 uni.getSystemInfoSync().appVersionCode,而非 plus.runtime.getProperty(appid, cb):
 * 后者为异步回调,缺 appid 或回调不触发会卡住整个流程;同步 API 更稳。 */
function readLocalVersionCode(): number {
  try {
    const info = uni.getSystemInfoSync() as { appVersionCode?: unknown };
    return Number(info.appVersionCode) || 0;
  } catch {
    return 0;
  }
}

/** 读取用户已跳过的版本号(versionCode),0 表示未跳过 */
function readSkippedVersion(): number {
  try {
    return Number(uni.getStorageSync(SKIPPED_VERSION_KEY)) || 0;
  } catch {
    return 0;
  }
}

/** 记录用户跳过的版本号 */
function writeSkippedVersion(code: number): void {
  try {
    uni.setStorageSync(SKIPPED_VERSION_KEY, code);
  } catch {
    /* 忽略写入失败,不影响主流程 */
  }
}

/** 读取上次自动检查时间戳(ms),0 表示从未检查 */
function readLastCheckTs(): number {
  try {
    return Number(uni.getStorageSync(LAST_CHECK_KEY)) || 0;
  } catch {
    return 0;
  }
}

/** 记录本次检查时间戳 */
function writeLastCheckTs(ts: number): void {
  try {
    uni.setStorageSync(LAST_CHECK_KEY, ts);
  } catch {
    /* 忽略 */
  }
}

/**
 * 下载 APK 并调起系统安装器。
 * - downloadUrl 为空:toast 提示「下载地址未配置」并跳过;
 * - stateChanged 回调实时刷新 uni.showLoading 标题显示百分比;
 * - 下载完成(status=200)调 plus.runtime.install 走系统安装器;
 * - 失败(下载/安装)给 toast,并 reject 由调用方吞掉,不外抛。
 */
function downloadAndInstall(info: VersionInfo): Promise<void> {
  return new Promise((resolve, reject) => {
    if (!info.downloadUrl) {
      uni.showToast({ title: '下载地址未配置', icon: 'none' });
      reject(new Error('downloadUrl 为空'));
      return;
    }
    const dl = getPlus()?.downloader;
    const rt = getPlus()?.runtime;
    if (!dl || !rt) {
      uni.showToast({ title: '更新组件不可用', icon: 'none' });
      reject(new Error('plus.runtime/downloader 不可用'));
      return;
    }

    uni.showLoading({ title: '准备下载…', mask: true });
    const task = dl.createDownload(
      info.downloadUrl,
      { filename: `_doc/apk/update_${info.version}.apk` },
      (t, status) => {
        uni.hideLoading();
        if (status === 200 && t.state === 'success') {
          // 调起系统安装器(force:false 走系统 UI,用户授权「未知来源」后安装)
          rt.install(
            t.filename,
            { force: false },
            () => resolve(),
            (e) => {
              console.error('[appUpdate] 安装失败:', e);
              uni.showToast({ title: '安装失败,请稍后重试', icon: 'none' });
              reject(e);
            },
          );
        } else {
          uni.showToast({ title: '下载失败,请检查网络', icon: 'none' });
          reject(new Error(`下载状态异常: ${status}`));
        }
      },
    );
    // 实时刷新下载百分比到 loading 标题
    task.addEventListener('stateChanged', (t) => {
      if (t.state === 'downloading' && t.totalSize > 0) {
        const pct = Math.floor((t.downloadedSize / t.totalSize) * 100);
        uni.showLoading({ title: `下载中 ${pct}%`, mask: true });
      }
    });
    task.start();
  });
}

/** 判定当前是否 iOS(iOS 无法整包侧载,仅提示) */
function isIOS(): boolean {
  try {
    return uni.getSystemInfoSync().platform === 'ios';
  } catch {
    return false;
  }
}

/**
 * 弹出更新确认弹窗并触发下载安装(平台分支在此收敛)。
 * - iOS:仅 showModal 提示「请通过应用商店更新」,不下载。
 * - Android:showModal 二选一(强制更新 showCancel:false 不可关闭),
 *   确认→下载安装,取消→记录跳过的版本号。
 */
function showUpdateDialogThenDownload(info: VersionInfo): Promise<void> {
  return new Promise((resolve) => {
    if (isIOS()) {
      uni.showModal({
        title: '发现新版本',
        content: info.releaseNotes || `新版本 v${info.version} 已发布,请通过应用商店更新。`,
        showCancel: false,
        confirmText: '知道了',
        complete: () => resolve(),
      });
      return;
    }
    uni.showModal({
      title: `发现新版本 v${info.version}`,
      content: info.releaseNotes || '请更新到最新版本以获得更好体验。',
      confirmText: '立即更新',
      cancelText: '稍后',
      showCancel: !info.forceUpdate,
      success: (res) => {
        if (res.confirm) {
          // 下载/安装失败在内部已 toast,这里吞掉 reject 不外抛
          void downloadAndInstall(info).then(resolve).catch(() => resolve());
        } else {
          // 用户点「稍后」:记录跳过的版本(强制更新 showCancel=false 不会走到此分支)
          writeSkippedVersion(info.versionCode);
          resolve();
        }
      },
      fail: () => resolve(),
    });
  });
}

/**
 * App 端检查更新核心逻辑。
 * @param opts.manual true 表示手动触发(「我的」页入口):忽略节流与跳过缓存,失败给 toast。
 */
async function checkAppUpdateOnApp(opts: { manual?: boolean }): Promise<void> {
  const manual = opts.manual === true;
  console.log('[appUpdate] 开始检查更新, manual =', manual);

  // 自动检查:24h 节流,未到间隔直接返回
  if (!manual && Date.now() - readLastCheckTs() < AUTO_CHECK_INTERVAL_MS) {
    console.log('[appUpdate] 自动检查被 24h 节流跳过');
    return;
  }

  // 拉取最新版本信息(失败:自动静默 console.warn,手动 toast)
  let info: VersionInfo;
  try {
    info = await fetchLatestVersion();
    console.log('[appUpdate] 已获取服务端版本:', info.version, 'versionCode =', info.versionCode);
  } catch (e) {
    if (manual) {
      uni.showToast({ title: e instanceof RequestError ? e.message : '检查更新失败', icon: 'none' });
    } else {
      console.warn('[appUpdate] 检查更新失败(已静默):', e);
    }
    return;
  }
  // 成功取到信息后记录检查时间
  writeLastCheckTs(Date.now());

  // 数值比对:服务端 versionCode <= 本地 versionCode 即无更新
  const localCode = readLocalVersionCode();
  console.log('[appUpdate] 本地 versionCode =', localCode, '比对结果 =', compareVersionCode(localCode, info.versionCode));
  if (compareVersionCode(localCode, info.versionCode) <= 0) {
    if (manual) uni.showToast({ title: '已是最新版本', icon: 'none' });
    return;
  }

  // 自动检查:用户曾跳过该版本则不再弹(手动入口忽略此缓存,强制再提示)
  if (!manual && readSkippedVersion() === info.versionCode) return;

  await showUpdateDialogThenDownload(info);
}
// #endif

/**
 * 检查应用更新(对外主入口)。
 *
 * - App 端(APP-PLUS):实际检查并按需弹窗下载;自动调用受 24h 节流,
 *   手动调用(manual=true)忽略节流与跳过缓存。
 * - H5 / 小程序:编译期剔除为 no-op;手动入口给 toast「当前环境不支持更新」。
 * - 任何失败均不阻断应用启动。
 *
 * 平台分支用并列的 #ifdef / #ifndef,保证 TS 类型检查时两段代码都可达。
 */
export async function checkAppUpdate(opts: { manual?: boolean } = {}): Promise<void> {
  // 手动触发总是响应;仅自动检查防重入(避免启动检查未结束时重复触发)
  if (!opts.manual && isChecking) return;
  isChecking = true;
  try {
    // #ifdef APP-PLUS
    await checkAppUpdateOnApp(opts);
    // #endif
    // #ifndef APP-PLUS
    if (opts.manual) uni.showToast({ title: '当前环境不支持更新', icon: 'none' });
    // #endif
  } finally {
    isChecking = false;
  }
}

/**
 * 「我的」页手动入口:强制检查(忽略节流与跳过缓存),
 * 失败或无更新均给 toast 反馈。
 */
export function checkAppUpdateManual(): void {
  void checkAppUpdate({ manual: true });
}
