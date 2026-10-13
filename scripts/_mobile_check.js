// 用真实 Chrome（移动端视口）验证 H5：有没有被遮挡、点击能不能命中
// 用法：NODE_PATH=<ws>/node_modules node scripts/_mobile_check.js [url]
const puppeteer = require("puppeteer-core");

const URL_ = process.argv[2] || "https://french-learning-miniapp.app.workbuddy.host/";
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME, headless: "new",
    args: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
    defaultViewport: { width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 2 },
  });
  const page = await browser.newPage();
  const errs = [];
  page.on("pageerror", (e) => errs.push("pageerror: " + e.message));
  page.on("console", (m) => { if (m.type() === "error") errs.push("console: " + m.text()); });

  await page.goto(URL_, { waitUntil: "networkidle2", timeout: 60000 });
  await new Promise((r) => setTimeout(r, 3000));

  const info = await page.evaluate(() => {
    const vw = innerWidth, vh = innerHeight;
    const at = (x, y) => {
      const el = document.elementFromPoint(x, y);
      if (!el) return "null";
      return el.tagName + "." + (el.className || "-") +
        (el.closest("[data-act]") ? " [data-act=" + el.closest("[data-act]").getAttribute("data-act") + "]" : "") +
        (el.closest("[data-opt]") ? " [data-opt]" : "");
    };
    return {
      vw, vh,
      modalHidden: document.querySelector("#modalRoot").hidden,
      modalDisplay: getComputedStyle(document.querySelector("#modalRoot")).display,
      tabbarHidden: document.querySelector("#tabbar").hidden,
      screenRect: document.querySelector("#screen").getBoundingClientRect().toJSON(),
      frameRect: document.querySelector(".phone-frame").getBoundingClientRect().toJSON(),
      probes: {
        "中上(195,300)": at(195, 300),
        "中间(195,420)": at(195, 420),
        "中下(195,560)": at(195, 560),
        "底部(195,800)": at(195, 800),
        "最底(195,830)": at(195, 830),
      },
    };
  });
  console.log("视口:", info.vw + "x" + info.vh);
  console.log("phone-frame:", JSON.stringify(info.frameRect));
  console.log("#screen:", JSON.stringify(info.screenRect));
  console.log("modal 打开?", !info.modalHidden, "| display:", info.modalDisplay);
  console.log("tabbar 隐藏?", info.tabbarHidden);
  console.log("\n--- 点击命中探测 ---");
  for (const [k, v] of Object.entries(info.probes)) console.log(" ", k, "=>", v);

  // 真实点击：先关掉弹窗（若开着），再点等级卡
  if (!info.modalHidden) {
    const opt = await page.$("[data-opt]");
    if (opt) {
      const box = await opt.boundingBox();
      console.log("\n弹窗选项位置:", JSON.stringify(box));
      await opt.click();
      await new Promise((r) => setTimeout(r, 2500));
      console.log("点选项后 modal 打开?", !(await page.evaluate(() => document.querySelector("#modalRoot").hidden)));
    }
  }

  const card = await page.$('[data-act="level"]');
  if (card) {
    const b = await card.boundingBox();
    console.log("\n等级卡位置:", JSON.stringify(b));
    const top = await page.evaluate((x, y) => {
      const el = document.elementFromPoint(x, y);
      return el ? el.tagName + "." + el.className : "null";
    }, b.x + b.width / 2, b.y + b.height / 2);
    console.log("卡片中心命中元素:", top);
    await card.click().catch((e) => console.log("click 失败:", e.message));
    await new Promise((r) => setTimeout(r, 2500));
    console.log("点卡片后 hash =", await page.evaluate(() => location.hash));
  } else {
    console.log("\n没有找到等级卡");
  }

  if (errs.length) { console.log("\n--- 控制台错误 ---"); errs.slice(0, 8).forEach((e) => console.log(" ", e)); }
  else console.log("\n控制台无错误");

  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });
