// 等级详情：该等级下已发布课时列表（PRD 5.3 路由 /pages/level/detail?id=）
const api = require("../../utils/request");

Page({
  data: {
    loading: true,
    lessons: [],
    levelId: null,
  },

  onLoad(options) {
    this.setData({ levelId: options.id });
    this.load(options.id);
  },

  load(id) {
    api.get("/api/levels/" + id + "/lessons")
      .then((lessons) => this.setData({ lessons, loading: false }))
      .catch((err) => {
        this.setData({ loading: false });
        wx.showToast({ title: err.message, icon: "none" });
      });
  },

  onLessonTap(e) {
    const id = e.currentTarget.dataset.id;
    const ls = this.data.lessons.find((l) => String(l.id) === String(id));
    if (ls && !ls.card_count) {
      wx.showToast({ title: "该课时暂无内容", icon: "none" });
      return;
    }
    wx.navigateTo({ url: "/pages/lesson/detail?id=" + id });
  },
});
