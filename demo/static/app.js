/* ============================================================
   法语学习小程序 · H5 预览版前端逻辑
   API 路径与 PRD 第 8 章完全一致，便于原样迁移到 miniprogram/
   ============================================================ */
(function () {
  "use strict";

  var API = "/api";
  var TOKEN_KEY = "fr_token";
  var DEVICE_KEY = "fr_device";

  var state = {
    token: localStorage.getItem(TOKEN_KEY) || "",
    user: null,
    summary: null,
    levels: [],
    lessons: {},      // levelId -> lessons
    lessonCards: {},  // lessonId -> cards
    study: null,      // 闪卡学习会话
  };

  // ------------------------------------------------------------------ 工具
  function $(sel) { return document.querySelector(sel); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function toast(msg) {
    var t = $("#toast");
    t.textContent = msg;
    t.hidden = false;
    clearTimeout(t._tm);
    t._tm = setTimeout(function () { t.hidden = true; }, 1800);
  }

  function api(path, method, body) {
    var headers = { "Content-Type": "application/json" };
    if (state.token) {
        headers["Authorization"] = "Bearer " + state.token;
        // 兼容会剥离 Authorization 的网关；生产环境只用 Authorization 即可
        headers["X-Auth-Token"] = state.token;
    }
    return fetch(API + path, {
      method: method || "GET",
      headers: headers,
      body: body ? JSON.stringify(body) : undefined,
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (d) {
        if (!r.ok) {
          var msg = (d.error && d.error.message) || ("请求失败 " + r.status);
          throw new Error(msg);
        }
        return d;
      });
    });
  }

  // ------------------------------------------------------------------ 登录
  // ⚠️ H5 版没有 wx.login，用本地 device_id 冒充 openid 完成"模拟登录"。
  // 真机小程序里这段替换为：wx.login() 拿 code → POST /api/auth/wx-login
  // （见 miniprogram/utils/auth.js，openid 只能由服务端换取，绝不能前端传）
  function ensureLogin() {
    var device = localStorage.getItem(DEVICE_KEY);
    if (!device) {
      device = "d" + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
      localStorage.setItem(DEVICE_KEY, device);
    }
    return api("/auth/wx-login", "POST", { code: device, nickname: "法语学习者" })
      .then(function (d) {
        state.token = d.token;
        state.user = d.user;
        localStorage.setItem(TOKEN_KEY, d.token);
        // PRD 5.2：新用户（且未做过 opt-in 选择）弹出敏感词汇确认
        if (d.is_new_user && !d.user.sensitive_opt_in) {
          showOptInModal();
        }
        return d;
      });
  }

  // ------------------------------------------------------------------ 弹窗
  function closeModal() { $("#modalRoot").hidden = true; $("#modalRoot").innerHTML = ""; }

  function showOptInModal() {
    var root = $("#modalRoot");
    root.innerHTML =
      '<div class="modal">' +
      "<h3>关于学习内容的设置</h3>" +
      "<p>法语日常口语里包含一些脏话与冒犯性表达。了解它们有助于听懂真实对话，" +
      "但你可能并不想学。你希望包含这类内容吗？</p>" +
      '<div class="opt-item" data-opt="1"><div class="opt-title">学习全部词汇</div>' +
      '<div class="opt-desc">包含脏话、俗语等真实口语表达（可随时在「我的」里改）</div></div>' +
      '<div class="opt-item" data-opt="0"><div class="opt-title">仅学习常规词汇</div>' +
      '<div class="opt-desc">跳过所有被标记为敏感的内容（推荐）</div></div>' +
      "</div>";
    root.hidden = false;
    root.querySelectorAll("[data-opt]").forEach(function (el) {
      el.addEventListener("click", function () {
        var v = el.getAttribute("data-opt") === "1";
        api("/user/preferences/sensitive-opt-in", "POST", { sensitive_opt_in: v })
          .then(function () {
            state.user.sensitive_opt_in = v;
            closeModal();
            toast(v ? "已开启：包含敏感词汇" : "已设置：仅常规词汇");
            render();
          })
          .catch(function (e) { toast(e.message); });
      });
    });
  }

  // ------------------------------------------------------------------ 路由
  var TAB_ROUTES = ["#/home", "#/learn", "#/profile"];

  function parseHash() {
    var h = location.hash || "#/home";
    var qi = h.indexOf("?");
    var path = qi > -1 ? h.slice(0, qi) : h;
    var query = {};
    if (qi > -1) {
      h.slice(qi + 1).split("&").forEach(function (kv) {
        var p = kv.split("=");
        if (p[0]) query[decodeURIComponent(p[0])] = decodeURIComponent(p[1] || "");
      });
    }
    return { path: path, query: query };
  }

  function go(hash) {
    if (location.hash === hash) render(); else location.hash = hash;
  }

  function render() {
    var r = parseHash();
    var screen = $("#screen");
    var isTab = TAB_ROUTES.indexOf(r.path) > -1;

    $("#tabbar").hidden = !isTab;
    $("#navBack").hidden = isTab;
    if (isTab) {
      document.querySelectorAll(".tab").forEach(function (t) {
        t.classList.toggle("active", t.getAttribute("data-route") === r.path);
      });
    }

    var titles = {
      "#/home": "Bonjour !", "#/learn": "学习", "#/profile": "我的",
      "#/level": "选择课时", "#/lesson": "课时详情", "#/study": "闪卡学习",
      "#/calendar": "打卡日历", "#/reminder": "学习提醒", "#/sensitive": "敏感词汇设置",
    };
    $("#navTitle").textContent = titles[r.path] || "Bonjour !";

    switch (r.path) {
      case "#/home": return renderHome(screen);
      case "#/learn": return renderLearn(screen);
      case "#/profile": return renderProfile(screen);
      case "#/level": return renderLevel(screen, r.query.id);
      case "#/lesson": return renderLesson(screen, r.query.id);
      case "#/study":
        // 复习模式直接复用已构建好的会话；否则按 lesson_id 取卡
        if (r.query.mode === "review" && state.study) return drawStudy(screen);
        return renderStudy(screen, r.query.lesson_id);
      case "#/calendar": return renderCalendar(screen);
      case "#/reminder": return renderReminder(screen);
      case "#/sensitive": return renderSensitive(screen);
      default: location.hash = "#/home";
    }
  }

  function skeleton(n) {
    var s = "";
    for (var i = 0; i < (n || 3); i++) s += '<div class="skel skel-card"></div>';
    return s;
  }

  // ------------------------------------------------------------------ 首页
  function renderHome(el) {
    el.innerHTML = '<div class="page">' + skeleton(3) + "</div>";
    Promise.all([
      api("/user/today-summary"),
      api("/levels"),
    ]).then(function (res) {
      state.summary = res[0];
      state.levels = res[1];
      var s = res[0];
      var goal = s.daily_goal || 20;
      var done = Math.min(s.cards_learned_today || 0, goal);
      var pct = goal ? done / goal : 0;
      var C = 2 * Math.PI * 27;

      var html = '<div class="page">';
      html += '<div class="hero">';
      html += '<div class="hero-top"><div><div class="hero-hi">Bonjour !</div>' +
        '<div class="hero-sub">' + (s.checked_in ? "今天已打卡，继续保持" : "今天还没开始，来学几张卡吧") + "</div></div>" +
        '<div class="avatar">🇫🇷</div></div>';
      html += '<div class="goal-row"><div class="ring">' +
        '<svg width="62" height="62">' +
        '<circle cx="31" cy="31" r="27" stroke="rgba(255,255,255,.28)" stroke-width="5" fill="none"/>' +
        '<circle cx="31" cy="31" r="27" stroke="#fff" stroke-width="5" fill="none" stroke-linecap="round" ' +
        'stroke-dasharray="' + C.toFixed(1) + '" stroke-dashoffset="' + (C * (1 - pct)).toFixed(1) + '"/>' +
        "</svg></div>";
      html += '<div class="goal-text">今日目标<b>' + done + "</b> / " + goal + " 张卡片";
      html += '<div style="font-size:12px;opacity:.85">' +
        (done >= goal ? "今日目标已完成 🎉" : "还差 " + (goal - done) + " 张") + "</div>";
      html += '<div class="streak-pill">🔥 连续打卡 ' + (s.streak_days || 0) + " 天</div>";
      html += "</div></div></div>";

      html += '<div class="section-title">选择等级</div><div class="level-grid">';
      res[1].forEach(function (lv) {
        html += '<div class="level-card' + (lv.lesson_count ? "" : " zero") + '" data-act="level" data-id="' + lv.id + '">' +
          '<div class="corner"></div>' +
          '<div class="level-code">' + esc(lv.code) + "</div>" +
          '<div class="level-name">' + esc(lv.name.split(" - ")[1] || lv.name) + "</div>" +
          '<div class="level-desc">' + esc(lv.description) + "</div>" +
          '<div class="level-count">📚 ' + lv.lesson_count + " 个课时</div></div>";
      });
      html += "</div>";

      html += '<div class="section-title">即将上线</div><div class="coming">';
      html += '<div class="coming-item"><span>🎧 听力训练</span><span class="tag">V1 敬请期待</span></div>';
      html += '<div class="coming-item"><span>🤖 AI 对话练习</span><span class="tag">V1 敬请期待</span></div>';
      html += '<div class="coming-item"><span>🗣️ 跟读发音评分</span><span class="tag">V1 敬请期待</span></div>';
      html += '<div class="coming-item"><span>🏆 学习排行榜</span><span class="tag">V1 敬请期待</span></div>';
      html += "</div></div>";

      el.innerHTML = html;
    }).catch(function (e) {
      el.innerHTML = '<div class="page"><div class="empty"><div class="empty-ico">📡</div>' +
        '<div class="empty-txt">' + esc(e.message) + '</div>' +
        '<div style="margin-top:16px"><button class="btn" data-act="retry">点击重试</button></div></div></div>';
    });
  }

  // ------------------------------------------------------------------ 学习页
  function renderLearn(el) {
    el.innerHTML = '<div class="page">' + skeleton(3) + "</div>";
    Promise.all([
      api("/levels"),
      api("/flashcard-progress/review-today"),
    ]).then(function (res) {
      var levels = res[0];
      var review = res[1];
      var html = '<div class="page">';

      html += '<div class="card"><div class="between"><div>' +
        '<div style="font-size:14px;font-weight:600">今日待复习</div>' +
        '<div class="muted" style="font-size:12px;margin-top:4px">按记忆曲线，今天该看这些</div></div>' +
        '<div style="font-size:26px;font-weight:700;color:var(--fr-blue)">' + review.total + "</div></div>";
      if (review.total > 0) {
        html += '<button class="btn block" style="margin-top:14px" data-act="review">开始复习</button>';
      } else {
        html += '<div class="muted" style="font-size:12px;margin-top:10px">暂无到期卡片，去学个新课时吧</div>';
      }
      html += "</div>";

      html += '<div class="section-title">按等级学习</div>';
      levels.forEach(function (lv) {
        html += '<div class="card" style="padding:14px 16px;margin-bottom:10px">';
        html += '<div class="between" data-act="level" data-id="' + lv.id + '" style="cursor:pointer">' +
          "<div><b>" + esc(lv.code) + "</b> <span class='muted' style='font-size:12px'>" +
          esc(lv.name.split(" - ")[1] || lv.name) + "</span>" +
          '<span class="badge">' + lv.lesson_count + " 课时</span></div>" +
          '<span class="lesson-arrow">›</span></div>';
        html += "</div>";
      });
      html += "</div>";
      el.innerHTML = html;
    }).catch(function (e) { toast(e.message); });
  }

  // ------------------------------------------------------------------ 等级详情
  function renderLevel(el, id) {
    el.innerHTML = '<div class="page">' + skeleton(2) + "</div>";
    api("/levels/" + id + "/lessons").then(function (lessons) {
      state.lessons[id] = lessons;
      var html = '<div class="page"><div class="card">';
      if (!lessons.length) {
        html += '<div class="empty"><div class="empty-ico">📭</div><div class="empty-txt">该等级暂无已发布课时</div></div>';
      } else {
        lessons.forEach(function (ls) {
          html += '<div class="lesson-item" data-act="lesson" data-id="' + ls.id + '">' +
            '<div class="lesson-ico">' + (iconForType(ls.lesson_type)) + "</div>" +
            '<div class="lesson-main"><div class="lesson-title">' + esc(ls.title) + "</div>" +
            '<div class="lesson-meta">' + esc(ls.description || "") + "</div>" +
            '<div class="lesson-meta" style="margin-top:5px">📇 ' + ls.card_count + " 张卡片</div></div>" +
            '<span class="lesson-arrow">›</span></div>';
        });
      }
      html += "</div></div>";
      el.innerHTML = html;
    }).catch(function (e) { toast(e.message); });
  }

  function iconForType(t) {
    return { vocabulary: "📇", grammar: "📐", listening: "🎧", speaking: "🗣️", culture: "🎭" }[t] || "📇";
  }

  // ------------------------------------------------------------------ 课时详情
  function renderLesson(el, id) {
    el.innerHTML = '<div class="page">' + skeleton(2) + "</div>";
    Promise.all([api("/lessons/" + id), api("/lessons/" + id + "/flashcards")]).then(function (res) {
      var lesson = res[0], cards = res[1];
      var html = '<div class="page">';
      html += '<div class="card"><div style="font-size:16px;font-weight:600">' + esc(lesson.title) + "</div>" +
        '<div class="muted" style="font-size:12.5px;margin-top:8px;line-height:1.7">' + esc(lesson.description || "") + "</div>" +
        '<div style="margin-top:12px;font-size:12px" class="muted">共 ' + cards.total + " 张卡片</div></div>";

      html += '<div class="card"><div style="font-size:13px;font-weight:600;margin-bottom:6px">卡片预览</div>';
      cards.items.slice(0, 8).forEach(function (c) {
        html += '<div style="padding:9px 0;border-bottom:1px solid var(--line);font-size:13.5px">' +
          esc(c.front_text) + ' <span class="muted" style="font-size:12px">— ' + esc(c.back_text.slice(0, 22)) + "…</span></div>";
      });
      if (cards.total > 8) html += '<div class="muted" style="font-size:12px;padding-top:10px">…还有 ' + (cards.total - 8) + " 张</div>";
      html += "</div>";
      html += '<button class="btn block" data-act="start-study" data-id="' + id + '">开始学习（' + cards.total + " 张）</button>";
      html += "</div>";
      el.innerHTML = html;
    }).catch(function (e) { toast(e.message); });
  }

  // ------------------------------------------------------------------ 闪卡学习
  function renderStudy(el, lessonId) {
    api("/lessons/" + lessonId + "/flashcards").then(function (d) {
      if (!d.items.length) {
        el.innerHTML = '<div class="page"><div class="empty"><div class="empty-ico">📭</div>' +
          '<div class="empty-txt">该课时暂无内容</div></div></div>';
        return;
      }
      state.study = {
        cards: d.items, idx: 0, flipped: false, results: [], startAt: Date.now(),
        lessonId: Number(lessonId), lessonTitle: "",
      };
      drawStudy(el);
    }).catch(function (e) { toast(e.message); });
  }

  function startReview() {
    api("/flashcard-progress/review-today").then(function (d) {
      if (!d.items.length) { toast("今天没有待复习卡片"); return; }
      state.study = { cards: d.items, idx: 0, flipped: false, results: [], startAt: Date.now(), lessonId: null, lessonTitle: "今日复习" };
      // 注意：复习没有 lesson_id，用 mode=review 标记，避免走到课时取卡逻辑
      location.hash = "#/study?mode=review";
    }).catch(function (e) { toast(e.message); });
  }

  function drawStudy(el) {
    var st = state.study;
    var c = st.cards[st.idx];
    var pct = (st.idx / st.cards.length) * 100;

    var html = '<div class="study-wrap">';
    html += '<div class="study-progress"><div class="progress-bar"><i style="width:' + pct + '%"></i></div>' +
      '<span class="progress-txt">' + (st.idx + 1) + " / " + st.cards.length + "</span></div>";

    html += '<div class="flip-card' + (st.flipped ? " flipped" : "") + '" data-act="flip"><div class="flip-inner">';
    // 正面：法语
    html += '<div class="flip-face"><div class="fc-front">' + esc(c.front_text) + "</div>" +
      '<div class="fc-hint">点击卡片翻面看释义</div>' +
      (c.tags && c.tags.length ? '<div style="margin-top:12px;font-size:11.5px;color:var(--text2)">' +
        c.tags.map(function (t) { return "#" + esc(t); }).join(" ") + "</div>" : "") + "</div>";
    // 背面：中文 + 例句 + 地道提示
    html += '<div class="flip-face flip-back">' +
      (c.is_sensitive ? '<div class="fc-tag">敏感词汇</div>' : "") +
      '<div class="fc-back-main">' + esc(c.front_text) + "</div>" +
      '<div class="fc-back-sub">' + esc(c.back_text) + "</div>";
    if (c.example_sentence) {
      html += '<div class="fc-example"><div class="fc-ex-fr">' + esc(c.example_sentence) + "</div>" +
        (c.example_translation ? '<div class="fc-ex-zh">' + esc(c.example_translation) + "</div>" : "") + "</div>";
    }
    if (c.tip) html += '<div class="fc-tip">💡 ' + esc(c.tip) + "</div>";
    html += "</div></div></div>";

    html += '<div class="study-actions">' +
      '<button class="btn btn-wrong" data-act="answer" data-v="wrong">不认识</button>' +
      '<button class="btn btn-right" data-act="answer" data-v="correct">认识</button></div>';
    html += "</div>";
    el.innerHTML = html;
  }

  function answerCard(v) {
    var st = state.study;
    var c = st.cards[st.idx];
    var btn = document.querySelectorAll('[data-act="answer"]');
    btn.forEach(function (b) { b.disabled = true; });

    api("/flashcard-progress", "POST", {
      flashcard_id: c.id,
      result: v,
      response_time_ms: Date.now() - (st.lastFlipAt || st.startAt),
      lesson_id: st.lessonId || undefined,
    }).then(function (d) {
      st.results.push({ card: c, result: v });
      st.idx += 1;
      st.flipped = false;
      st.lastCheckin = d.checkin;
      if (st.idx >= st.cards.length) {
        drawSummary($("#screen"), d.checkin && d.checkin.created);
      } else {
        st.lastFlipAt = Date.now();
        drawStudy($("#screen"));
      }
    }).catch(function (e) {
      toast(e.message);
      btn.forEach(function (b) { b.disabled = false; });
    });
  }

  // ------------------------------------------------------------------ 学习小结
  function drawSummary(el, justCheckedIn) {
    var st = state.study;
    var total = st.results.length;
    var ok = st.results.filter(function (r) { return r.result === "correct"; }).length;
    var pct = total ? Math.round((ok / total) * 100) : 0;
    var sec = Math.round((Date.now() - st.startAt) / 1000);
    var C = 2 * Math.PI * 62;

    var html = '<div class="summary-wrap">';
    html += '<div style="font-size:18px;font-weight:600;margin-top:10px">学习完成 !</div>';
    html += '<div class="muted" style="font-size:12.5px;margin-top:6px">本次共学习 ' + total + " 张卡片</div>";

    html += '<div class="sum-ring"><svg width="150" height="150">' +
      '<circle cx="75" cy="75" r="62" stroke="#E8E5E1" stroke-width="10" fill="none"/>' +
      '<circle cx="75" cy="75" r="62" stroke="#5B7FA5" stroke-width="10" fill="none" stroke-linecap="round" ' +
      'stroke-dasharray="' + C.toFixed(1) + '" stroke-dashoffset="' + (C * (1 - pct / 100)).toFixed(1) +
      '" style="transition:stroke-dashoffset 1s ease"/></svg>' +
      '<div class="pct"><b>' + pct + "%</b><span>正确率</span></div></div>";

    html += '<div class="sum-stats">' +
      '<div class="stat"><b>' + ok + '</b><span>认识</span></div>' +
      '<div class="stat"><b>' + (total - ok) + '</b><span>不认识</span></div>' +
      '<div class="stat"><b>' + Math.max(1, Math.round(sec / 60)) + '</b><span>用时(分)</span></div></div>';

    html += '<div class="card" style="text-align:left"><div style="font-size:13px;font-weight:600;margin-bottom:6px">本次回顾</div><div class="review-list">';
    st.results.forEach(function (r) {
      html += '<div class="review-item"><span class="review-dot ' + (r.result === "correct" ? "ok" : "no") + '">' +
        (r.result === "correct" ? "✓" : "✕") + "</span>" +
        '<div><div class="review-fr">' + esc(r.card.front_text) + "</div>" +
        '<div class="muted" style="font-size:12px;margin-top:2px">' + esc(r.card.back_text.slice(0, 30)) + "</div></div></div>";
    });
    html += "</div></div>";

    html += '<button class="btn block" data-act="back-learn" style="margin-top:8px">返回学习</button>' +
      '<button class="btn block ghost" data-act="retry-lesson" style="margin-top:10px">再学一遍</button>';
    html += "</div>";
    el.innerHTML = html;

    if (justCheckedIn) setTimeout(showCheckinAnim, 400);
  }

  function showCheckinAnim() {
    var streak = (state.study && state.study.lastCheckin && state.study.lastCheckin.streak_days) || 1;
    var box = document.createElement("div");
    box.className = "checkin-mask";
    box.innerHTML = '<div class="checkin-card"><div class="flame">🔥</div>' +
      '<div class="checkin-title">打卡成功</div>' +
      '<div class="checkin-desc">已连续学习 <b>' + streak + "</b> 天<br/>明天继续，别断掉哦</div>" +
      '<button class="btn" style="margin-top:16px" data-act="close-checkin">好的</button></div>';
    document.querySelector(".phone-frame").appendChild(box);
  }

  // ------------------------------------------------------------------ 我的
  function renderProfile(el) {
    el.innerHTML = '<div class="page">' + skeleton(2) + "</div>";
    api("/user/profile").then(function (p) {
      var html = '<div class="page">';
      html += '<div class="profile-head"><div class="avatar">🇫🇷</div><div>' +
        '<div class="p-name">' + esc(p.nickname || "法语学习者") + "</div>" +
        '<div class="p-level">当前等级：' + esc(p.current_level || "未设置") + "</div></div></div>";

      html += '<div class="stat-row" style="margin-top:12px">' +
        '<div class="stat"><b>' + p.total_study_days + "</b><span>学习天数</span></div>" +
        '<div class="stat"><b>' + p.total_cards_learned + "</b><span>累计卡片</span></div>" +
        '<div class="stat"><b>' + p.streak_days + "</b><span>连续打卡</span></div></div>";

      html += '<div class="menu">' +
        menuItem("📅", "打卡日历", "看看坚持了几天", "calendar") +
        menuItem("⚙️", "学习提醒", "每天定时提醒", "reminder") +
        menuItem("📝", "敏感词汇设置", p.sensitive_opt_in ? "已开启全部" : "仅常规词汇", "sensitive") +
        menuItem("📤", "分享给好友", "V1 开放", "share") +
        menuItem("📌", "添加到桌面", "V1 开放", "shortcut") +
        menuItem("ℹ️", "关于", "V0 框架版", "about") +
        "</div>";

      html += '<div style="text-align:center;margin-top:20px"><button class="btn ghost" data-act="reset">清空本机演示数据</button></div>';
      html += "</div>";
      el.innerHTML = html;
    }).catch(function (e) { toast(e.message); });
  }

  function menuItem(ico, label, extra, act) {
    return '<button class="menu-item" data-act="m-' + act + '"><span class="menu-ico">' + ico + "</span>" +
      '<span class="menu-label">' + label + '</span><span class="menu-extra">' + esc(extra) + "</span>" +
      '<span class="menu-arrow">›</span></button>';
  }

  // ------------------------------------------------------------------ 打卡日历
  function renderCalendar(el) {
    api("/checkins/calendar?month=" + currentMonth()).then(function (d) {
      var days = {};
      d.items.forEach(function (i) { days[i.checkin_date] = i; });
      var now = new Date();
      var y = Number(d.month.slice(0, 4)), m = Number(d.month.slice(5, 7));
      var first = new Date(y, m - 1, 1).getDay(); // 0=周日
      var total = new Date(y, m, 0).getDate();
      var t = new Date();
      var todayKey = t.getFullYear() + "-" + String(t.getMonth() + 1).padStart(2, "0") + "-" + String(t.getDate()).padStart(2, "0");

      var html = '<div class="page"><div class="card">';
      html += '<div class="cal-head"><b>' + y + " 年 " + m + " 月</b>" +
        '<span class="muted" style="font-size:12px">' + d.items.length + " 天已打卡</span></div>";
      html += '<div class="cal-grid">';
      ["日", "一", "二", "三", "四", "五", "六"].forEach(function (w) {
        html += '<div class="cal-w">' + w + "</div>";
      });
      var start = (first + 6) % 7; // 让周一排第一列
      for (var i = 0; i < start; i++) html += '<div class="cal-d empty">0</div>';
      for (var dd = 1; dd <= total; dd++) {
        var key = y + "-" + String(m).padStart(2, "0") + "-" + String(dd).padStart(2, "0");
        var cls = "cal-d" + (days[key] ? " on" : "") + (key === todayKey ? " today" : "");
        html += '<div class="' + cls + '">' + dd + "</div>";
      }
      html += "</div>";
      html += '<div class="muted" style="font-size:12px;margin-top:14px">🔥 当前连续 ' +
        (state.user ? state.user.streak_days : 0) + " 天</div>";
      html += "</div></div>";
      el.innerHTML = html;
    }).catch(function (e) { toast(e.message); });
  }

  function currentMonth() {
    var d = new Date();
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0");
  }

  // ------------------------------------------------------------------ 设置
  function renderReminder(el) {
    api("/user/profile").then(function (p) {
      var html = '<div class="page"><div class="card">';
      html += '<div class="between" style="padding:6px 0"><div><div style="font-size:14px">每日学习提醒</div>' +
        '<div class="muted" style="font-size:12px;margin-top:4px">开启后将在设定时间推送（V1 生效）</div></div>' +
        '<div class="switch' + (p.reminder_enabled ? " on" : "") + '" data-act="toggle-reminder"><i></i></div></div>';
      html += "</div>";
      html += '<div class="card"><div class="between" style="padding:6px 0"><div>' +
        '<div style="font-size:14px">提醒时间</div>' +
        '<div class="muted" style="font-size:12px;margin-top:4px">建议选你通常有空的时段</div></div>' +
        '<input type="time" value="' + (p.reminder_time || "20:00") + '" data-act="time" ' +
        'style="border:1px solid var(--line);border-radius:8px;padding:6px 10px;font-family:inherit;font-size:14px" /></div></div>';
      html += '<div class="card"><div class="between" style="padding:6px 0"><div>' +
        '<div style="font-size:14px">每日目标卡片数</div>' +
        '<div class="muted" style="font-size:12px;margin-top:4px">影响首页进度环</div></div>' +
        '<input type="number" min="5" max="100" value="' + (p.daily_goal || 20) + '" data-act="goal" ' +
        'style="width:70px;border:1px solid var(--line);border-radius:8px;padding:6px 10px;font-family:inherit;font-size:14px;text-align:center" /></div></div>';
      html += '<button class="btn block" data-act="save-reminder">保存设置</button>';
      html += '<div class="muted" style="font-size:11.5px;text-align:center;margin-top:14px;line-height:1.7">' +
        "注：微信订阅消息需用户在小程序内逐次授权，V0 仅预留设置项与接口</div>";
      html += "</div>";
      el.innerHTML = html;
    }).catch(function (e) { toast(e.message); });
  }

  function renderSensitive(el) {
    api("/user/profile").then(function (p) {
      var on = !!p.sensitive_opt_in;
      var html = '<div class="page"><div class="card">' +
        '<div style="font-size:14px;font-weight:600">敏感词汇学习</div>' +
        '<div class="muted" style="font-size:12.5px;margin-top:8px;line-height:1.8">' +
        "法语日常口语包含脏话与冒犯性表达。了解它们有助于听懂真实对话，但你可以选择不学。" +
        "关闭后，所有标记为敏感的内容将不会出现在学习中。</div></div>";
      html += '<div class="opt-item' + (on ? " sel" : "") + '" data-act="set-sensitive" data-v="1">' +
        '<div class="opt-title">学习全部词汇（含敏感词）</div>' +
        '<div class="opt-desc">包含 merde、putain 等真实口语表达</div></div>';
      html += '<div class="opt-item' + (on ? "" : " sel") + '" data-act="set-sensitive" data-v="0">' +
        '<div class="opt-title">仅学习常规词汇</div>' +
        '<div class="opt-desc">跳过所有敏感内容（推荐）</div></div>';
      html += '<div class="muted" style="font-size:12px;text-align:center;margin-top:16px">当前状态：<b>' +
        (on ? "全部词汇" : "仅常规词汇") + "</b></div>";
      html += "</div>";
      el.innerHTML = html;
    }).catch(function (e) { toast(e.message); });
  }

  // ------------------------------------------------------------------ 事件委托
  document.addEventListener("click", function (ev) {
    var el = ev.target.closest("[data-act]");
    if (!el) return;
    var act = el.getAttribute("data-act");

    switch (act) {
      case "flip":
        state.study.flipped = !state.study.flipped;
        state.study.lastFlipAt = Date.now();
        el.classList.toggle("flipped", state.study.flipped);
        break;
      case "answer":
        answerCard(el.getAttribute("data-v"));
        break;
      case "level":
        go("#/level?id=" + el.getAttribute("data-id"));
        break;
      case "lesson":
        go("#/lesson?id=" + el.getAttribute("data-id"));
        break;
      case "start-study":
        go("#/study?lesson_id=" + el.getAttribute("data-id"));
        break;
      case "review":
        startReview();
        break;
      case "back-learn":
        state.study = null;
        go("#/learn");
        break;
      case "retry-lesson":
        if (state.study) go("#/study?lesson_id=" + (state.study.lessonId || 1));
        break;
      case "close-checkin": {
        var m = document.querySelector(".checkin-mask");
        if (m) m.remove();
        break;
      }
      case "retry":
        render();
        break;
      case "m-calendar": go("#/calendar"); break;
      case "m-reminder": go("#/reminder"); break;
      case "m-sensitive": go("#/sensitive"); break;
      case "m-share": toast("分享功能 V1 开放（onShareAppMessage 已预留）"); break;
      case "m-shortcut": toast("添加到桌面 V1 开放"); break;
      case "m-about":
        alert("法语学习小程序 V0 框架版\n\nH5 预览仅用于交互验收，\n真机小程序请看 miniprogram/ 源码。");
        break;
      case "reset":
        if (confirm("将清空本机的登录态与演示数据，确定？")) {
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(DEVICE_KEY);
          location.reload();
        }
        break;
      case "set-sensitive":
        api("/user/preferences/sensitive-opt-in", "POST",
          { sensitive_opt_in: el.getAttribute("data-v") === "1" })
          .then(function () { toast("已保存"); render(); })
          .catch(function (e) { toast(e.message); });
        break;
      case "toggle-reminder":
        el.classList.toggle("on");
        break;
      case "save-reminder": {
        var sw = document.querySelector('[data-act="toggle-reminder"]');
        var time = document.querySelector('[data-act="time"]');
        var goal = document.querySelector('[data-act="goal"]');
        api("/user/preferences/reminder", "PUT", {
          reminder_enabled: sw.classList.contains("on"),
          reminder_time: time.value,
          daily_goal: Number(goal.value) || 20,
        }).then(function () { toast("设置已保存"); history.back(); })
          .catch(function (e) { toast(e.message); });
        break;
      }
    }
  });

  document.querySelectorAll(".tab").forEach(function (t) {
    t.addEventListener("click", function () { location.hash = t.getAttribute("data-route"); });
  });
  $("#navBack").addEventListener("click", function () { history.back(); });

  window.addEventListener("hashchange", render);

  // ------------------------------------------------------------------ 启动
  function clock() {
    var d = new Date();
    $("#clock").textContent = String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
  }
  clock(); setInterval(clock, 30000);

  ensureLogin()
    .then(function () { render(); })
    .catch(function (e) {
      $("#screen").innerHTML = '<div class="page"><div class="empty"><div class="empty-ico">📡</div>' +
        '<div class="empty-txt">登录失败：' + esc(e.message) + '</div>' +
        '<div style="margin-top:16px"><button class="btn" onclick="location.reload()">重试</button></div></div></div>';
    });
})();
