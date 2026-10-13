// 打卡日历（PRD 5.6 / 8.3 GET /api/checkins/calendar）
const api = require("../../utils/request");
const util = require("../../utils/util");

Page({
  data: {
    month: "",
    monthLabel: "",
    weeks: ["一", "二", "三", "四", "五", "六", "日"],
    cells: [],   // [{day, on, today, empty}]
    checkinCount: 0,
    streakDays: 0,
  },

  onLoad() {
    this.load(util.currentMonth());
  },

  load(month) {
    api.get("/api/checkins/calendar?month=" + month).then((d) => {
      const days = {};
      d.items.forEach((i) => { days[i.checkin_date] = i; });

      const y = Number(month.slice(0, 4));
      const m = Number(month.slice(5, 7));
      const first = new Date(y, m - 1, 1).getDay();       // 0=周日
      const start = (first + 6) % 7;                       // 周一为第一列
      const total = new Date(y, m, 0).getDate();
      const now = new Date();
      const todayKey = now.getFullYear() + "-" + String(now.getMonth() + 1).padStart(2, "0") + "-" + String(now.getDate()).padStart(2, "0");

      const cells = [];
      for (let i = 0; i < start; i++) cells.push({ empty: true });
      for (let dd = 1; dd <= total; dd++) {
        const key = y + "-" + String(m).padStart(2, "0") + "-" + String(dd).padStart(2, "0");
        cells.push({ day: dd, on: !!days[key], today: key === todayKey });
      }

      this.setData({
        month,
        monthLabel: y + " 年 " + m + " 月",
        cells,
        checkinCount: d.items.length,
      });

      // streak 从 profile 拿
      api.get("/api/user/profile").then((p) => this.setData({ streakDays: p.streak_days })).catch(() => {});
    }).catch((err) => wx.showToast({ title: err.message, icon: "none" }));
  },

  onPrevMonth() {
    const [y, m] = this.data.month.split("-").map(Number);
    const d = new Date(y, m - 2, 1);
    this.load(d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0"));
  },
  onNextMonth() {
    const [y, m] = this.data.month.split("-").map(Number);
    const d = new Date(y, m, 1);
    this.load(d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0"));
  },
});
