/**
 * 版本更新相关类型定义。
 *
 * 字段名与后端 VersionOut(CamelModel 自动转 camelCase)对齐,
 * 见 server/app/routers/version.py 与 server/app/schemas.py。
 */

/** 后端 GET /api/version/latest 的响应 */
export interface VersionInfo {
  /** 展示版本号(如 1.0.1),仅用于弹窗文案展示 */
  version: string;
  /** 数值版本号(后端从 app_version 派生,如 101),用于客户端数值比对 */
  versionCode: number;
  /** APK 下载完整 URL(后端 .env 决定,可为后端 /library/... 直链或外链) */
  downloadUrl: string;
  /** 更新说明(展示在更新弹窗内容区,可多行) */
  releaseNotes: string;
  /** 是否强制更新(为 true 时弹窗不可关闭) */
  forceUpdate: boolean;
}
