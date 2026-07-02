import { createSSRApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";

// uni-app Vue3 入口:创建应用实例并注册 Pinia
export function createApp() {
  const app = createSSRApp(App);
  app.use(createPinia());
  return {
    app,
  };
}
