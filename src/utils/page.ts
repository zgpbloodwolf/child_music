/**
 * 当前页路由工具(跨端安全)。
 *
 * 背景:`getCurrentPages()[last].route` 在不同端是否带前导 `/` 不一致
 * (微信/抖音不带,快手/H5 一般带),比较前必须统一归一化,否则 isTabBarPage 误判
 * 会导致悬浮播放栏 bottom 偏移取错(详见 MiniPlayer 组件)。
 *
 * 调用时机:仅限页面级组件 setup / 事件回调中调用(此时栈顶即当前页)。
 * 切勿在 App.onLaunch 中调用——那时 page 尚未生成,栈可能为空。
 */

/** tabBar 页白名单:必须与 pages.json 的 tabBar.list 同步维护(均不带前导 /) */
const TAB_BAR_PAGES = ['pages/home/index', 'pages/mine/index'];

/**
 * 从页面对象中安全取出 route 字段。
 * uni-app/小程序页面对象的 route 在各端类型声明不统一,故用类型守卫,避免 any。
 */
function pickRoute(page: unknown): string {
  if (page && typeof page === 'object' && 'route' in page) {
    const route = (page as { route?: unknown }).route;
    if (typeof route === 'string') return route;
  }
  return '';
}

/**
 * 取当前栈顶页 route 并归一化:去前导 `/`、去尾 `/`、转小写。
 * 取不到(空栈/异常)返回空串。
 */
export function currentPageRoute(): string {
  try {
    const pages = getCurrentPages();
    if (!pages || pages.length === 0) return '';
    const raw = pickRoute(pages[pages.length - 1]);
    return raw.replace(/^\/+/, '').replace(/\/+$/, '').toLowerCase();
  } catch {
    return '';
  }
}

/** 当前页是否 tabBar 页(按归一化后的 route 匹配白名单) */
export function isTabBarPage(): boolean {
  return TAB_BAR_PAGES.includes(currentPageRoute());
}
