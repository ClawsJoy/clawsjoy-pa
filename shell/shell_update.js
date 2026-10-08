'use strict';
/*
 * shell_update.js —— 「壳层之更新」之**策**（一处定形 · 承 pm_1885 §三 ／ pm_1886 §一 ／ pm_1890 §一 ／ pm_1896 §三）。
 *
 * 分（一处定形 · 照 `update.js` 之族）：
 *   * 本档 ＝ **纯策**（态机 ＋ 人话 ＋ 门）⇒ ⛔ `electron` ／ ⛔ 出网 ／ ⛔ 直引 `electron-updater`
 *     （其由：可单测 —— `electron-updater` 之实由 `main.js` **注入**）。
 *   * **A 式**（pm_1885 §三.1 · PM 之裁）：`update-available ⇒ downloadUpdate()`（⛔ `autoDownload = true`）
 *     ／ `update-downloaded ⇒ **候人之明点** ⇒ quitAndInstall()`（⛔ 偷重启 —— 承 pm_1885 §三.2）。
 *   * **态机八字** ＋ **失败七码**（pm_1890 §一.1）：唯一源 ＝ `state()`（**拉** · pm_1890 §一.2）；
 *     「推」唯唤面**再拉**（⛔ 各算态 —— 免得「拉与推不一」而用户见二真相）。
 *   * ⛔ **行话上屏**（pm_1890 §一.3 ／ CW `1887 §一.3`）：返之 `message` 唯**人话 ＋ 去处**；
 *     原始之错（其或含本机径 ／ 端点 ／ 件名）**唯入日志** ⇒ ⛔ 返上屏；`code` 供面**可查**。
 *   * ⛔ 动 `app-update.yml` 之四栏（pm_1889 §一 · 我一手复核：其唯 `provider` ／ `url` ／ `channel`
 *     ／ `updaterCacheDirName` ∧ ⛔ `publisherName` ⇒ 校验路本不启 ⇒ **不签名可走应用内更新**）。
 *
 * 返之形（**一处定形** —— 页 ⇄ 壳之桥 · CW `1887` ＋ PM `1890 §一`）：
 *   成 ⇒ `{ok:true, phase, current, latest, progress}`；
 *   败 ⇒ `{ok:false, phase, code, message}`（`message` ＝ 人话 ＋ 去处）；
 *   ⭐ `phase` **恒在**（八字之一）⇒ 面可据以判「**此壳 ⛔ 供此能**」（＝ `unsupported` ／ `no-updater`）。
 *   ⭐ `progress` 唯 `downloading` 时非空 ∧ 唯 `total` 可量时给 `pct`（⛔ 编数 —— 承「如实读数」）。
 */

var PHASES = ['unsupported', 'idle', 'checking', 'available', 'downloading', 'downloaded', 'installing', 'failed'];
var CODES = ['no-updater', 'offline', 'check-failed', 'download-failed', 'verify-failed', 'install-failed', 'unknown'];

//: 去处（唯此一处 · ⛔ 二处各拼）—— 与 `main.js:shellLogFile()` 同物。
var DEST = '%LOCALAPPDATA%\\ClawsJoyPA\\shell\\shell.log';

//: 人话（**因**）—— ⛔ 行话 ／ ⛔ 本机径 ／ ⛔ 端点（承 pm_1890 §一.3）。
var WORD = {
  'no-updater': '本壳 ⛔ 带更新器 ⇒ 请重新安装桌面程序',
  'offline': '连不上更新源（本机网络 ∨ 更新源未开）',
  'check-failed': '查新版 ⛔ 成',
  'download-failed': '下载新版 ⛔ 成',
  'verify-failed': '新版之完整性校验 ⛔ 过',
  'install-failed': '安装 ⛔ 成',
  'unknown': '更新出错'
};

function messageOf(code) {
  var w = WORD[code] || WORD['unknown'];
  return w + '（去处：' + DEST + '）';
}

/* ---------------------------------------------------------------- 态（**纯** · 一处定形） */
function blank(current) {
  return { phase: 'idle', current: current || null, latest: null, progress: null, code: '', message: '' };
}

