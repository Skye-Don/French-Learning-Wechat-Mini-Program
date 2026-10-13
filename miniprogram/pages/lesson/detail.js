// 课时详情：课时信息 + 闪卡预览 + 开始学习入口（PRD 5.3 /pages/lesson/detail?id=）
const api = require("../../utils/request");

Page({
  data: {
    loading: true,
    lesson: null,
    cards: [],
    total: 0,
    lessonId: null,
  },

  onLoad(options) {
    this.setData({ lessonId: options.id });
    Promise.all([
      api.get("/api/lessons/" + options.id),
      api.get("/api/lessons/" + options.id + "/flashcards"),
    ])
      .then(([lesson, cards]) => {
        this.setData({ lesson, cards: cards.items, total: cards.total, loading: false });
        wx.setNavigationBarTitle({ title: lesson.title || "课时详情" });
      })
      .catch((err) => {
        this.setData({ loading: false });
        wx.showToast({ title: err.message, icon: "none" });
      });
  },

  onStartStudy() {
    if (!this.data.total) {
      wx.showToast({ title: "该课时暂无内容", icon: "none" });
      return;
    }
    wx.navigateTo({ url: "/pages/flashcard/study?lesson_id=" + this.data.lessonId });
  },
});
