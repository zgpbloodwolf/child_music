/**
 * 全局配置:环境相关的常量。
 *
 * 后端服务经 Nginx Proxy Manager 暴露为公网 .../childmusic,提供曲库元数据与音频/封面
 * 文件分发。音频不再打包进 App,改为在线访问(默认)+ 下载缓存离线(收藏歌曲)。
 */

/** 运行环境:切换只改这一个值。
 *  - local:本机联调(连接本机后端 127.0.0.1:8823)
 *  - online:线上公网地址(经 Nginx Proxy Manager 暴露) */
export type AppEnv = 'local' | 'online';
export const APP_ENV: AppEnv = 'online';

/** 各环境的后端基础地址(含反向代理子路径前缀 /childmusic) */
const API_BASE_URLS: Record<AppEnv, string> = {
  local: 'http://127.0.0.1:8823/childmusic',
  online: 'http://zgp.vip.cpolar.cn/childmusic',
};

/** 后端服务基础地址:元数据请求与音频/封面文件 URL 均基于此拼接 */
export const API_BASE_URL = API_BASE_URLS[APP_ENV];
