// 验证后台页：难度下拉是否为 A1-B2、列表徽标是否渲染、筛选是否可用
// 用法：NODE_PATH=<ws>/node_modules node scripts/_admin_check.js [url]
const puppeteer = require("puppeteer-core");

const BASE = (process.argv[2] || "https://french-learning-miniapp.app.workbuddy.host").replace(/\/$/, "");
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME, headless: "new",
    args: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
    defaultViewport: { width: 1280, height: 900 },
  });
  const page = await browser.newPage();
  await page.goto(BASE + "/admin", { waitUntil: "networkidle2", timeout: 60000 });
  await new Promise((r) => setTimeout(r, 3500));

  const r = await page.evaluate(() => {
    const sel = document.getElementById("f_difficulty");
    const fLevel = document.getElementById("filterLevel");
    const badges = Array.from(document.querySelectorAll("#list .tag[class*='lvl-']"));
    const dist = {};
    badges.forEach((b) => { const k = b.textContent.trim(); dist[k] = (dist[k] || 0) + 1; });
    return {
      selectTag: sel ? sel.tagName : "缺失",
      options: sel ? Array.from(sel.options).map((o) => o.value + "=" + o.textContent.slice(0, 12)) : [],
      filterExists: !!fLevel,
      filterOptions: fLevel ? Array.from(fLevel.options).map((o) => o.value || "(全部)") : [],
      badgeCount: badges.length,
      difficultyDist: dist,
      rowCount: document.querySelectorAll("#list tbody tr").length,
      hasNumberBadge: badges.some((b) => /^[1-5]$/.test(b.textContent.trim())),
    };
  });
  console.log("难度控件:", r.selectTag);
  console.log("下拉选项:", r.options);
  console.log("难度筛选器:", r.filterExists, r.filterOptions);
  console.log("列表行数:", r.rowCount, "| 难度徽标数:", r.badgeCount);
  console.log("徽标分布:", JSON.stringify(r.difficultyDist));
  console.log("是否残留数字难度徽标:", r.hasNumberBadge);

  // 试一下按 B1 筛选
  if (r.filterExists) {
    await page.select("#filterLevel", "B1");
    await new Promise((r2) => setTimeout(r2, 800));
    const after = await page.evaluate(() => {
      const b = Array.from(document.querySelectorAll("#list .tag[class*='lvl-']")).map((x) => x.textContent.trim());
      return { rows: document.querySelectorAll("#list tbody tr").length, badges: [...new Set(b)] };
    });
    console.log("筛选 B1 后:", JSON.stringify(after));
  }

  await page.screenshot({ path: "_shot_admin.png", fullPage: false });
  console.log("截图: _shot_admin.png");
  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });
