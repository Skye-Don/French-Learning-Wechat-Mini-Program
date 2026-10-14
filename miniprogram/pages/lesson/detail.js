// 课时详情（简化版）：话题信息 + 选择背卡数量（5 张 / 10 张 / 全部）（PRD 5.3 /pages/lesson/detail?id=）
const api = require("../../utils/request");

Page({
  data: {
    loading: true,
    lesson: null,
    total: 0,
    lessonId: null,
    // 按钮文案与对应数量（按课时总卡数动态生成）
    btn5: null,   // "开始背 5 张"（总数 >= 5 时显示）
    btn10: null,  // "开始背 10 张" 或 "开始背全部（N 张）"
    count10: 0,
  },

  onLoad(options) {
    this.setData({ lessonId: options.id });
    Promise.all([
      api.get("/api/lessons/" + options.id),
      api.get("/api/lessons/" + options.id + "/flashcards"),
    ])
      .then(([lesson, cards]) => {
        const total = cards.total || 0;
        // 按钮规则：>=10 两档；5~9 一档 + 全部；<5 仅全部
        let btn5 = null, btn10 = null, count10 = 0;
        if (total >= 10) {
          btn5 = "开始背 5 张闪卡";
          btn10 = "开始背 10 张闪卡";
          count10 = 10;
        } else if (total >= 5) {
          btn5 = "开始背 5 张闪卡";
          btn10 = "开始背全部（" + total + " 张）";
          count10 = total;
        } else if (total > 0) {
          btn10 = "开始背全部（" + total + " 张）";
          count10 = total;
        }
        this.setData({ lesson, total, btn5, btn10, count10, loading: false });
        wx.setNavigationBarTitle({ title: lesson.title || "课时详情" });
      })
      .catch((err) => {
        this.setData({ loading: false });
        wx.showToast({ title: err.message, icon: "none" });
      });
  },

  onStartStudy(e) {
    if (!this.data.total) {
      wx.showToast({ title: "该课时暂无内容", icon: "none" });
      return;
    }
    const count = Number(e.currentTarget.dataset.count) || 0;
    wx.navigateTo({
      url: "/pages/flashcard/study?lesson_id=" + this.data.lessonId + "&count=" + count,
    });
  },
});
