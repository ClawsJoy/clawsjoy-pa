"use strict";
/* ClawsJoy PA 前端 v0.2（2026-09-10）
   模式（8）：聊天/工作/项目开发 = 已启用；电影/深度设计/3D/动画/游戏 = 预留(MCP/流水线接入后启用)
   通道：聊天 → /v9/pa/dialog（PA 层，纯商量不出手）；工作/开发 → /v9/agent/chat（执行循环）
   线程：每线程独立 sid + 模式，消息存 localStorage；项目文件：/v9/sandbox/list
*/
const API = window.location.origin;
const MODES = {"chat":{"ic":"💬","label":"聊天","hint":"就事论事 · 目标导向 · 画像/审美/情感沉淀","on":true,"chan":"pa","perm":"只读"},"work":{"ic":"🛠️","label":"工作","hint":"办公类 computer use · 浏览器 · 轻度设计与图文 · 演示视频","on":true,"chan":"agent","perm":"标准"},"dev":{"ic":"⌨️","label":"项目开发","hint":"代码/工程 · 权限最高 · 沙箱与仓库","on":true,"chan":"agent","perm":"高"},"film":{"ic":"🎬","label":"电影制作","hint":"分镜/成片流水线","on":false,"chan":"agent","perm":"高"},"design":{"ic":"🎨","label":"专业深度设计","hint":"品牌/视觉系统/画册","on":false,"chan":"agent","perm":"高"},"model3d":{"ic":"🧊","label":"3D 建模","hint":"Blender MCP · 建模/材质","on":false,"chan":"mcp","perm":"高"},"anim":{"ic":"🌀","label":"动画渲染","hint":"绑定/动画/渲染农场","on":false,"chan":"mcp","perm":"高"},"game":{"ic":"🎮","label":"游戏制作","hint":"原型/关卡/资源","on":false,"chan":"agent","perm":"高"}};

/* ---- 状态 ---- */
let state = { mode:'chat', threads:[], activeThread:null };
/* ===== 面闸（拆单体追加 · 2026-10-04 · CW b2a5182 · 承 pm_976 §三.1）=====
   面清单与开关的真源 = web/pa/faces.json（每面 open 旗）。
   读不到 / 解析失败 / 非 2xx ⇒ 全体按 open（fail-open · ⛔ 改变原行为）。
   open:false 的面 ⇒ ① boot.js 里其启动步经 PA_FACES.guard 跳过 ② 其 DOM（faces.json 的 dom 选择器）收起。
   一开关关全部私面：把 faces.json 里 private:true 的面 open 置 false。
   ⚠ 本闸为同步读（XMLHttpRequest async=false）—— 为使 boot 次序逐字不动；代价：解析期一次本机阻塞读。 */
window.PA_FACES = (function(){
  var OPEN = {}, META = {}, api = {
    loaded: false, open: OPEN, meta: META,
    on: function(id){ return OPEN[id] !== false; },
    guard: function(id, fn){ return function(){ if(!api.on(id)) return; return fn.apply(null, arguments); }; },
    hide: function(){
      Object.keys(META).forEach(function(id){
        var m = META[id]; if(!m || m.open !== false) return;
        (m.dom || []).forEach(function(sel){
          try{
            var els = document.querySelectorAll(sel);
            for(var i=0;i<els.length;i++){ els[i].style.display='none'; els[i].setAttribute('aria-hidden','true'); }
          }catch(e){}
        });
      });
    },
    load: function(){
      try{
        var r = new XMLHttpRequest();
        r.open('GET', 'pa/faces.json', false);
        r.send(null);
        if(r.status >= 200 && r.status < 300){
          var d = JSON.parse(r.responseText);
          (d.faces || []).forEach(function(f){ if(f && f.id){ OPEN[f.id] = (f.open !== false); META[f.id] = f; } });
          api.loaded = true;
        }
      }catch(e){ api.loaded = false; }
      return api.loaded;
    }
  };
  return api;
})();
PA_FACES.load();
try{ PA_FACES.hide(); }catch(e){}
document.addEventListener('DOMContentLoaded', function(){ try{ PA_FACES.hide(); }catch(e){} });

/* ⭐ 面之「缺」三态 · **一处定形**（承 pm 18:00 批一 ＋ pm 17:47 §二改① ＋ pm_刀12p §〇）。
   「未接」一名三义 ⇒ ⛔ 前端各写一套（必漂）⇒ 三态（＋不可达之**特形**「回退支」）唯此一处：
     ① PA_GAP.todo(why) ⇒ ⒜ 未接 · 待办（M1）＝ 后端无此面 ／ 无此键 ⇒ 将来会接；
     ② PA_GAP.off(why)  ⇒ ⛔ 不接（红线）      ＝ 不会有 ⇒ ⛔ 以「未接」暗许「将来会接」＝ 软性虚诺；
     ③ PA_GAP.down(why) ⇒ 不可达              ＝ 后端此刻不在 ／ 未应答 ⇒ ⛔ ≠ 未接 · ⛔ 读成真 0。
   ⚠ 静态壳（`pa.html` · ⭐ 唯一壳 —— 承 pm 1203 §一：副本 `web/pa_v3.html` 已于 2026-10-05 删 · TD 716bc31）⛔ 调 JS ⇒ 其属此三形之静态标**逐字抄此三形**（无 JS 兜底）；
     运行期由 `today.js` 之 `paSrcWrite` **认领覆盖**（双保险 · ⛔ 二说 · 承 pm 18:00 §一）。 */
