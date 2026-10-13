// 敏感词汇设置（PRD 5.2 / 5.5：sensitive_opt_in 修改）
const api = require("../../utils/request");

Page({
  data: {
    optIn: false,
    loaded: false,
  },

  onLoad() {
    api.get("/api/user/profile").then((p) => {
      this.setData({ optIn: !!p.sensitive_opt_in, loaded: true });
    }).catch((err) => wx.showToast({ title: err.message, icon: "none" }));
  },

  onChoose(e) {
    const v = e.currentTarget.dataset.v === "1";
    if (v === this.data.optIn) return;
    api.post("/api/user/preferences/sensitive-opt-in", { sensitive_opt_in: v })
      .then(() => {
        this.setData({ optIn: v });
        wx.showToast({ title: "已保存", icon: "success" });
      })
      .catch((err) => wx.showToast({ title: err.message, icon: "none" }));
  },
});
