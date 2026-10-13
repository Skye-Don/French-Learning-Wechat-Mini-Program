// 学习提醒设置（PRD 5.9：V0 只做 UI 与接口预留，不实际推送）
// 真实推送需 wx.requestSubscribeMessage 授权（V1 实现），模板 ID 到 mp 后台申请
const api = require("../../utils/request");

Page({
  data: {
    enabled: false,
    time: "20:00",
    goal: 20,
    saving: false,
  },

  onLoad() {
    api.get("/api/user/profile").then((p) => {
      this.setData({
        enabled: !!p.reminder_enabled,
        time: p.reminder_time || "20:00",
        goal: p.daily_goal || 20,
      });
    }).catch((err) => wx.showToast({ title: err.message, icon: "none" }));
  },

  onToggle() {
    this.setData({ enabled: !this.data.enabled });
  },

  onTimeChange(e) {
    this.setData({ time: e.detail.value });
  },

  onGoalInput(e) {
    this.setData({ goal: Number(e.detail.value) || 20 });
  },

  onSave() {
    if (this.data.saving) return;
    this.setData({ saving: true });
    api.put("/api/user/preferences/reminder", {
      reminder_enabled: this.data.enabled,
      reminder_time: this.data.time,
      daily_goal: this.data.goal,
    })
      .then(() => {
        wx.showToast({ title: "设置已保存", icon: "success" });
        setTimeout(() => wx.navigateBack(), 600);
      })
      .catch((err) => {
        this.setData({ saving: false });
        wx.showToast({ title: err.message, icon: "none" });
      });
  },
});
