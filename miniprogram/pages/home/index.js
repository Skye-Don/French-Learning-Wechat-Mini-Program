// 首页：等级入口 + 今日概览（PRD 5.4）
const api = require("../../utils/request");
const auth = require("../../utils/auth");
const { track } = require("../../utils/track");
const app = getApp();

Page({
  data: {
    loading: true,
    loadError: "",
    user: null,
    summary: null,
    goalPct: 0, // 今日目标完成百分比（进度条用）
    levels: [],
    showOptIn: false, // 敏感词 opt-in 弹窗（PRD 5.2）
    optInValue: null,
  },

  onLoad() {
    this.init();
  },

  onShow() {
    // V0 行为分析：首页曝光
    track("page_view", { page: "home" });
    // 从学习页返回时刷新统计
    if (!this.data.loading && this.data.user) {
      this.refreshSummary();
    }
  },

  init() {
    auth.ensureLogin()
      .then((user) => {
        this.setData({
          user,
          // PRD 5.2：新用户首次进入弹出敏感词汇 opt-in（只弹一次）
          showOptIn: app.consumeNewUserOptInFlag() && !user.sensitive_opt_in,
        });
        return Promise.all([this.refreshSummary(), this.loadLevels()]);
      })
      .catch((err) => {
        // PRD 5.1 异常处理：登录失败提示 + 重试按钮
        this.setData({ loading: false, loadError: err.message || "登录失败，请稍后重试" });
      });
  },

  refreshSummary() {
    return api.get("/api/user/today-summary").then((s) => {
      const goal = s.daily_goal || 20;
      const done = Math.min(s.cards_learned_today || 0, goal);
      this.setData({
        summary: s,
        goalPct: Math.round((done / goal) * 100),
        loading: false,
      });
    });
  },

  loadLevels() {
    return api.get("/api/levels").then((levels) => {
      this.setData({ levels });
    });
  },

  onRetry() {
    this.setData({ loading: true, loadError: "" });
    this.init();
  },

  onLevelTap(e) {
    const id = e.currentTarget.dataset.id;
    const lv = this.data.levels.find((l) => String(l.id) === String(id));
    if (lv && !lv.lesson_count) {
      wx.showToast({ title: "该等级暂无课时", icon: "none" });
      return;
    }
    track("level_select", { level_id: Number(id) });
    wx.navigateTo({ url: "/pages/level/detail?id=" + id });
  },

  onGoStudy() {
    track("page_view", { page: "learn_entry" });
    wx.switchTab({ url: "/pages/learn/index" });
  },

  // ---- 敏感词 opt-in（PRD 5.2）----
  onOptInChoose(e) {
    this.setData({ optInValue: e.currentTarget.dataset.v === "1" });
  },
  onOptInConfirm() {
    if (this.data.optInValue === null) {
      wx.showToast({ title: "请先选择一项", icon: "none" });
      return;
    }
    const v = this.data.optInValue;
    track("sensitive_opt_toggle", { value: v });
    api.post("/api/user/preferences/sensitive-opt-in", { sensitive_opt_in: v })
      .then(() => {
        this.setData({ showOptIn: false });
        this.data.user.sensitive_opt_in = v;
        wx.showToast({ title: v ? "已开启全部词汇" : "仅学习常规词汇", icon: "none" });
        this.loadLevels();
      })
      .catch((err) => wx.showToast({ title: err.message, icon: "none" }));
  },
  onOptInClose() {
    // PRD 5.2 异常处理：未选择默认不学敏感词（conservative default）
    this.setData({ showOptIn: false });
  },
});