window.PA_GAP = {
  todo: function(why){ return '⒜ 未接 · 待办（M1）' + (why ? ('｜为何未接：' + why) : ''); },
  off:  function(why, kind){ return '⛔ 不接（' + (kind || '红线') + (why ? ('：' + why) : '') + '）'; },
  down: function(why){ return '不可达' + (why ? ('（' + why + '）') : ''); },
  /* ④ **回退支**（后端应答在 · **键不在**）—— 不可达之**特形** ⇒ 其文**须与「无此面」分形**
     （⛔ 同形 ⇒ 读方必误：PM-90 之假阳即此病之实证 · 承 pm 18:08 §二）｜`key` ⛔ 省 ⇒ **附键名**（一名一义）。 */
  fallback: function(key){ return '（回退支：后端未给此键 ' + key + ' ⇒ 此刻不可达）'; },
  /* 短标（窄格 · 如 `.duty .r .k` 之 62px）：同三态，⛔ 载长「为何」（长句入其所辖正文）。 */
  tag:  function(bucket){ return (bucket === 'off') ? '⛔ 不接' : ((bucket === 'down') ? '不可达' : '⒜ 未接'); }
};


/* ===== ⭐ 面之「陈旧」第四态 · **一处定形**（承 pm 19:05 令 §一 ／ pm_刀12p §〇 之三态 ＋ 本态）=====
   病（今日两实证）：① PM `18:00` 之假阳（把「回退支」字样读成「未接」）；
                    ② 老板 `18:5x` 之旧页（把「后端未载」读成「没做」）
   ⇒ ⭐ **同一根刺：面把「我此刻看到的」冒充「现在是什么」**。
   四态（唯此一处）：⒜ 未接 · 待办（M1）｜⒝ ⛔ 不接（红线）｜⒞ 不可达｜⭐ ⒟ **陈旧**（数是真的 · 刻是旧的）。
   形（pm 19:05 §一）：
     ⒜ 凡活面之数上屏 ⇒ 同屏附「取数刻」（用**后端** `at`；⛔ 以屏刻充 · 承 L76）；
     ⒝ 取数刻 与 此刻 之差 > 阈（默认 5 min）⇒ 显「⏳ 已陈旧 · 请刷新」（⛔ 静默显旧数）；
     ⒞ 刷新须有**显式入口**（⛔ 强求自轮询 —— 省资源；起服 ／ 后端换 `pid` 后尤须提示）；
     ⒟ 反控：静置 > 阈 ⇒ 必显陈旧；刷新后 ⇒ 陈旧消 ＋ 刻前移（`setThresh` 供机械验 · 两向皆可验）。
   ⛔ 本器只标「刻」与「陈旧」：⛔ 改数 ／ ⛔ 造刻 ／ ⛔ 以屏刻充数刻。 */
