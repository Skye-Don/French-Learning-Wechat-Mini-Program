// 我的：个人中心（PRD 5.7）
const api = require("../../utils/request");
const auth = require("../../utils/auth");

Page({
  data: {
    profile: null,
    loading: true,
    avatarUrl: "", // 本地绑定头像 → 服务端头像，兜底空（显示 🇫🇷）
    bound: false,
  },

  onShow() {
    this.load();
  },

  load() {
    this.setData({
      avatarUrl: wx.getStorageSync("fr_avatar") || "",
      bound: wx.getStorageSync("fr_bound") === 1,
    });
    api.get("/api/user/profile")
      .then((profile) => {
        if (!this.data.avatarUrl) this.setData({ avatarUrl: profile.avatar_url || "" });
        this.setData({ profile, loading: false });
      })
      .catch((err) => {
        this.setData({ loading: false });
        wx.showToast({ title: err.message, icon: "none" });
      });
  },

  /** 账号绑定：未绑定时进绑定页；已绑定可重新修改头像昵称 */
  onAccount() {
    wx.navigateTo({ url: "/pages/auth/welcome" });
  },

  onCalendar() { wx.navigateTo({ url: "/pages/checkin/calendar" }); },
  onReminder() { wx.navigateTo({ url: "/pages/settings/reminder" }); },
  onSensitive() { wx.navigateTo({ url: "/pages/settings/sensitive" }); },

  onAbout() {
    wx.showModal({
      title: "关于",
      content: "法语学习小程序 V0 框架版\n面向零基础/初级法语学习者",
      showCancel: false,
    });
  },

  /** 清空本地演示数据（开发期调试用） */
  onReset() {
    wx.showModal({
      title: "清空本地数据",
      content: "将删除本机的登录态缓存，重新登录。确定？",
      success: (res) => {
        if (res.confirm) {
          auth.logout();
          wx.removeStorageSync("fr_bound");
          wx.removeStorageSync("fr_avatar");
          wx.reLaunch({ url: "/pages/home/index" });
        }
      },
    });
  },

  onShareAppMessage() {
    return { title: "一起来学最地道的法语", path: "/pages/home/index" };
  },
  onShareTimeline() {
    return { title: "一起来学最地道的法语" };
  },
});
