// ============================================================
// 后端地址与全局常量
// ============================================================
//
// 切换后端：只改下面的 CURRENT（"local" / "prod" / "demo"）
//   local  本机后端（联调用）:  cd demo && python server.py  ->  http://127.0.0.1:8000
//          模拟器需勾选「详情 → 本地设置 → 不校验合法域名」
//   prod   你的生产后端（上线用）: 填 PROD_BASE_URL，并在 mp 后台配 request 合法域名
//   demo   托管 H5 预览环境（仅供浏览器打开看效果）
//          ⚠️ 该托管网关会拦截微信环境(UA 含 MicroMessenger)的请求，
//             因此开发者工具/真机小程序用它必报 401/403，不要用它联调！
// ============================================================
const CURRENT = "local";

const LOCAL_BASE_URL = "http://127.0.0.1:8000";   // 本机 demo 后端（python server.py 默认端口）
const PROD_BASE_URL  = "";                        // ← 上线前填你的 HTTPS 域名（需备案，以微信官方规则为准）
const DEMO_BASE_URL  = "https://french-learning-miniapp.app.workbuddy.host";

const MAP = { local: LOCAL_BASE_URL, prod: PROD_BASE_URL, demo: DEMO_BASE_URL };

module.exports = {
  API_BASE_URL: MAP[CURRENT] || LOCAL_BASE_URL,

  // 调试开关：true 时 wx.request 打印路径与耗时（上线请置 false）
  DEBUG: false,

  // 错误码（PRD 10.2）
  ERR_TOKEN_EXPIRED: 401,
};
