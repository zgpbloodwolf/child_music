/* 后台公共侧边栏:各管理页在 <body> 开头同步引入 <script src="common.js"></script>。
 * 注入内容:左侧导航(当前模块高亮)+ 底部身份/退出占位(id=whoami / id=logoutBtn,
 * 由各页自己的登录态脚本填充与绑定;因本脚本同步执行且先于页面内联脚本,元素届时已存在)。
 * 样式随脚本注入 <head>,排在页面样式之后,可覆盖页面同名规则。
 */
(function () {
  // 应用前缀(自动识别 /admin/xxx 子路径),与各页 BASE 规则一致
  var BASE = location.pathname.replace(/\/admin\/[^/]*\/?$/, "") || "";

  var style = document.createElement("style");
  style.textContent = [
    /* 内容区右移,给固定侧边栏留位 */
    "body.with-sidebar { padding-left: 208px; }",
    ".admin-sidebar { position: fixed; left: 0; top: 0; bottom: 0; width: 208px; background: #fff; border-right: 1px solid #ececec; display: flex; flex-direction: column; z-index: 50; }",
    ".sb-brand { padding: 18px 16px 14px; font-size: 16px; font-weight: 600; color: #222; border-bottom: 1px solid #f0f0f0; }",
    ".sb-brand .sub { display: block; margin-top: 2px; font-size: 11px; font-weight: 400; color: #b0aaa5; letter-spacing: 1px; }",
    ".sb-nav { flex: 1; padding: 10px 8px; display: flex; flex-direction: column; gap: 2px; overflow-y: auto; }",
    ".sb-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 8px; font-size: 14px; color: #555; text-decoration: none; }",
    ".sb-item:hover { background: #fff4e8; color: #222; }",
    ".sb-item.on { background: #fff1e3; color: #e8722a; font-weight: 600; }",
    ".sb-foot { padding: 12px 14px; border-top: 1px solid #f0f0f0; font-size: 12px; color: #999; display: flex; align-items: center; gap: 8px; }",
    ".sb-foot #whoami { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }",
    ".sb-foot button { background: #f2f2f2; color: #555; border: none; border-radius: 6px; padding: 5px 10px; font-size: 12px; cursor: pointer; }",
    ".sb-foot button:hover { background: #e5e5e5; }",
    /* 窄屏:侧边栏折叠为顶栏(管理后台以桌面为主,仅保证可用) */
    "@media (max-width: 760px) {",
    "  body.with-sidebar { padding-left: 0; padding-top: 54px; }",
    "  .admin-sidebar { width: 100%; height: 54px; flex-direction: row; align-items: center; border-right: none; border-bottom: 1px solid #ececec; }",
    "  .sb-brand { border-bottom: none; padding: 0 12px; font-size: 14px; white-space: nowrap; }",
    "  .sb-brand .sub { display: none; }",
    "  .sb-nav { flex-direction: row; padding: 0 6px; }",
    "  .sb-item { padding: 8px 9px; font-size: 13px; }",
    "  .sb-item span.sb-ico { display: none; }",
    "  .sb-foot { border-top: none; border-left: 1px solid #f0f0f0; margin-left: auto; padding: 0 10px; }",
    "}",
  ].join("\n");

  var ITEMS = [
    { path: "/admin/songs", icon: "🎵", label: "歌曲管理" },
    { path: "/admin/categories", icon: "🗂️", label: "分类管理" },
    { path: "/admin/members", icon: "👤", label: "账号管理" },
  ];
  var nav = ITEMS.map(function (it) {
    var on = location.pathname === BASE + it.path || location.pathname === BASE + it.path + "/";
    return '<a class="sb-item' + (on ? " on" : "") + '" href="' + BASE + it.path + '">'
      + '<span class="sb-ico">' + it.icon + "</span>" + it.label + "</a>";
  }).join("");

  var bar = document.createElement("aside");
  bar.className = "admin-sidebar";
  bar.innerHTML = '<div class="sb-brand">🎵 启蒙音频<span class="sub">后 台 管 理</span></div>'
    + '<nav class="sb-nav">' + nav + "</nav>"
    + '<div class="sb-foot"><span id="whoami"></span><button id="logoutBtn" type="button">退出</button></div>';

  document.head.appendChild(style);
  document.body.classList.add("with-sidebar");
  document.body.insertBefore(bar, document.body.firstChild);
})();
