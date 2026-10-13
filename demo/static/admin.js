/* 极简内容后台：闪卡 CRUD + 统计（V0 Demo 专用） */
(function () {
  "use strict";

  // 后台为演示便捷，复用同一套 token 机制：先以固定设备号登录取得管理员身份标识
  var TOKEN = "";

  // 后台门禁钥匙：与服务端 DEMO_ADMIN_KEY 对应（默认 french-admin-2026）。
  // 这只是"预览版防君子"的门禁——钥匙在前端可见，不具备真实安全性。
  // 生产必须换 backend/ 的 AdminAccount + JWT + 审计日志那套。
  // 运维想改钥匙：服务端设环境变量 DEMO_ADMIN_KEY，前端在控制台执行
  //   localStorage.setItem("admin_key", "新钥匙")
  var ADMIN_KEY = localStorage.getItem("admin_key") || "french-admin-2026";
  var allCards = [];
  var lessons = [];

  function api(path, method, body) {
    var headers = { "Content-Type": "application/json", "X-Admin-Key": ADMIN_KEY };
    if (TOKEN) {
        headers["Authorization"] = "Bearer " + TOKEN;
        headers["X-Auth-Token"] = TOKEN;
    }
    return fetch("/api" + path, {
      method: method || "GET", headers: headers, body: body ? JSON.stringify(body) : undefined,
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (d) {
        if (!r.ok) throw new Error((d.error && d.error.message) || "请求失败 " + r.status);
        return d;
      });
    });
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function boot() {
    var device = localStorage.getItem("admin_device");
    if (!device) { device = "admin_" + Date.now().toString(36); localStorage.setItem("admin_device", device); }
    api("/auth/wx-login", "POST", { code: device, nickname: "内容管理员" }).then(function (d) {
      TOKEN = d.token;
      return Promise.all([loadStats(), loadLessons(), loadCards()]);
    }).catch(function (e) {
      document.getElementById("list").innerHTML = '<div class="empty" style="color:#D4837A">' + esc(e.message) + "</div>";
    });
  }

  function loadStats() {
    return api("/admin/stats").then(function (s) {
      document.getElementById("stats").innerHTML =
        stat(s.users, "注册用户") + stat(s.flashcards, "闪卡总数") +
        stat(s.lessons, "已发布课时") + stat(s.checkins_today, "今日打卡");
    });
  }
  function stat(n, label) {
    return '<div class="stat"><b>' + n + "</b><span>" + label + "</span></div>";
  }

  function loadLessons() {
    return api("/admin/lessons").then(function (d) {
      lessons = d.items;
      var opts = lessons.map(function (l) {
        return '<option value="' + l.id + '">' + esc(l.title) + "</option>";
      }).join("");
      document.getElementById("f_lesson").innerHTML = opts;
      document.getElementById("filterLesson").innerHTML =
        '<option value="">全部课时</option>' + opts;
    });
  }

  function loadCards() {
    return api("/admin/flashcards").then(function (d) {
      allCards = d.items;
      drawList();
    });
  }


  // CEFR 难度归一：历史库里存的是 1-5 整数，统一显示成 A1/A2/B1/B2
  var NUM_TO_CEFR = { 1: "A1", 2: "A2", 3: "B1", 4: "B2", 5: "B2" };
  function levelOf(c) {
    var v = c.difficulty;
    if (typeof v === "number" || (typeof v === "string" && /^\d+$/.test(v))) {
      return NUM_TO_CEFR[Number(v)] || "A1";
    }
    v = String(v || "").toUpperCase();
    return (["A1", "A2", "B1", "B2"].indexOf(v) > -1) ? v : "A1";
  }

  function drawList() {
    var q = (document.getElementById("q").value || "").toLowerCase();
    var lid = document.getElementById("filterLesson").value;
    var lvl = document.getElementById("filterLevel").value;
    var rows = allCards.filter(function (c) {
      if (lid && String(c.lesson_id) !== String(lid)) return false;
      if (lvl && String(levelOf(c)) !== lvl) return false;
      if (!q) return true;
      return (c.front_text + c.back_text).toLowerCase().indexOf(q) > -1;
    });

    if (!rows.length) {
      document.getElementById("list").innerHTML = '<div class="empty">没有匹配的闪卡</div>';
      return;
    }
    var html = "<table><thead><tr><th style='width:60px'>ID</th><th style='width:150px'>法语正面</th><th>中文释义</th><th style='width:110px'>标签</th><th style='width:64px'>难度</th><th style='width:90px'>状态</th><th style='width:110px'>操作</th></tr></thead><tbody>";
    rows.forEach(function (c) {
      var tags = (c.tags || []).map(function (t) {
        return '<span class="tag' + (t === "脏话" || t === "敏感" ? " warn" : "") + '">' + esc(t) + "</span>";
      }).join("");
      if (c.is_sensitive) tags += '<span class="tag warn">敏感</span>';
      html += "<tr>" +
        "<td class='muted'>" + c.id + "</td>" +
        "<td class='fr'>" + esc(c.front_text) + "</td>" +
        "<td>" + esc(c.back_text) + "</td>" +
        "<td>" + tags + "</td>" +
        "<td><span class='tag lvl-" + levelOf(c) + "'>" + levelOf(c) + "</span></td>" +
        "<td>" + esc(c.status || "published") + "</td>" +
        "<td><button class='btn ghost' data-del='" + c.id + "' style='padding:5px 10px'>删除</button></td></tr>";
    });
    html += "</tbody></table>";
    var el = document.getElementById("list");
    el.innerHTML = html;
    el.querySelectorAll("[data-del]").forEach(function (b) {
      b.addEventListener("click", function () {
        if (!confirm("确定删除这张闪卡？")) return;
        api("/admin/flashcards/" + b.getAttribute("data-del"), "DELETE").then(function () {
          loadCards(); loadStats();
        }).catch(function (e) { alert(e.message); });
      });
    });
  }

  document.getElementById("q").addEventListener("input", drawList);
  document.getElementById("filterLesson").addEventListener("change", drawList);
  document.getElementById("filterLevel").addEventListener("change", drawList);

  document.getElementById("btnCreate").addEventListener("click", function () {
    var payload = {
      lesson_id: Number(document.getElementById("f_lesson").value),
      front_text: document.getElementById("f_front").value.trim(),
      back_text: document.getElementById("f_back").value.trim(),
      example_sentence: document.getElementById("f_ex_fr").value.trim() || null,
      example_translation: document.getElementById("f_ex_zh").value.trim() || null,
      tip: document.getElementById("f_tip").value.trim() || null,
      difficulty: document.getElementById("f_difficulty").value || "A1",
      tags: document.getElementById("f_tags").value.split(/[,，]/).map(function (s) { return s.trim(); }).filter(Boolean),
      is_sensitive: document.getElementById("f_sensitive").checked,
      status: document.getElementById("f_status").value,
      sort_order: 999,
    };
    if (!payload.front_text || !payload.back_text) { alert("法语正面与中文释义必填"); return; }
    api("/admin/flashcards", "POST", payload).then(function () {
      var m = document.getElementById("createMsg");
      m.textContent = "已保存 ✓";
      setTimeout(function () { m.textContent = ""; }, 2500);
      ["f_front", "f_back", "f_ex_fr", "f_ex_zh", "f_tip", "f_tags"].forEach(function (id) {
        document.getElementById(id).value = "";
      });
      loadCards(); loadStats();
    }).catch(function (e) { alert(e.message); });
  });

  boot();
})();
