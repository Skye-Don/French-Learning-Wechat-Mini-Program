// ============================================================
// 行为埋点（V0 数据分析）
// 设计：本地先攒批（Storage），网络恢复 / 切后台时补发，避免高频请求。
// 事件类型白名单见生产后端 EVENT_TYPES；非白名单会被服务端丢弃。
// 隐私：仅采集用于产品优化的匿名行为，不采集 openid 等直接身份字段。
// ============================================================
const api = require("./request");

const QUEUE_KEY = "analytics_queue";
const MAX_BATCH = 50;
const MAX_LOCAL = 200;

function getQueue() {
  try {
    return wx.getStorageSync(QUEUE_KEY) || [];
  } catch (e) {
    return [];
  }
}

function saveQueue(list) {
  try {
    wx.setStorageSync(QUEUE_KEY, list);
  } catch (e) {
    // 存储不可用时静默丢弃，不影响主流程
  }
}

/**
 * 上报一条行为事件（先入本地队列，不直接请求）
 * @param {string} eventType 事件类型（如 app_launch / flashcard_study）
 * @param {object} payload   附带的业务参数（可空）
 */
function track(eventType, payload) {
  const list = getQueue();
  list.push({ event_type: eventType, payload: payload || null, _t: Date.now() });
  if (list.length > MAX_LOCAL) {
    list.splice(0, list.length - MAX_LOCAL); // 队列过长截断，防本地存储膨胀
  }
  saveQueue(list);
  if (list.length >= 10) {
    flush(); // 攒够一批主动发一次
  }
}

/**
 * 把本地队列批量上报到服务端。
 * 幂等：服务端按事件落库，重复上报仅多计数；失败保留队列下次重试。
 */
function flush() {
  const list = getQueue();
  if (!list.length) return Promise.resolve({ accepted: 0 });
  const batch = list.slice(0, MAX_BATCH).map((e) => ({
    event_type: e.event_type,
    payload: e.payload,
  }));
  return api.post("/api/analytics/track", { events: batch })
    .then((res) => {
      const rest = getQueue().slice(batch.length);
      saveQueue(rest);
      return res;
    })
    .catch(() => {
      // 失败保留队列，下次 retry（最多保留 MAX_LOCAL 条）
    });
}

module.exports = { track, flush };
