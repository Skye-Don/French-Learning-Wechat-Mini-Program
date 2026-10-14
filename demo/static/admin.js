/* 管理后台（V0 Demo）：登录 + 数据概览 + 闪卡管理 */
(function () {
  "use strict";

  var TOKEN = "";          // 小程序侧用户 token（供管理员身份调用业务接口）
  var ADMIN_KEY = "";      // 登录成功后由 /api/admin/login 签发的门禁钥匙
  var allCards = [];
  var lessons = [];

  // ---------- 基础工具 ----------
  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function api(path, method, body) {
    var headers = { "Content-Type": "application/json" };
    if (ADMIN_KEY) headers["X-Admin-Key"] = ADMIN_KEY;
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

  // ---------- 登录 ----------
  function showLogin() {
    $("loginView").style.display = "flex";
    $("appView").style.display = "none";
  }
  function showApp(nickname) {
    $("loginView").style.display = "none";
    $("appView").style.display = "block";
    $("whoami").textContent = "👤 " + nickname;
  }

  function doLogin(username, password) {
    return fetch("/api/admin/login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: username, password: password }),
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (d) {
        if (!r.ok) throw new Error((d.error && d.error.message) || "登录失败 " + r.status);
        return d;
      });
    });
  }

  function afterLogin(d) {
    ADMIN_KEY = d.token;
    TOKEN = "";
    sessionStorage.setItem("admin_session", JSON.stringify({ token: d.token, nickname: d.nickname }));
    showApp(d.nickname);
    bootData();
  }

  $("loginForm").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var u = $("loginUser").value.trim();
    var p = $("loginPass").value;
    if (!u || !p) { $("loginMsg").textContent = "请输入用户名和密码"; return; }
    $("btnLogin").disabled = true;
    $("btnLogin").textContent = "登录中…";
    doLogin(u, p).then(afterLogin).catch(function (e) {
      $("loginMsg").textContent = e.message;
    }).then(function () {
      $("btnLogin").disabled = false;
      $("btnLogin").textContent = "登 录";
    });
  });

  $("btnLogout").addEventListener("click", function () {
    sessionStorage.removeItem("admin_session");
    ADMIN_KEY = ""; TOKEN = "";
    $("loginPass").value = "";
    $("loginMsg").textContent = "";
    showLogin();
  });

  // ---------- Tab 切换 ----------
  var tabs = document.querySelectorAll("nav button");
  tabs.forEach(function (b) {
    b.addEventListener("click", function () {
      tabs.forEach(function (x) { x.classList.remove("on"); });
      b.classList.add("on");
      document.querySelectorAll("section.tab").forEach(function (s) { s.classList.remove("on"); });
      $("tab-" + b.getAttribute("data-tab")).classList.add("on");
      if (b.getAttribute("data-tab") === "overview") loadAnalytics();
    });
  });

  // ---------- 数据概览 ----------
  function loadAnalytics() {
    return api("/analytics/dashboard").then(function (d) { drawOverview(d); });
  }

  function drawOverview(d) {
    $("ovStats").innerHTML =
      ovStat(d.total_users, "注册用户") +
      ovStat(d.active_users_1d, "1 日活跃") +
      ovStat(d.active_users_7d, "7 日活跃") +
      ovStat(d.events_7d, "7 日行为事件");

    // 热门闪卡：id 映射成法语原文
    var byId = {};
    allCards.forEach(function (c) { byId[c.id] = c; });
    var top = d.top_cards_7d || [];
    if (!top.length) {
      $("ovTop").innerHTML = '<div class="empty">近 7 日暂无学习行为数据</div>';
    } else {
      var html = "<table><thead><tr><th style='width:52px'>排名</th><th>闪卡</th><th style='width:80px'>学习次数</th></tr></thead><tbody>";
      top.forEach(function (t, i) {
        var c = byId[t.flashcard_id];
        html += "<tr><td class='muted'>" + (i + 1) + "</td>" +
          "<td class='fr'>" + esc(c ? c.front_text : "#" + t.flashcard_id) +
          (c ? " <span class='muted' style='font-weight:400'>" + esc(c.back_text) + "</span>" : "") + "</td>" +
          "<td><b>" + t.count + "</b></td></tr>";
      });
      $("ovTop").innerHTML = html + "</tbody></table>";
    }

    // 等级分布条形图
    var lv = d.level_distribution || [];
    var max = 1;
    lv.forEach(function (x) { if (x.count > max) max = x.count; });
    if (!lv.length) {
      $("ovLevels").innerHTML = '<div class="empty">暂无用户数据</div>';
    } else {
      $("ovLevels").innerHTML = lv.map(function (x) {
        var pct = Math.round(x.count * 100 / max);
        return "<div class='bar-row'><span class='bl'>" + esc(x.level) + "</span>" +
          "<span class='bar'><i style='width:" + pct + "%'></i></span>" +
          "<span class='bn'>" + x.count + "</span></div>";
      }).join("");
    }
  }
  function ovStat(n, label) {
    return '<div class="stat"><b>' + n + "</b><span>" + label + "</span></div>";
  }

  // ---------- 闪卡管理（原有功能）----------
  function bootData() {
    var device = localStorage.getItem("admin_device");
    if (!device) { device = "admin_" + Date.now().toString(36); localStorage.setItem("admin_device", device); }
    api("/auth/wx-login", "POST", { code: device, nickname: "内容管理员" }).then(function (d) {
      TOKEN = d.token;
      return Promise.all([loadStats(), loadLessons(), loadCards(), loadAnalytics()]);
    }).catch(function (e) {
      $("list").innerHTML = '<div class="empty" style="color:#D4837A">' + esc(e.message) + "</div>";
    });
  }

  function loadStats() {
    return api("/admin/stats").then(function (s) {
      $("stats").innerHTML =
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
      $("f_lesson").innerHTML = opts;
      $("filterLesson").innerHTML = '<option value="">全部课时</option>' + opts;
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
    var q = ($("q").value || "").toLowerCase();
    var lid = $("filterLesson").value;
    var lvl = $("filterLevel").value;
    var rows = allCards.filter(function (c) {
      if (lid && String(c.lesson_id) !== String(lid)) return false;
      if (lvl && String(levelOf(c)) !== lvl) return false;
      if (!q) return true;
      return (c.front_text + c.back_text).toLowerCase().indexOf(q) > -1;
    });

    if (!rows.length) {
      $("list").innerHTML = '<div class="empty">没有匹配的闪卡</div>';
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
    var el = $("list");
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

  $("q").addEventListener("input", drawList);
  $("filterLesson").addEventListener("change", drawList);
  $("filterLevel").addEventListener("change", drawList);

  $("btnCreate").addEventListener("click", function () {
    var payload = {
      lesson_id: Number($("f_lesson").value),
      front_text: $("f_front").value.trim(),
      back_text: $("f_back").value.trim(),
      example_sentence: $("f_ex_fr").value.trim() || null,
      example_translation: $("f_ex_zh").value.trim() || null,
      tip: $("f_tip").value.trim() || null,
      difficulty: $("f_difficulty").value || "A1",
      tags: $("f_tags").value.split(/[,，]/).map(function (s) { return s.trim(); }).filter(Boolean),
      is_sensitive: $("f_sensitive").checked,
      status: $("f_status").value,
      sort_order: 999,
    };
    if (!payload.front_text || !payload.back_text) { alert("法语正面与中文释义必填"); return; }
    api("/admin/flashcards", "POST", payload).then(function () {
      var m = $("createMsg");
      m.textContent = "已保存 ✓";
      setTimeout(function () { m.textContent = ""; }, 2500);
      ["f_front", "f_back", "f_ex_fr", "f_ex_zh", "f_tip", "f_tags"].forEach(function (id) {
        $(id).value = "";
      });
      loadCards(); loadStats();
    }).catch(function (e) { alert(e.message); });
  });

  // ---------- 启动：已登录（sessionStorage 有效）直接进后台，否则显示登录页 ----------
  (function init() {
    var saved = null;
    try { saved = JSON.parse(sessionStorage.getItem("admin_session") || "null"); } catch (e) { /* ignore */ }
    if (saved && saved.token) {
      ADMIN_KEY = saved.token;
      showApp(saved.nickname || "admin");
      bootData();
    } else {
      showLogin();
    }
  })();
})();
