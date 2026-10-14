// ============================================================
// 账号绑定页（首次启动流程：隐私说明 → 微信登录 → 头像昵称绑定）
//
// 背景（微信官方规范，2022-10 后生效，以官方文档核实为准）：
//   - wx.getUserProfile 已回收：不再返回真实昵称头像（返回匿名数据）
//   - 现行唯一支持形态 = 「头像昵称填写能力」：
//       button open-type="chooseAvatar"（用户主动选头像）
//       input type="nickname"（键盘可快捷填入微信昵称）
//   - "微信验证登录"本身 = wx.login 静默换取登录态（openid 只在服务端）
//
// 流程：一键登录按钮 → wx.login 验证 → PUT /api/user/profile 绑定昵称
//       → 标记已绑定 → 进首页（新用户会接着弹敏感词选择）
// ============================================================
const api = require("../../utils/request");
const auth = require("../../utils/auth");

const BOUND_KEY = "fr_bound";    // 1=已绑定 2=跳过
const AVATAR_KEY = "fr_avatar";  // 本地保存的头像文件路径（V0 设备本地）

Page({
  data: {
    avatarUrl: "",
    nickname: "",
    submitting: false,
  },

  onLoad() {
    // 再次进入（从「我的」页来）时回显已保存的信息
    this.setData({
      avatarUrl: wx.getStorageSync(AVATAR_KEY) || "",
      nickname: (wx.getStorageSync("fr_user") || {}).nickname || "",
    });
  },

  /** 用户选择头像（chooseAvatar 回调） */
  onChooseAvatar(e) {
    const tmp = e.detail.avatarUrl;
    if (!tmp) return;
    // V0：把临时文件持久化到本机（跨设备同步需对象存储，V1 接入）
    try {
      wx.getFileSystemManager().saveFile({
        tempFilePath: tmp,
        success: (r) => this.setData({ avatarUrl: r.savedFilePath }),
        fail: () => this.setData({ avatarUrl: tmp }), // 保存失败仍可本会话显示
      });
    } catch (e2) {
      this.setData({ avatarUrl: tmp });
    }
  },

  onNickInput(e) {
    this.setData({ nickname: e.detail.value });
  },

  /** 一键登录并绑定 */
  onBind() {
    if (this.data.submitting) return;
    this.setData({ submitting: true });

    // 1) 微信验证登录（静默 wx.login → 服务端换 JWT，安全规范见 utils/auth.js）
    auth.forceRelogin()
      .then(() => {
        // 2) 绑定昵称到服务端（头像 V0 仅存本机，见文件头注释）
        const nick = (this.data.nickname || "").trim() || "法语学习者";
        return api.put("/api/user/profile", { nickname: nick });
      })
      .then(() => {
        // 3) 标记已绑定 + 缓存头像 → 进首页（新用户会接着弹敏感词选择）
        wx.setStorageSync(BOUND_KEY, 1);
        if (this.data.avatarUrl) wx.setStorageSync(AVATAR_KEY, this.data.avatarUrl);
        wx.reLaunch({ url: "/pages/home/index" });
      })
      .catch((err) => {
        this.setData({ submitting: false });
        wx.showToast({ title: err.message || "绑定失败，请重试", icon: "none" });
      });
  },

  /** 暂不绑定（不强制；之后可在「我的 → 账号绑定」补绑） */
  onSkip() {
    wx.setStorageSync(BOUND_KEY, 2);
    wx.reLaunch({ url: "/pages/home/index" });
  },
});
