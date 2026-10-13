// ============================================================
// 网络请求封装
// - 自动携带 Authorization: Bearer <token>
// - 401 时自动静默重登并重放一次请求
// - 统一超时 / 错误提示（PRD 8 / 10.2 错误码约定）
// ============================================================
const BASE_URL = require("./config").API_BASE_URL;

// ⚠️ 不能在模块顶层 require("./auth")：
// auth.js 顶层 require 了本文件（request），形成循环依赖。
// CommonJS 下先被加载的一方拿到的是对方"还没填完的空 exports"，
// 表现为 auth.getToken is not a function。
// 解决：函数体内惰性 require（模块系统有缓存，无性能损耗）。
function getAuth() {
  return require("./auth");
}

function request(path, method, data, retry) {
  return new Promise((resolve, reject) => {
    const auth = getAuth();
    const token = auth.getToken();
    wx.request({
      url: BASE_URL + path,
      method: method || "GET",
      data: data || {},
      timeout: 10000,
      header: {
        "Content-Type": "application/json",
        Authorization: token ? "Bearer " + token : "",
        // 双通道带 token：部分托管网关会注入自己的 Authorization 头覆盖客户端值，
        // 因此服务端同时接受 X-Auth-Token 作为登录态来源（对生产后端无副作用）。
        "X-Auth-Token": token || "",
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
          return;
        }
        // 401：token 失效 → 静默重登一次再重放（PRD 5.1 异常处理）
        if (res.statusCode === 401 && !retry) {
          getAuth().forceRelogin()
            .then(() => resolve(request(path, method, data, true)))
            .catch(() => reject(makeError(res)));
          return;
        }
        reject(makeError(res));
      },
      fail(err) {
        // PRD 7.4 弱网兜底：网络层失败统一提示
        reject({ code: -1, message: "网络异常，请检查网络后重试", raw: err });
      },
    });
  });
}

function makeError(res) {
  const body = res.data || {};
  return {
    code: res.statusCode,
    message: (body.error && body.error.message) || "请求失败（" + res.statusCode + "）",
    raw: body,
  };
}

module.exports = {
  get: (path, data) => request(path, "GET", data),
  post: (path, data) => request(path, "POST", data),
  put: (path, data) => request(path, "PUT", data),
  del: (path, data) => request(path, "DELETE", data),
};