window.PA_STALE = (function(){
  var DEF_THRESH_MS = 5 * 60 * 1000;   /* 阈 5 min（pm 19:05 §一⒝ 所建议） */
  var THRESH_MS = DEF_THRESH_MS;
  var reg = [], refreshFn = null;

  function parseAt(t){
    if(t === undefined || t === null || t === '') return null;
    var ms = Date.parse(String(t).trim().replace(' ', 'T'));
    return isNaN(ms) ? null : ms;
  }
  function ageMs(at){ var ms = parseAt(at); return (ms === null) ? null : (Date.now() - ms); }
  function fmtAge(ms){
    if(ms === null) return '—';
    var m = Math.floor(ms / 60000);
    if(m < 1) return '不足 1 分';
    if(m < 60) return m + ' 分';
    return Math.floor(m / 60) + ' 时 ' + (m % 60) + ' 分';
  }
  function stOf(rec){
    if(rec.at === undefined || rec.at === null || rec.at === '') return {k:'nostamp'};
    var a = ageMs(rec.at);
    if(a === null) return {k:'badstamp'};
    return (a > THRESH_MS) ? {k:'stale', age:a} : {k:'fresh', age:a};
  }
  /* 徽标插于**其所标之元素之后**（⛔ 作其子 —— 行之内文由渲染函数重写 ⇒ 子会被抹）。幂等（元素上存引）。 */
  function ensure(rec){
    if(rec.el && rec.el.__paStaleBadge && rec.el.__paStaleBadge.parentNode) return rec.el.__paStaleBadge;
    if(!rec.el || !rec.el.parentNode) return null;
    var b = document.createElement('span');
    b.className = 'pastale';
    rec.el.parentNode.insertBefore(b, rec.el.nextSibling);
    rec.el.__paStaleBadge = b;
    rec.badge = b;
    return b;
  }
  var api = {
    DEF_THRESH_MS: DEF_THRESH_MS,
    getThresh: function(){ return THRESH_MS; },
    setThresh: function(ms){ THRESH_MS = ms; return api.tick(); },   /* 反控 ／ 验器（⛔ 生产线不改其值） */
    ageMs: ageMs, fmtAge: fmtAge,
    isStale: function(at){ var a = ageMs(at); return (a !== null && a > THRESH_MS); },
    clear: function(){
      reg.forEach(function(r){
        try{ if(r.badge && r.badge.parentNode) r.badge.parentNode.removeChild(r.badge); }catch(e){}
        try{ if(r.el) delete r.el.__paStaleBadge; }catch(e){}
      });
      reg = [];
    },
    /* 幂等（按元素）：同一元素重标 ⇒ **更新其刻**（⛔ 重入册 —— 面会被重渲染 ⇒ 重入册 ⇒ 计数虚增）。 */
    mark: function(el, at, label){
      if(el){ for(var i = 0; i < reg.length; i++){ if(reg[i].el === el){ reg[i].at = (at === undefined ? null : at); reg[i].label = label || ''; ensure(reg[i]); return reg[i]; } } }
      var rec = {el: el || null, at: (at === undefined ? null : at), label: label || ''};
      reg.push(rec); ensure(rec); return rec;
    },
    tick: function(){
      var nStale = 0, nNo = 0, worst = null;
      reg.forEach(function(rec){
        var s = stOf(rec), txt = '', cls = 'pastale';
        if(s.k === 'nostamp'){ txt = '⚠ 取数刻未给（后端未给 `at` ⇒ 报 PM 转 TD · ⛔ 以屏刻充）'; cls += ' warn'; nNo++; }
        else if(s.k === 'badstamp'){ txt = '⚠ 取数刻不可解析（' + String(rec.at) + '）'; cls += ' warn'; nNo++; }
        else if(s.k === 'stale'){ txt = '⏳ 已陈旧 · 请刷新（取数刻 ' + String(rec.at) + ' · 已逾 ' + fmtAge(s.age) + '）'; cls += ' on'; nStale++; if(worst === null || s.age > worst) worst = s.age; }
        var b = rec.badge;
        if(b && b.parentNode){
          b.textContent = txt; b.className = cls;
          b.title = '活面：' + rec.label + '（取数刻 ' + ((rec.at === null || rec.at === undefined || rec.at === '') ? '未给' : String(rec.at)) + ' · 阈 ' + fmtAge(THRESH_MS) + '）';
        }
        try{ if(rec.el) rec.el.setAttribute('data-pa-stale', s.k); }catch(e){}
      });
      api.stale = nStale; api.nostamp = nNo;
      var host = document.getElementById('paStaleBar');
      if(host){
        if(nStale > 0){ host.hidden = false; host.textContent = '⏳ ' + nStale + ' 处活面已陈旧（最旧 ' + fmtAge(worst) + '）· 点此刷新 ↻'; }
        else { host.hidden = true; host.textContent = ''; }
      }
      return {stale: nStale, nostamp: nNo};
    },
    onRefresh: function(fn){ refreshFn = fn; },
    refresh: function(){
      if(typeof refreshFn === 'function'){ try{ var r = refreshFn(); if(r && typeof r.catch === 'function') r.catch(function(){}); return r; }catch(e){ return null; } }
      return null;
    },
    start: function(){ api.tick(); try{ setInterval(api.tick, 30000); }catch(e){} }
  };
  return api;
})();

/* 陈旧之「显式入口」（↻ 刷新）＋ 汇总条 —— **运行期注入**（⛔ 动静态壳：壳 ⛔ 调 JS ⇒ 无 JS 时既无活数亦无陈旧）。 */
(function(){
  function doRefresh(){
    try{
      if(window.PA_STALE && typeof window.paRefreshLive === 'function'){ window.PA_STALE.refresh(); return; }
      location.reload();
    }catch(e){ try{ location.reload(); }catch(_e){} }
  }
  function build(){
    try{
      var tr = document.querySelector('.topbar .top-right') || document.querySelector('.top-right');
      if(tr && !document.getElementById('paStaleBar')){
        var bar = document.createElement('span');
        bar.id = 'paStaleBar'; bar.hidden = true;
        bar.title = '陈旧之汇总（⛔ 静默显旧数）：点此 ＝ 刷新活面之读数';
        bar.onclick = doRefresh;
        tr.insertBefore(bar, tr.firstChild);
      }
      if(tr && !document.getElementById('paRefreshBtn')){
        var b = document.createElement('span');
        b.className = 'chip'; b.id = 'paRefreshBtn';
        b.title = '刷新活面之读数（显式入口 · ⛔ 自轮询；起服 ／ 后端换 pid 后尤须一按）';
        b.textContent = '↻ 刷新';
        b.onclick = doRefresh;
        tr.appendChild(b);
      }
      if(window.PA_STALE) window.PA_STALE.start();
    }catch(e){}
  }
  if(document.readyState === 'loading'){ document.addEventListener('DOMContentLoaded', build); }
  else { build(); }
})();