/* progress ⇒ {done,total,pct} ∨ null。⭐ ⛔ 编数：total ⛔ 可量 ⇒ pct ＝ null（承「如实读数」）。 */
function progressOf(p) {
  if (!p) { return null; }
  var done = Number(p.transferred || 0);
  var total = Number(p.total || 0);
  return { done: done, total: total, pct: (total > 0 ? Math.round(done * 100 / total) : null) };
}

/* 错之因 ⇒ 七码之一。⚠ 此为**启发**（依消息之文 · ⛔ 以「已判准」充）—— 判不得 ⇒ unknown。 */
function classify(err, phase) {
  var raw = (err && err.message != null) ? err.message : err;
  var m = (raw === undefined || raw === null) ? '' : String(raw);
  if (!m) { return 'unknown'; }
  if (/(sha512|checksum|integrity|signature|blockmap)/i.test(m)) { return 'verify-failed'; }
  if (/(ENOTFOUND|ECONNREFUSED|ETIMEDOUT|EAI_AGAIN|ECONNRESET|getaddrinfo|net::)/i.test(m)) { return 'offline'; }
  if (phase === 'available' || phase === 'downloading') { return 'download-failed'; }
  if (phase === 'downloaded' || phase === 'installing') { return 'install-failed'; }
  return 'check-failed';
}

/* 一事 ⇒ 新态（**纯**：⛔ 副作用 ⇒ 可单测）。 */
function reduce(st, evt) {
  var s = { phase: st.phase, current: st.current, latest: st.latest, progress: st.progress,
            code: st.code, message: st.message };
  var t = (evt && evt.t) || '';
  if (t === 'unsupported') {
    s.phase = 'unsupported'; s.code = 'no-updater'; s.message = messageOf('no-updater');
  } else if (t === 'checking') {
    s.phase = 'checking'; s.code = ''; s.message = '';
  } else if (t === 'available') {
    s.phase = 'available'; s.latest = (evt.info && evt.info.version) || s.latest; s.code = ''; s.message = '';
  } else if (t === 'none') {
    s.phase = 'idle'; s.latest = null; s.progress = null; s.code = ''; s.message = '';
  } else if (t === 'progress') {
    s.phase = 'downloading'; s.progress = progressOf(evt.p); s.code = ''; s.message = '';
  } else if (t === 'downloaded') {
    s.phase = 'downloaded'; s.latest = (evt.info && evt.info.version) || s.latest;
    s.progress = null; s.code = ''; s.message = '';
  } else if (t === 'installing') {
    s.phase = 'installing'; s.code = ''; s.message = '';
  } else if (t === 'error') {
    var c = classify(evt.err, evt.phase || st.phase);
    s.phase = 'failed'; s.code = c; s.message = messageOf(c);
  }
  return s;
}

/* 态 ⇒ 桥之返（**一处定形** · ⛔ 二处各拼）。 */
function reply(st) {
  var ok = !(st.phase === 'failed' || st.phase === 'unsupported');
  var out = { ok: ok, phase: st.phase, current: st.current, latest: st.latest, progress: st.progress };
  if (!ok) { out.code = st.code || 'unknown'; out.message = st.message || messageOf(out.code); }
  return out;
}

