// 学习小结（PRD 5.5）：正确率 / 用时 / 回顾 / 打卡成功动画
const app = getApp();

Page({
  data: {
    total: 0,
    ok: 0,
    pct: 0,
    duration: "",
    results: [],
    showCheckin: false,
    streak: 1,
    animPct: 0,
  },

  onLoad() {
    const s = app.globalData.lastStudySession;
    if (!s) {
      wx.showToast({ title: "没有学习记录", icon: "none" });
      setTimeout(() => wx.switchTab({ url: "/pages/learn/index" }), 800);
      return;
    }
    const total = s.results.length;
    const ok = s.results.filter((r) => r.result === "correct").length;
    const sec = Math.max(1, Math.round((Date.now() - s.startAt) / 1000));

    this.setData({
      total,
      ok,
      pct: total ? Math.round((ok / total) * 100) : 0,
      duration: Math.floor(sec / 60) + " 分 " + (sec % 60) + " 秒",
      results: s.results,
      showCheckin: !!(s.checkin && s.checkin.created),
      streak: (s.checkin && s.checkin.streak_days) || 1,
    });
    // 进度环动画：先 0 再过渡到目标值
    setTimeout(() => this.setData({ animPct: this.data.pct }), 100);
    // 清理，避免返回重入
    app.globalData.lastStudySession = null;
  },

  onBackLearn() {
    wx.switchTab({ url: "/pages/learn/index" });
  },

  onCloseCheckin() {
    this.setData({ showCheckin: false });
  },

  onShareAppMessage() {
    return {
      title: "我刚刚学了 " + this.data.total + " 张法语闪卡，正确率 " + this.data.pct + "%！",
      path: "/pages/home/index",
    };
  },
});
