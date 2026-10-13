// ============================================================
// 登录态管理（PRD 5.1 微信一键登录）
//
// 标准流程（安全红线）：
//   wx.login() 拿临时 code
//     → POST /api/auth/wx-login { code }
//     → 服务端拿 code 调 jscode2session 换 openid（AppSecret 只在服务端）
//     → 服务端查/建用户、签发 JWT
//     → 前端只保存 token，禁止保存 openid/session_key
// ============================================================
const { post } = require("./request");

const TOKEN_KEY = "fr_token";
const USER_KEY = "fr_user";

function getToken() {
  return wx.getStorageSync(TOKEN_KEY) || "";
}

function getCachedUser() {
  return wx.getStorageSync(USER_KEY) || null;
}

/** wx.login 的 Promise 化 */
function wxLogin() {
  return new Promise((resolve, reject) => {
    wx.login({
      success: (res) => (res.code ? resolve(res.code) : reject(new Error("wx.login 未返回 code"))),
      fail: (err) => reject(new Error("wx.login 失败: " + (err && err.errMsg))),
    });
  });
}

/** 用 code 换登录态（后端见 backend/app/routers/auth.py） */
function loginByWxCode(code) {
  return post("/api/auth/wx-login", { code }).then((d) => {
    wx.setStorageSync(TOKEN_KEY, d.token);
    wx.setStorageSync(USER_KEY, d.user);
    return { ...d.user, is_new_user: d.is_new_user };
  });
}

/** 确保已登录：有 token 直接返回缓存用户，否则静默登录 */
function ensureLogin() {
  const token = getToken();
  const cached = getCachedUser();
  if (token && cached) return Promise.resolve(cached);
  return forceRelogin();
}

/** 强制重新登录（token 失效 / 首次启动） */
function forceRelogin() {
  return wxLogin()
    .then(loginByWxCode)
    .then((user) => {
      return user;
    });
}

/** 退出登录（演示用） */
function logout() {
  wx.removeStorageSync(TOKEN_KEY);
  wx.removeStorageSync(USER_KEY);
}

module.exports = { getToken, getCachedUser, ensureLogin, forceRelogin, logout };
