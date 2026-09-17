# browser_local observe 动作设计（P2 储备能力）

**状态**: 设计稿（未实施）
**优先级**: P2 — 不影响当前任务，作为「Agent 学习用户操作」储备
**日期**: 2026-08-26

---

## 一、目标

用户手动操作平台（发布/回填/填表）时，Agent 用 `observe` 捕捉用户的每个动作（点击/输入/跳转/接口调用），记录成可复用的 SOP + 选择器。

**价值**：把「用户会做、Agent 不会做」的操作，通过观察自动提炼成 Agent 可执行的选择器序列——降低每次新平台/新功能的校准成本（如之前抖音/B站逐轮探测）。

---

## 二、接口设计

### 2.1 动作：observe_start

```json
{"action": "observe_start", "frame": 0, "max_actions": 200}
```

- **frame**（可选）: 观察的 frame（默认主 frame 0）
- **max_actions**（可选）: 动作日志上限（默认 200，防内存膨胀）
- 返回: `{"observe_id": "obs_xxx", "started": true}`
- 注入监听后**立即返回**（不阻塞）——用户继续手动操作

### 2.2 动作：observe_stop

```json
{"action": "observe_stop", "observe_id": "obs_xxx"}
```

- 停止监听、移除注入脚本、返回操作日志
- 返回: 见 §三 日志结构

---

## 三、日志结构（observe_stop 返回）

```json
{
  "observe_id": "obs_xxx",
  "duration_ms": 84321,
  "action_count": 12,
  "actions": [
    {"type": "navigate", "from": "https://creator.douyin.com/.../upload", "to": "https://creator.douyin.com/.../post/image?type=new", "ts": 1752},
    {"type": "click", "selector": "input[type=file][accept*='image/']", "text": "", "tag": "INPUT", "ts": 8310},
    {"type": "input", "selector": "input[placeholder='添加作品标题']", "value": "AI刷题考研真相", "tag": "INPUT", "ts": 15420},
    {"type": "input", "selector": "div[contenteditable='true']", "value": "考研人每天...", "tag": "DIV", "ts": 20113},
    {"type": "click", "selector": "button:has-text('暂存')", "text": "暂存", "tag": "BUTTON", "ts": 30255},
    {"type": "api", "method": "POST", "url": "https://creator.douyin.com/.../draft", "params": {"title": "...", "images": [...]}, "ts": 31002}
  ],
  "sop_draft": {
    "steps": [
      "navigate(入口URL)",
      "upload(kind=image, file=...)",
      "fill(title, input[placeholder='添加作品标题'])",
      "click(contenteditable=true, keyboard.type)",
      "click(button:has-text('暂存'))"
    ],
    "confidence": 0.9
  }
}
```

**字段说明**:
- `selector`: 尽量精确——优先 `input[placeholder='...']`/`button:has-text('...')` 类语义选择器，其次 class（标注 `cls_source=hashed` 提醒可能漂移）
- `value`: input 值截断 200 字符（防敏感信息）；`api.params` 截断 1000 字符
- `ts`: 相对观察起始的毫秒
- `sop_draft`: 客户端初步提炼的步骤序列（供 Agent 复核）——**最终 SOP 由 Agent 提炼**，客户端只做顺序整理

---

## 四、观察脚本设计（注入前端 JS）

### 4.1 监听器清单（evaluate 注入，存 window.__observe_xxx）

| 监听器 | 事件 | 记录内容 |
|---|---|---|
| click | `document.addEventListener('click', ..., true)` 捕获阶段 | selector(从 e.target 向上合成) + 文本 + tag |
| input/change | `document.addEventListener('input'/'change', ..., true)` | 填写的值（`e.target.value` 截断）+ selector |
| DOM 变化 | `MutationObserver`（subtree+childList+attributes） | 关键节点增删（class 含 modal/dropdown/option 等，节流 200ms） |
| navigation | `window.addEventListener('popstate')` + `pushState/replaceState` 拦截 + `pagehide` | URL 变化（from/to） |
| fetch/XHR | 包装 `window.fetch` + `XMLHttpRequest.open/send` | method + url + body(截断) + status |

