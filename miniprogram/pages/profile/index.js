// 我的：个人中心（PRD 5.7）
const api = require("../../utils/request");
const auth = require("../../utils/auth");

Page({
  data: {
    profile: null,
    loading: true,
  },

  onShow() {
    this.load();
  },

  load() {
    api.get("/api/user/profile")
      .then((profile) => this.setData({ profile, loading: false }))
      .catch((err) => {
        this.setData({ loading: false });
        wx.showToast({ title: err.message, icon: "none" });
      });
  },

  onCalendar() { wx.navigateTo({ url: "/pages/checkin/calendar" }); },
  onReminder() { wx.navigateTo({ url: "/pages/settings/reminder" }); },
  onSensitive() { wx.navigateTo({ url: "/pages/settings/sensitive" }); },

  onShare() {
    // PRD 5.10：V0 用 open-type=share 的 button 触发；这里做兜底提示
    wx.showToast({ title: "点击右上角「···」也可转发", icon: "none" });
  },
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
