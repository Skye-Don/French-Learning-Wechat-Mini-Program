// 通用工具函数
module.exports = {
  /** 认识/不认识的结果 → 中文 */
  resultText(v) {
    return { correct: "认识", wrong: "不认识", skip: "跳过" }[v] || v;
  },

  /** 秒 → 「X 分 Y 秒」 */
  formatDuration(sec) {
    sec = Math.max(0, Math.round(sec));
    if (sec < 60) return sec + " 秒";
    return Math.floor(sec / 60) + " 分 " + (sec % 60) + " 秒";
  },

  /** 课时类型 → 图标 */
  lessonIcon(type) {
    return { vocabulary: "📇", grammar: "📐", listening: "🎧", speaking: "🗣️", culture: "🎭" }[type] || "📇";
  },

  /** 当前 YYYY-MM（打卡日历用） */
  currentMonth() {
    const d = new Date();
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0");
  },
};