### 4.2 selector 合成算法

```js
function bestSelector(el) {
  // 1) 有 id → #id
  // 2) 有稳定属性: input[placeholder=...] / button:has-text(前8字) / [data-e2e=...]
  // 3) 语义 class(非哈希): .publish-btn(长度<20 且非 base64 样)
  // 4) 兜底: tag + nth-of-type 路径(标注 unstable)
}
```

### 4.3 注入/移除

- `observe_start` → `page.evaluate(注入脚本)`，返回 observe_id（存客户端 `self._observe = {id, start_ts, log}`）
- `observe_stop` → `page.evaluate(移除脚本)` + 取回 `window.__observe_log` → 返回
- 若页面刷新（navigation 到新页面）→ 监听器随页面销毁丢失 → **observe_start 需处理跨页续观**（见 §五 限制）

---

## 五、实现位置（改动点）

| 层 | 文件 | 改动 |
|---|---|---|
| 工具层 schema | `core/tools/browser_local.py` | enum 加 `observe_start`/`observe_stop`；加 `observe_id`/`max_actions` 参数 |
| 客户端实现 | `scripts/agent_client/actions.py` | 新增 `observe_start()`/`observe_stop()` 方法（基于现有 evaluate 注入 JS）；`_observe` 状态存客户端进程 |
| 客户端分发 | `scripts/agent_client/agent_client.py` | 分发链加两个分支（不涉及审批——观察只读不改） |
| lib 层 | `core/lib/v8/browser_local.py` | 无改动（observe 非敏感，不走审批；execute 直接透传） |
| 测试 | `tests/unit/test_browser_observe.py` | 模拟 page 验证脚本注入/日志收集/selector 合成 |

**复用**：观察脚本本质是 evaluate 的 JS 字符串常量——放 `actions.py` 模块级 `_OBSERVE_START_JS`/`_OBSERVE_STOP_JS`，与 evaluate 共用注入通道。

---

## 六、SOP 提炼流程（Agent 侧）

1. **用户手动操作一次**（如抖音发图文）：用户说「我来操作，你观察」
2. **Agent**：`observe_start(frame=0)` → 提示用户开始 → 用户操作完成 → `observe_stop()`
3. **Agent 拿到 actions 日志**：
   - 过滤无意义动作（hover、纯滚动、focus）
   - 合并连续 input 到同一选择器
   - 从 navigate/api 推断步骤边界（进入编辑页=步骤1、保存草稿的 api=收尾）
   - **生成 SOP**：步骤 + 选择器 + 交互方式（fill vs click+keyboard）
4. **回填 platforms.py + SOP 文档**：与手动校准产出相同格式
5. **验证**：Agent 按提炼的 SOP 自动执行一次，成功则交付

**与现有校准的关系**：observe 是「观察学习」路径，与「逐轮探测校准」互补——observe 快（一次人工操作），校准稳（逐元素验证）。优先 observe 快速锁定大框架，再用校准微调细节。

---

## 七、限制与风险

| 限制 | 说明 | 缓解 |
|---|---|---|
| **页面刷新丢失监听** | 跨页导航后注入脚本随旧文档销毁 | 客户端在 `page.on('framenavigated')` 重新注入（或接受仅单页观察，多页拆多次 observe） |
| **敏感信息** | input value / api body 可能含密码/Token | 默认截断 200 字符；`api.params` 过滤 `password/token/secret/cookie` 键 |
| **iframe** | 编辑区在 iframe 时需观察对应 frame | observe_start 的 `frame` 参数指定；多 frame 复杂页面先 frames 探测 |
| **shadow DOM** | 监听器默认不穿透 shadow root | 观察脚本用 `composedPath()` 处理（记录宿主元素）；复杂场景降级为主文档 |
| **性能** | MutationObserver 高频触发 | 节流 200ms + max_actions 上限；观察结束即移除 |
| **XHR/fetch 干扰** | 平台自身轮询/埋点请求刷屏 | 过滤 `/log|/collect|/pv|/track|/monitor` 类 URL；只留业务请求 |

