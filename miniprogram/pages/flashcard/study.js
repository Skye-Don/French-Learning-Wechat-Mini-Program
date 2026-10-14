// 闪卡学习（PRD 5.5）：翻面 → 认识/不认识 → 记录进度 → 学完跳小结
// 两种模式：?lesson_id=xx 课时学习   ?mode=review 今日复习
const api = require("../../utils/request");

Page({
  data: {
    loading: true,
    cards: [],
    idx: 0,
    flipped: false,
    submitting: false,
    card: null,
    progressPct: 0,
  },

  session: null, // 学习会话（不进 data，避免 setData 开销）

  onLoad(options) {
    if (options.mode === "review") {
      this.loadReview();
    } else if (options.lesson_id) {
      // count：本次要背的数量（课时详情页选 5 张 / 10 张 / 全部；0 表示全部）
      this.loadLesson(options.lesson_id, Number(options.count) || 0);
    } else {
      wx.showToast({ title: "参数缺失", icon: "none" });
      setTimeout(() => wx.navigateBack(), 800);
    }
  },

  loadLesson(lessonId, count) {
    api.get("/api/lessons/" + lessonId + "/flashcards")
      .then((d) => {
        let items = d.items || [];
        // 随机取样 count 张：保证每次"背 5 张"内容不同，而不是永远前 N 张
        if (count && count < items.length) {
          items = items.slice().sort(() => Math.random() - 0.5).slice(0, count);
        }
        this.start(items, lessonId, "");
      })
      .catch((err) => this.fail(err));
  },

  loadReview() {
    api.get("/api/flashcard-progress/review-today")
      .then((d) => this.start(d.items, null, "今日复习"))
      .catch((err) => this.fail(err));
  },

  start(cards, lessonId, title) {
    if (!cards || !cards.length) {
      wx.showToast({ title: "该课时暂无内容", icon: "none" });
      setTimeout(() => wx.navigateBack(), 800);
      return;
    }
    this.session = {
      cards,
      lessonId,
      results: [],     // [{card, result}]
      startAt: Date.now(),
      lastFlipAt: Date.now(),
    };
    this.setData({ loading: false, cards, idx: 0, card: cards[0], flipped: false, progressPct: 0 });
  },

  fail(err) {
    this.setData({ loading: false });
    wx.showToast({ title: err.message, icon: "none" });
    setTimeout(() => wx.navigateBack(), 900);
  },

  /** 点击卡片翻面 */
  onFlip() {
    if (!this.session) return;
    this.session.lastFlipAt = Date.now();
    this.setData({ flipped: !this.data.flipped });
  },

  /** 认识 / 不认识（PRD 5.5：记录 learning_records + flashcard_progress UPSERT） */
  onAnswer(e) {
    if (this.data.submitting || !this.session) return;
    const result = e.currentTarget.dataset.v; // 'correct' | 'wrong'
    const card = this.data.card;
    this.setData({ submitting: true });

    api.post("/api/flashcard-progress", {
      flashcard_id: card.id,
      result,
      response_time_ms: Date.now() - this.session.lastFlipAt,
      lesson_id: this.session.lessonId || undefined,
    })
      .then((res) => {
        this.session.results.push({ card, result });
        this.session.lastCheckin = res.checkin || null;

        const next = this.data.idx + 1;
        if (next >= this.data.cards.length) {
          // 学完 → 小结页（把会话数据带过去）
          const app = getApp();
          app.globalData.lastStudySession = {
            results: this.session.results,
            startAt: this.session.startAt,
            checkin: this.session.lastCheckin,
          };
          wx.redirectTo({ url: "/pages/flashcard/summary" });
        } else {
          this.setData({
            idx: next,
            card: this.data.cards[next],
            flipped: false,
            submitting: false,
            progressPct: Math.round((next / this.data.cards.length) * 100),
          });
          this.session.lastFlipAt = Date.now();
        }
      })
      .catch((err) => {
        // PRD 5.5 异常处理：失败可重试（进度已落库的不受影响）
        this.setData({ submitting: false });
        wx.showToast({ title: err.message, icon: "none" });
      });
  },
});
