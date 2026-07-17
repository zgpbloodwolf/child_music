/**
 * 全局配置:环境相关的常量。
 *
 * 后端基础地址与当前运行环境均从 Vite 的 .env 读取(变量以 VITE_ 开头,编译期注入):
 *  - VITE_APP_ENV:运行环境,local(本机联调)/ online(线上公网)
 *  - VITE_API_BASE_URL_LOCAL / VITE_API_BASE_URL_ONLINE:对应环境的后端地址(含 /childmusic 前缀)
 * 模板见根目录 .env.example;本地地址不入库,各自复制为 .env 后填写。
 *
 * 注意:App(真机/模拟器)里 127.0.0.1 指向手机自身,联调时务必填开发机局域网 IP,
 * 并保证手机与电脑同一 WiFi、电脑防火墙放行 8823。
 */

/** 运行环境:切换只改 .env 的 VITE_APP_ENV */
export type AppEnv = 'local' | 'online';

/** 当前运行环境:取自 VITE_APP_ENV,缺省回退 local */
export const APP_ENV: AppEnv = (import.meta.env.VITE_APP_ENV as AppEnv) || 'local';

/** 各环境的后端基础地址(含反向代理子路径前缀 /childmusic) */
const API_BASE_URLS: Record<AppEnv, string> = {
  local: import.meta.env.VITE_API_BASE_URL_LOCAL || '',
  online: import.meta.env.VITE_API_BASE_URL_ONLINE || '',
};

/** 后端服务基础地址:元数据请求与音频/封面文件 URL 均基于此拼接 */
export const API_BASE_URL = API_BASE_URLS[APP_ENV];
