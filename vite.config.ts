import { defineConfig } from "vite";
import uni from "@dcloudio/vite-plugin-uni";
import { fileURLToPath, URL } from "node:url";

// https://vitejs.dev/config/
export default defineConfig({
  // uni-app 会把 vite 的 root 指向 src/(源码根),默认 envDir 随 root 落到 src/,
  // 导致项目根的 .env 不被加载。此处显式指定 envDir 为项目根(本文件所在目录)。
  envDir: fileURLToPath(new URL(".", import.meta.url)),
  plugins: [uni()],
});