---

## 八、实施步骤（以后做时的顺序）

1. `actions.py`：`_OBSERVE_START_JS`/`_OBSERVE_STOP_JS` 脚本常量 + `observe_start/stop` 方法 + `_observe` 状态
2. `agent_client.py`：分发分支
3. `core/tools/browser_local.py`：schema enum + 参数
4. `tests/unit/test_browser_observe.py`：mock page 验证（脚本注入、日志 JSON、selector 合成、敏感过滤）
5. 真机验证：用户手动操作一个平台（如抖音），Agent observe → 提炼 SOP → 自动执行验证

**预估工作量**：脚本编写 ~2h，测试 ~1h，真机验证 ~1h（合计半天）
---

## 附录 A：核心脚本原型（最小可用，供实施参考）

### A.1 observe_start 注入脚本（简化版）

```js
// 注入到页面: window.__observe_start(maxActions)
(function () {
  if (window.__observe_log) return { started: false, reason: 'already' };
  var MAX = window.__observe_max || 200;
  var log = [];
  var t0 = Date.now();
  function rec(a) { if (log.length < MAX) { a.ts = Date.now() - t0; log.push(a); } }
  function selOf(el) {
    if (!el || el === document) return '';
    if (el.id) return '#' + el.id;
    var ph = el.getAttribute && el.getAttribute('placeholder');
    if (ph) return el.tagName.toLowerCase() + "[placeholder='" + ph.slice(0, 40) + "']";
    var t = (el.innerText || '').trim().slice(0, 8);
    if (t && /^[a-z\u4e00-\u9fa5]{2,8}$/.test(t)) return el.tagName.toLowerCase() + ":has-text('" + t + "')";
    var cls = String(el.className || '').split(' ').filter(function(c){ return c.length > 2 && c.length < 24 && !/^[a-zA-Z0-9_-]{16,}$/.test(c); })[0];
    if (cls) return el.tagName.toLowerCase() + '.' + cls;
    return el.tagName.toLowerCase();
  }
  document.addEventListener('click', function (e) {
    var el = e.target && e.target.closest ? e.target.closest('button,input,textarea,a,[role=button]') : e.target;
    rec({ type: 'click', selector: selOf(el), text: (el.innerText || el.value || '').trim().slice(0, 40), tag: el.tagName });
  }, true);
  document.addEventListener('input', function (e) {
    var el = e.target;
    rec({ type: 'input', selector: selOf(el), value: String(el.value || '').slice(0, 200), tag: el.tagName });
  }, true);
  var of = window.fetch;
  window.fetch = function () {
    var url = arguments[0], opts = arguments[1] || {};
    if (!/log|collect|pv|track|monitor/i.test(String(url))) {
      rec({ type: 'api', method: (opts.method || 'GET'), url: String(url).slice(0, 200), params: {} });
    }
    return of.apply(this, arguments);
  };
  window.__observe_log = log;
  return { started: true, observe_id: 'obs_' + Math.random().toString(36).slice(2, 10) };
})()
```

### A.2 observe_stop 提取脚本（简化版）

```js
// 提取并清理
(function () {
  var log = window.__observe_log || [];
  window.__observe_log = null;
  return JSON.stringify(log);
})()
```

> 说明：原型覆盖 click/input/fetch 三类核心监听；mutation/navigation/XHR 拦截按 §四.1 在实施时补全。selector 合成复用 selOf() 的优先级链（id → placeholder → 短文本 → 语义 class → tag 兜底）。
