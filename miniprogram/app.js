// ============================================================
// 法语学习小程序 · 入口
// 登录策略（PRD 5.1）：
//   onLaunch 静默登录 wx.login → 后端 code 换 openid → 返回 JWT
//   Token 过期时静默刷新，用户无感知
// 注意：openid 绝不能在前端出现；AppSecret 只能存服务端 .env
// ============================================================
const auth = require("./utils/auth");
const { track, flush } = require("./utils/track");

App({
  globalData: {
    userInfo: null,
    statusBarHeight: 0,
  },

  onLaunch() {
    // 系统信息（导航栏适配用）
    try {
      const sys = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
      this.globalData.statusBarHeight = sys.statusBarHeight || 20;
    } catch (e) {
      this.globalData.statusBarHeight = 20;
    }

    // 静默登录；失败不阻塞页面（各页面有兜底）
    auth.ensureLogin()
      .then((user) => {
        this.globalData.userInfo = user;
        // PRD 5.2：新用户且未选择过 → 首页会自行弹出 opt-in 弹窗
        // 这里只广播一次事件，避免每个页面重复判断
        if (user.is_new_user && !user.sensitive_opt_in) {
          this._isNewPendingOptIn = true;
        }
        // V0 行为分析：应用启动事件 + 把登录前可能攒下的队列补发
        track("app_launch", { channel: "weapp", is_new_user: !!user.is_new_user });
        flush();
      })
      .catch((err) => {
        console.warn("[app] 静默登录失败（弱网或后端异常），页面将使用兜底逻辑", err);
      });
  },

  onHide() {
    // 切后台时把本地埋点队列补发一次
    try { flush(); } catch (e) { /* 不影响主流程 */ }
  },

  /** 首页调用：是否需要弹敏感词 opt-in（只弹一次） */
  consumeNewUserOptInFlag() {
    const v = this._isNewPendingOptIn;
    this._isNewPendingOptIn = false;
    return !!v;
  },
});
