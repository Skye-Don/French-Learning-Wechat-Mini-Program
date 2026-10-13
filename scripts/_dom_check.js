// 用 jsdom 真实加载 H5 页面，验证：启动 → 渲染 → 点击链路
// 用法：NODE_PATH=<workspace>/node_modules node scripts/_dom_check.js <baseURL>
const fs = require("fs");
const path = require("path");
const { JSDOM, VirtualConsole } = require("jsdom");

const BASE = process.argv[2] || "http://127.0.0.1:8000";
const STATIC = path.join(__dirname, "..", "demo", "static");

const vc = new VirtualConsole();
const errors = [];
vc.on("jsdomError", (e) => errors.push("jsdomError: " + (e.stack || e.message)));
vc.on("error", (...a) => errors.push("console.error: " + a.join(" ")));

let html = fs.readFileSync(path.join(STATIC, "index.html"), "utf8");
html = html.replace('<script src="/static/app.js"></script>', "");
const appJs = fs.readFileSync(path.join(STATIC, "app.js"), "utf8");

const dom = new JSDOM(html, {
  url: BASE + "/", runScripts: "dangerously", pretendToBeVisual: true, virtualConsole: vc,
});
const { window } = dom;
const log = [];
window.fetch = (url, opts) => {
  const abs = new URL(url, BASE).toString();
  return globalThis.fetch(abs, opts).then((r) => {
    log.push(`  ${(opts && opts.method) || "GET"} ${url} -> ${r.status}`); return r;
  }).catch((e) => { log.push(`  ${url} -> ERR ${e.message}`); throw e; });
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const txt = () => (window.document.querySelector("#screen").textContent || "")
  .replace(/\s+/g, " ").trim();
function click(sel) {
  const el = window.document.querySelector(sel);
  if (!el) return false;
  el.dispatchEvent(new window.MouseEvent("click", { bubbles: true, cancelable: true }));
  return true;
}
const step = async (name, sel, wait) => {
  const ok = click(sel);
  await sleep(wait || 2500);
  console.log(`\n[${name}] 找到元素=${ok} hash=${window.location.hash}`);
  console.log("  内容:", txt().slice(0, 130) || "(空)");
  return ok;
};

(async () => {
  try { window.eval(appJs); } catch (e) { console.log("❌ app.js 抛错：", e.message); process.exit(1); }
  await sleep(6000);
  console.log("=== 启动 ===");
  console.log(txt().slice(0, 90));

  await step("点等级 A1", '[data-act="level"]', 3000);
  await step("点第1个课时", '[data-act="lesson"]', 3000);
  await step("点开始学习", '[data-act="start-study"]', 3500);
  await step("翻卡", '[data-act="flip"]', 1200);
  await step("答对", '[data-act="answer"][data-v="correct"]', 3500);

  console.log("\n=== 网络请求汇总 ===");
  console.log(log.join("\n"));
  if (errors.length) {
    console.log("\n=== 控制台错误 ===");
    errors.slice(0, 6).forEach((e) => console.log(e.split("\n").slice(0, 5).join("\n")));
  } else console.log("\n控制台无错误");
  process.exit(0);
})();
