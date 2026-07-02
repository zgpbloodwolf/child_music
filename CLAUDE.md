# 项目规则:Music(手机端音乐应用)

> 本文件是项目的 AI 助手规则与上下文说明,供 Claude Code / Cursor 等编码助手及团队成员阅读。
> 请在动手编码前通读;涉及偏离本规则的改动需先与维护者确认。

---

## 1. 项目概述

- **定位**:手机端音乐播放应用(听歌、歌单、播放控制、后台播放等)。
- **目标平台**:App(iOS/Android)优先,可同时编译到 H5 与微信小程序。
- **语言(强制)**:全中文项目。代码注释、commit、文档、助手的所有提问与解释、界面文案一律用中文,**不要使用英文**(技术术语与代码标识符除外)。

---

## 2. 技术栈

| 项 | 选型 | 备注 |
| --- | --- | --- |
| 框架 | uni-app + Vue 3 (`<script setup>` 组合式 API) | 默认 Vue3 + Vite |
| 语言 | TypeScript | 新文件一律 `.ts` / `.vue`,**禁止**新增裸 `.js` |
| 状态管理 | Pinia | 替代 Vuex,模块化拆分 |
| 样式 | SCSS + `rpx` | 全局样式 `uni.scss`,页面级 SCSS 局部作用域 |
| 包管理 | pnpm | 锁文件 `pnpm-lock.yaml` |
| 请求 | `uni.request` 封装 | 统一走 `src/utils/request.ts` |
| UI 组件 | uni-ui / uView(按需) | 引入即用,避免全量注册 |

> 若实际工程为 **Vue2 + HBuilderX** 项目,请相应调整(Vuex、Options API),并在文件顶部标注差异。

---

## 3. 目录结构

```
src/
├── pages/            # 页面(在 pages.json 注册),按业务域分子目录
│   ├── home/         # 首页
│   ├── player/       # 播放页
│   └── playlist/     # 歌单详情
├── components/       # 可复用组件,组件名 PascalCase,目录同名
├── store/            # Pinia 模块: player / user / library ...
├── api/              # 接口定义,按业务域拆分(api/player.ts)
├── utils/            # 工具: request / audio / format / storage
├── types/            # 全局 TS 类型与接口定义
├── static/           # 静态资源(图片/图标),不参与编译,用绝对路径 /static/...
├── App.vue
├── main.ts
├── pages.json        # 页面路由、tabBar、全局样式配置
├── manifest.json     # 应用信息与各平台打包配置
└── uni.scss          # 全局 SCSS 变量(主题色、间距)
```

---

## 4. 音频播放约定(核心)

音乐 app 的核心是播放器,务必遵守:

- **统一使用** `uni.getBackgroundAudioManager()`(支持后台播放、锁屏控制、系统通知栏),**不要**用 `innerAudioContext` 做主播放。
- 所有播放逻辑收敛到 `src/store/player.ts`(单一数据源):当前歌曲、播放列表、播放状态、进度、播放模式。
- 修改 `src`、`title`、`coverImgUrl` 必须通过 store action,触发后由 `onCanplay` / `onTimeUpdate` / `onEnded` 回调同步状态。
- 进度跳转用 `bgAudioManager.seek(sec)`,UI 进度条节流(≥250ms 一次),避免频繁 seek。
- 监听器在 `App.vue` 或常驻页面注册一次,**避免重复绑定**导致多次回调。
- iOS 后台播放需在 `manifest.json` 配置 `UIBackgroundModes: ['audio']`,改动需验证真机后台行为。

---

## 5. 编码规范

### 命名
- 组件文件/目录:`PascalCase`(如 `SongItem/SongItem.vue`)。
- 页面文件:`index.vue`,目录名小写连字符(`player-detail`)。
- 变量/函数:`camelCase`;常量:`UPPER_SNAKE_CASE`;类型/接口:`PascalCase`。
- store:`useXxxStore`,action 名动宾结构(`playNext`、`togglePlayMode`)。

### Vue / TS
- 一律使用 `<script setup lang="ts">`,Options API 仅限已有 Vue2 代码。
- props 用 `defineProps<T>()` 类型化;emit 用 `defineEmits<T>()`。
- 禁止 `any`;必须时用 `unknown` + 类型守卫,并写注释。
- 复杂对象(歌曲、歌单、用户)在 `src/types/` 定义接口,跨文件复用。

### 样式
- 尺寸用 `rpx`(750 设计稿基准);字号、边框等 1px 场景可用 `px`。
- 颜色用 `uni.scss` 变量(`$primary`、`$text-main`),禁止散落硬编码色值。
- 页面样式加 `scoped`,避免全局污染。

### 接口
- 所有请求走 `utils/request.ts`,统一处理 baseURL、token、错误码、loading。
- 接口入参/返回必须定义 TS 类型,禁止裸 `uni.request`。

---

## 6. 跨端兼容约定

- 平台差异用条件编译,写明目标平台:
  ```vue
  <!-- #ifdef MP-WEIXIN -->
  <!-- 仅微信小程序 -->
  <!-- #endif -->
  <!-- #ifdef APP-PLUS -->
  <!-- 仅 App -->
  <!-- #endif -->
  ```
- DOM/BOM(`document`、`window`)仅在 H5 可用,**禁止**在通用代码直接引用。
- 本地存储用 `uni.setStorageSync` / `getStorageSync`,不用 `localStorage`。
- 网络图片处理小程序域名白名单;大图加 lazy-load 与占位。
- 改动涉及平台 API 时,至少在注释中标注已验证/未验证平台。

---

## 7. Git 提交规范

提交信息格式:`<type>(<scope>): <subject>`

- type:`feat` / `fix` / `refactor` / `style` / `perf` / `chore` / `docs` / `test`
- scope:模块名,如 `player`、`home`、`api`、`build`
- subject:简短中文描述,祈使句,不加句号

示例:
- `feat(player): 支持锁屏后切换下一首`
- `fix(api): 修复歌单列表分页参数丢失`

- 一个提交只做一件事,避免混合重构与功能。
- 不提交 `unpackage/`、`.DS_Store`、IDE 配置等(见 `.gitignore`)。

---

## 8. 常用命令

基于 uni-app Vue3 + Vite CLI 工程(非 HBuilderX):

```bash
pnpm install            # 安装依赖
pnpm dev:h5             # H5 开发
pnpm dev:mp-weixin      # 微信小程序开发(需微信开发者工具打开 dist/dev/mp-weixin)
pnpm dev:app            # App 开发(需 HBuilderX 真机/模拟器)
pnpm build:h5           # H5 生产构建
pnpm build:mp-weixin    # 微信小程序生产构建
```

> 若为 HBuilderX 工程,以上命令以 IDE 运行为准。

---

## 9. AI 助手工作约定

- **全程使用中文(强制)**:助手的所有提问、解释、说明、进度汇报、commit message、代码注释均用中文,**禁止使用英文**;面向用户的所有界面文案(按钮、标题、导航、提示、报错信息、空状态文案等)也全部使用中文,不混入英文。仅技术术语与代码标识符(如 `getBackgroundAudioManager`、`rpx`、`Pinia`)可保留原文。
- **先理解再动手**:改动前阅读相关页面/store/api,遵循现有模式;不要引入新的状态管理或请求方式。
- **最小改动**:只动与任务相关的文件,不要顺手重构无关代码;重构需单独说明并确认。
- **类型安全**:新增/修改代码必须类型通过,不新增 `any`。
- **跨端安全**:改动后自检是否破坏 H5/App/小程序兼容(见第 6 节),有平台风险须在回复中说明。
- **音频相关改动**:严格遵守第 4 节,修改播放器需说明对后台/锁屏/进度的影响。
- **验证**:提供测试或自测步骤;运行命令后如实报告结果,失败不掩饰。
- **不要擅自**:`git push`、改 `manifest.json` 的 appid/密钥、升级/更换依赖版本,除非被明确要求。
- **文件引用**:回复中引用代码使用 `文件路径:行号` 格式。
