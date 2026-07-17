/// <reference types="vite/client" />

/** 项目自定义的环境变量(见根目录 .env / .env.example,VITE_ 前缀由 Vite 编译期注入) */
interface ImportMetaEnv {
  /** 运行环境:local(本机联调)/ online(线上公网) */
  readonly VITE_APP_ENV: string;
  /** local 环境后端基础地址(含 /childmusic 前缀) */
  readonly VITE_API_BASE_URL_LOCAL: string;
  /** online 环境后端基础地址(含 /childmusic 前缀) */
  readonly VITE_API_BASE_URL_ONLINE: string;
}

declare module '*.vue' {
  import { DefineComponent } from 'vue'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/ban-types
  const component: DefineComponent<{}, {}, any>
  export default component
}
