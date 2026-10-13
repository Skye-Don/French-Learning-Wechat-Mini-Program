// 学习页：今日复习 + 按等级课时列表（PRD 5.3 / 5.5）
const api = require("../../utils/request");
const util = require("../../utils/util");

Page({
  data: {
    loading: true,
    levels: [],
    reviewTotal: 0,
  },

  onShow() {
    this.load();
  },

  load() {
    this.setData({ loading: true });
    Promise.all([
      api.get("/api/levels"),
      api.get("/api/flashcard-progress/review-today"),
    ])
      .then(([levels, review]) => {
        levels.forEach((lv) => { lv.icon = util.lessonIcon("vocabulary"); });
        this.setData({ levels, reviewTotal: review.total || 0, loading: false });
      })
      .catch((err) => {
        this.setData({ loading: false });
        wx.showToast({ title: err.message, icon: "none" });
      });
  },

  onReviewTap() {
    if (!this.data.reviewTotal) return;
    wx.navigateTo({ url: "/pages/flashcard/study?mode=review" });
  },

  onLevelTap(e) {
    const id = e.currentTarget.dataset.id;
    const lv = this.data.levels.find((l) => String(l.id) === String(id));
    if (lv && !lv.lesson_count) {
      wx.showToast({ title: "该等级暂无课时", icon: "none" });
      return;
    }
    wx.navigateTo({ url: "/pages/level/detail?id=" + id });
  },

  onShareAppMessage() {
    // PRD 5.10：V0 预留分享入口
    return { title: "一起来学最地道的法语", path: "/pages/home/index" };
  },
  onShareTimeline() {
    return { title: "一起来学最地道的法语" };
  },
});