/* ---------------------------------------------------------------- 器（策 ＋ 注入之实） */
/* o ＝ { updater（electron-updater 之 autoUpdater ∨ 假器 ∨ null）, current, packaged, log, notify } */
function createController(o) {
  var opt = o || {};
  var up = opt.updater || null;
  var log = opt.log || function () { };
  var notify = opt.notify || function () { };
  var live = (opt.packaged === false) ? null : up;      // ⭐ 开发态 ⛔ 真跑更新器（免误触）⇒ 同 unsupported
  var st = blank(opt.current);

  function set(evt) {
    st = reduce(st, evt);
    try { notify(); } catch (e) { /* 推之侧之错 ⛔ 阻壳 */ }
  }

  if (!live) {
    st = reduce(st, { t: 'unsupported' });
  } else {
    // ⭐ A 式（pm_1885 §三.1）：⛔ autoDownload=true —— 下载由**本档**于「有新版」时起（可控 · 可显进度）。
    try { live.autoDownload = false; } catch (e) { /* 假器无此栏 ⇒ ⛔ 阻 */ }
    live.on('checking-for-update', function () { set({ t: 'checking' }); });
    live.on('update-available', function (info) {
      set({ t: 'available', info: info });
      try { live.downloadUpdate(); }
      catch (e) { set({ t: 'error', err: e, phase: 'available' }); }
    });
    live.on('update-not-available', function () { set({ t: 'none' }); });
    live.on('download-progress', function (p) { set({ t: 'progress', p: p }); });
    live.on('update-downloaded', function (info) { set({ t: 'downloaded', info: info }); });
    live.on('error', function (e) {
      log('壳层之错（原始 ⇒ ⛔ 上屏 · 唯入日志）：' + ((e && e.message) || e));
      set({ t: 'error', err: e, phase: st.phase });
    });
  }

  function state() { return reply(st); }

  /* 查（幂等 · ⛔ 出网之自取 —— 唯 electron-updater 依 `app-update.yml` 之四栏）。 */
  function check() {
    if (!live) { return reply(st); }
    set({ t: 'checking' });
    try { live.checkForUpdates(); }
    catch (e) { set({ t: 'error', err: e, phase: 'checking' }); }
    return reply(st);
  }

  /* 装（⭐ **唯由人一次明点** ⇒ 面之钮 ／ 菜单；⛔ 自动 ⇒ 免得「偷重启」· 承 pm_1885 §三.2）。 */
  function install() {
    if (!live) { return reply(st); }
    if (st.phase !== 'downloaded') {
      log('壳层之装 ⛔ 行（态 ＝ ' + st.phase + '）⇒ 唯「已下毕」方装（承 pm_1885 §三.2 · ⛔ 谎报「已装」）');
      return reply(st);
    }
    set({ t: 'installing' });
    try { live.quitAndInstall(); }               // ⭐ 唯此一处 —— 其重启由**面之钮**先明书（「重启并安装」）
    catch (e) { set({ t: 'error', err: e, phase: 'installing' }); }
    return reply(st);
  }

  return { state: state, check: check, install: install };
}

module.exports = {
  PHASES: PHASES, CODES: CODES, DEST: DEST, WORD: WORD,
  blank: blank, progressOf: progressOf, classify: classify, reduce: reduce, reply: reply,
  createController: createController, selfTest: selfTest
};

/* ---------------------------------------------------------------- 自证（离机 · 纯 · ⛔ electron ／ ⛔ 网） */
function selfTest() {
  var fails = [];
  function say(ok, name) { if (!ok) { fails.push(name); } print((ok ? '  OK ' : '  X  ') + name); }
  function print(s) { if (typeof console !== 'undefined' && console.log) { console.log(s); } }

  var b = blank('9.0.10');
  say(b.phase === 'idle' && b.current === '9.0.10', '正控：初态 ＝ idle ∧ current 照载');
  say(reply(b).ok === true && reply(b).phase === 'idle', '正控：idle ⇒ ok:true ＋ phase');

  var a = reduce(b, { t: 'available', info: { version: '9.0.11' } });
  say(a.phase === 'available' && a.latest === '9.0.11', '正控：available ⇒ latest 照载');

  var pr = reduce(a, { t: 'progress', p: { transferred: 512, total: 1024 } });
  say(pr.phase === 'downloading' && pr.progress.pct === 50, '正控：progress ⇒ pct ＝ 50');
  var pr0 = reduce(a, { t: 'progress', p: { transferred: 7, total: 0 } });
  say(pr0.progress.pct === null && pr0.progress.done === 7, '反控：total ⛔ 可量 ⇒ pct ＝ null（⛔ 编数）');

  var dn = reduce(pr, { t: 'downloaded', info: { version: '9.0.11' } });
  say(dn.phase === 'downloaded' && dn.progress === null, '正控：downloaded ⇒ progress 归空');

  say(classify(new Error('sha512 checksum mismatch'), 'downloading') === 'verify-failed', '码：sha512 ⇒ verify-failed');
  say(classify(new Error('connect ECONNREFUSED 192.0.2.1:80'), 'checking') === 'offline', '码：ECONNREFUSED ⇒ offline');
  say(classify(new Error('boom'), 'downloading') === 'download-failed', '码：下载期之错 ⇒ download-failed');
  say(classify(new Error('boom'), 'checking') === 'check-failed', '码：查期之错 ⇒ check-failed');
  say(classify(new Error('boom'), 'installing') === 'install-failed', '码：装期之错 ⇒ install-failed');
  say(classify(new Error(''), 'idle') === 'unknown', '码：空 ⇒ unknown');
  say(CODES.indexOf(classify(new Error('x'), 'idle')) >= 0, '码：恒属七码之一');
  say(PHASES.indexOf(reduce(b, { t: 'error', err: new Error('x') }).phase) >= 0, '态：error ⇒ failed（属八字）');

  var f = reduce(b, { t: 'error', err: new Error('ECONNREFUSED C:\\Users\\x') });
  var r = reply(f);
  say(r.ok === false && r.code === 'offline' && !!r.message, '败 ⇒ ok:false ＋ code ＋ message');
  say(r.phase === 'failed', '败 ⇒ phase 亦在（面可判）');
  var bad = ['electron-updater', 'NSIS', 'blockmap', 'quitAndInstall', 'http://', 'C:' + String.fromCharCode(92)];
  var hit = bad.filter(function (w) { return String(r.message).indexOf(w) >= 0; });
  say(hit.length === 0, '反控：message ⛔ 载行话 ／ 径 ／ 端点（命中： ' + hit.join(',') + ' ）');
  say(String(r.message).indexOf('去处：') >= 0, '败 ⇒ message 载「去处」（承 pm_1890 §一.3）');
  say(JSON.stringify(r).indexOf('ECONNREFUSED') < 0, '反控：原始之错 ⛔ 上屏');

  var su = createController({ updater: null, current: '9.0.10', packaged: true });
  var rs = su.state();
  say(rs.phase === 'unsupported' && rs.ok === false && rs.code === 'no-updater',
      '反控：⛔ 更新器 ⇒ unsupported ／ no-updater（面据以判「此壳 ⛔ 供此能」）');
  var sudev = createController({ updater: makeFake(), current: '9.0.10', packaged: false });
  say(sudev.state().phase === 'unsupported', '反控：开发态 ⇒ unsupported（⛔ 真跑更新器）');

  function makeFake() {
    var h = {};
    var o = {
      autoDownload: true, dl: 0, qi: 0, ck: 0,
      on: function (ev, cb) { (h[ev] = h[ev] || []).push(cb); },
      emit: function (ev, arg) { (h[ev] || []).forEach(function (cb) { cb(arg); }); },
      checkForUpdates: function () { o.ck += 1; o.emit('checking-for-update'); },
      downloadUpdate: function () { o.dl += 1; },
      quitAndInstall: function () { o.qi += 1; }
    };
    return o;
  }

  var fake = makeFake();
  var pings = 0;
  var c = createController({ updater: fake, current: '9.0.10', packaged: true,
                             notify: function () { pings += 1; },
                             log: function () { } });
  say(fake.autoDownload === false, 'A 式：autoDownload 置 false');
  c.check();
  say(fake.ck === 1 && c.state().phase === 'checking', 'A 式：check ⇒ 查 ／ 态 ＝ checking');
  fake.emit('update-available', { version: '9.0.11' });
  say(fake.dl === 1, 'A 式：有新版 ⇒ 自动 downloadUpdate（1 次）');
  say(c.state().phase === 'available' && c.state().latest === '9.0.11', 'A 式：态 ＝ available');
  say(fake.qi === 0, '反控：⛔ 未经人点 ⇒ ⛔ 装（⛔ 偷重启）');
  fake.emit('update-downloaded', { version: '9.0.11' });
  say(c.install().phase === 'installing' && fake.qi === 1, '正控：已下毕 ＋ 人点 ⇒ quitAndInstall（1 次）');
  say(pings >= 4, '推：每事皆唤面**再拉**（ping 计 ＝ ' + pings + '）');
  var c2 = createController({ updater: makeFake(), current: '9.0.10', packaged: true, log: function () { } });
  say(c2.install().phase === 'idle', '反控：未下毕 ⇒ 装 ⛔ 行（态照旧 · ⛔ 谎报「已装」）');

  print('=== shell_update 自证 ' + (fails.length ? ('FAIL ' + fails.length) : 'PASS') + ' ===');
  if (fails.length) { fails.forEach(function (x) { print('  [FAIL] ' + x); }); return 1; }
  return 0;
}
