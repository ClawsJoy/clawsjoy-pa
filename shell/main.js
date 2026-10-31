'use strict';
/*
 * main.js —— ClawsJoy PA 桌面壳（Electron）之「壳层」主进程。
 * 承 pm_1672 §五.1（① 载荷入包 ⇒ ② 首启起服 ⇒ ③ version.json 之接 ⇒ ④ 单实例 ＋ 窗态
 * ⇒ ⑤ shell.openPath 开落点目录 ⇒ ⑥ 出包）＋ pm_1672 §五.2（双层更新之交界）。
 *
 * 硬约（**一处定形**）：
 *   * **ROOT** ＝ `process.resourcesPath/payload`（装根 ＝ **载荷之根**；⛔ 依外之 D:\clawsjoy_v9）
 *     ⇒ 载荷（`core\` ／ `web\` ／ `scripts\win_pa\` ／ `runtime\` ／ `wheel\`）皆自壳内出。
 *   * **版之真源** ＝ 载荷内 `core/lib/version.py:__version__`（⛔ 取壳之 `package.json` 之版 ⇒ 二者异层）；
 *     装根 `version.json` **建时**落（`make_payload.py` ⇒ 形唯 `installer_post.version_payload` 出），
 *     壳首启唯**核**之（⛔ 自造 ／ ⛔ 运行时私改装根）—— `/health.build` 之读即此件。
 *   * **窗之址** ＝ 本机之 `127.0.0.1:<port>`（<port> 由 `scripts\win_pa\port_lite.py` **薄径**读 ⇒ ⛔ 字面）。
 *   * **⛔ 出机**：本档 ⛔ 引网络之能（唯 `127.0.0.1` 之探活 + 用户点「检查更新」时之 electron-updater）。
 */
const { app, BrowserWindow, Tray, Menu, shell, dialog, ipcMain, nativeImage, globalShortcut, screen, WebContentsView, session, desktopCapturer } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');
const ID = require('./identity');   // ⭐ 身份之判（**一处定形** · pm_1679 §四）
const UP = require('./update');     // ⭐ 载荷层之更新之器（**一处定形** · pm_1684 §二）
const SU = require('./shell_update');  // ⭐ 壳层之更新之策（**一处定形** · pm_1885 §三 ／ pm_1890 §一）

const APP_ID = 'com.clawsjoy.pa';
const SELFTEST = !!process.env.CLAWSJOY_SHELL_SELFTEST;
const PACKAGED = app.isPackaged;

// ---------------------------------------------------------------- 径（一处定形）
function rootDir() {
  if (process.env.CLAWSJOY_ROOT) { return process.env.CLAWSJOY_ROOT; }
  if (PACKAGED) { return path.join(process.resourcesPath, 'payload'); }
  return path.join(__dirname, '..', 'dist', 'pa_shell', 'payload');
}
function localDir() {
  const la = process.env.LOCALAPPDATA || path.join(process.env.USERPROFILE || '.', 'AppData', 'Local');
  return path.join(la, 'ClawsJoyPA', 'shell');
}
function pyExe() {
  return process.env.CLAWSJOY_PY || path.join(rootDir(), 'runtime', 'python.exe');
}
function paNowindow() { return path.join(rootDir(), 'scripts', 'win_pa', 'pa_nowindow.py'); }
function portLite() { return path.join(rootDir(), 'scripts', 'win_pa', 'port_lite.py'); }
function versionJson() { return path.join(rootDir(), 'version.json'); }
function versionPy() { return path.join(rootDir(), 'core', 'lib', 'version.py'); }
function logsDir() { return path.join(rootDir(), 'logs'); }
function windowStateFile() { return path.join(localDir(), 'window.json'); }
function shellLogFile() { return path.join(localDir(), 'shell.log'); }

/* 落点目录（**一处定形** · 与后端 `core/lib/feedback_target.py:feedback_dir` 同序）：
   env PA_FEEDBACK_DIR ⇒ `config/feedback_target.yaml` 之平表 `dir:` ⇒ 默认 `data/pa/feedback`（相对装根）。 */
/* 后端所出之读数（**一处定形** · pm_1679 §五.1⒝）：载荷之路径唯 `/health` 出
   （承「读一处（`/health`）· 动分端」之律）⇒ 壳 ⛔ 自算（否则「一改一不改」⇒ 面之校必假红）。 */
let BACKEND_DIRS = { feedback: null, build_path: null, at: null };
function refreshBackendDirs(j) {
  try {
    const fb = (j && j.feedback) || {};
    const bd = (j && j.build) || {};
    if (fb.resolved_dir) { BACKEND_DIRS.feedback = String(fb.resolved_dir); }
    if (bd.path) { BACKEND_DIRS.build_path = String(bd.path); }
    BACKEND_DIRS.at = Date.now();
  } catch (e) { /* 照实：下面之报会显其因 */ }
}

/* 落点目录：后端所出为主（上）；回落（服未起 ⁄ `/health` ⛔ 答）则与后端同序算之（一处定形）。 */
function feedbackDirLocal() {
  let d = (process.env.PA_FEEDBACK_DIR || '').trim();
  if (!d) {
    const f = path.join(rootDir(), 'config', 'feedback_target.yaml');
    try {
      const txt = fs.readFileSync(f, 'utf8');
      const m = txt.match(/^\s*dir\s*:\s*(.+)$/m);
      if (m) { d = m[1].trim().replace(/^["']|["']$/g, '').replace(/\s+#.*$/, ''); }
    } catch (e) { /* 未见 ⇒ 默认（照实：下面之报会显其径） */ }
  }
  if (!d) { d = 'data/pa/feedback'; }
  // ⭐ 与后端 `feedback_target.feedback_dir` 同形：相对 ⇒ 挂装根，并**归一**
  //   （后端已以 `os.path.normpath` 归一 —— 二处同形 ⇒ 面之校假红之根已去）。
  return path.isAbsolute(d) ? path.normalize(d) : path.join(rootDir(), d);
}
function feedbackDir() { return BACKEND_DIRS.feedback || feedbackDirLocal(); }

// ---------------------------------------------------------------- 记账（机器面之日志）
function log() {
  const line = '[shell] ' + Array.prototype.slice.call(arguments).join(' ');
  console.log(line);
  try {
    fs.mkdirSync(localDir(), { recursive: true });
    fs.appendFileSync(shellLogFile(), line + '\n', 'utf8');
  } catch (e) { /* 日志写 ⛔ 得 ⇒ 唯 console（⛔ 崩） */ }
}

// ---------------------------------------------------------------- 子进程
function runPy(args, timeoutMs) {
  return new Promise(function (resolve) {
    let out = '';
    let done = false;
    const to = timeoutMs || 300000;
    let timer = null;
    const finish = function (code, why) {
      if (done) { return; }
      done = true;
      if (timer) { clearTimeout(timer); }
      resolve({ code: code, out: out, why: why || '' });
    };
    let p = null;
    try {
      p = spawn(pyExe(), ['-X', 'utf8', '-B'].concat(args), { cwd: rootDir(), windowsHide: true });
    } catch (e) {
      finish(-1, 'SPAWN: ' + (e && e.message));
      return;
    }
    timer = setTimeout(function () { try { p.kill(); } catch (e) {} finish(-1, 'TIMEOUT'); }, to);
    p.stdout.on('data', function (d) { out += d.toString('utf8'); });
    p.stderr.on('data', function (d) { out += d.toString('utf8'); });
    p.on('error', function (e) { finish(-1, 'ERROR: ' + (e && e.message)); });
    p.on('close', function (code) { finish(code, ''); });
  });
}

// ---------------------------------------------------------------- 端口（薄径）
let PORT = null;
let PORT_WHY = '';
async function readPort() {
  const r = await runPy([portLite(), '--root', rootDir()], 60000);
  const tail = (r.out || '').trim().split('\n').filter(function (x) { return x.trim(); });
  const last = tail.length ? tail[tail.length - 1].trim() : '';
  const n = parseInt(last, 10);
  if (r.code === 0 && n > 0) { PORT = n; PORT_WHY = ''; return n; }
  PORT = null;
  PORT_WHY = 'rc=' + r.code + ' ／ ' + last.slice(0, 160);
  return null;
}
function paUrl() { return PORT ? ('http://127.0.0.1:' + PORT + '/web/pa.html?paWin=1') : ''; }

// ---------------------------------------------------------------- ② ③ 首启（version.json 之核 ⇒ 起服）
async function firstRunCheck() {
  const res = { version_json: versionJson(), exists: fs.existsSync(versionJson()),
                version: null, error: null, body: null };
  if (!res.exists) {
    log('⛔ 见装根 version.json —— 本应随「壳内载荷」建时落（`make_payload.py` 之 `installer_post.version_payload`）'
        + ' ⇒ 报照实 ∧ `get /health.build.available` 必 false；⛔ 运行时私改装根（免 HKCU ／ 启动器 ／ install_record 之杂）');
  }
  try {
    const j = JSON.parse(fs.readFileSync(versionJson(), 'utf8'));
    res.version = j.version || null;
    res.body = j;
    log('装根 version.json：version=' + res.version + ' ／ channel=' + j.channel
        + ' ／ commit=' + String(j.commit || '-').slice(0, 12) + ' ／ tree=' + String(j.tree || '-').slice(0, 12));
  } catch (e) {
    res.error = String((e && e.message) || e);
    log('装根 version.json 读 ⛔ 得：' + res.error);
  }
  return res;
}

// ------------------------------------------------ 安装期之记（任务定形之果 · 上报一次 · 承 pm_1896 §二.3⒞）
/* 由：NSIS 壳器于装毕跑 `scripts/win_pa/install_tasks_silent.py --go`（`shell/build/tasks.nsh` —— 其转调
 *   `install_win_pa` 之任务之路 ⇒ 一处定形）⇒ 其记唯落 `%LOCALAPPDATA%\ClawsJoyPA\shell\`（与 `shell.log`
 *   同处）；⭐ 壳首启**报一次**：rc ⛔ 0 ⇒ 上屏明书（**因 ＋ 去处**）· 报毕**改名**（⛔ 每启皆报 —— 免噪声）
 *   ∧ ⛔ 阻壳（任务败而阻壳 ＝ 更坏之态 · 承 pm_1896 §二.3⒞）。 */
function installTasksRecord() { return path.join(localDir(), 'install_tasks.rc'); }
async function reportInstallTasksOnce() {
  const rcFile = installTasksRecord();
  let txt = null;
  try { if (fs.existsSync(rcFile)) { txt = fs.readFileSync(rcFile, 'utf8'); } } catch (e) { txt = null; }
  if (txt == null) { return null; }
  try { fs.renameSync(rcFile, rcFile + '.reported'); } catch (e) { /* ⛔ 改得 ⇒ 唯日志 */ }
  const m = String(txt).match(/rc=(\S*)/);
  const raw = m ? m[1] : '';
  const rc = /^-?\d+$/.test(raw) ? Number(raw) : null;   // ⭐ ⛔ 编数：⛔ 数字者 ⇒ null（照实）
  log('安装期之记（计划任务之形）：rc=' + (rc === null ? ('⛔ 数（' + raw + '）') : rc));
  if (rc === 0) { return { rc: 0 }; }
  await showLines('安装：计划任务之形 ⛔ 成（桌面程序照装）', [
    '因：装桌面程序时「计划任务之形」定形 ⛔ 成（rc=' + (rc === null ? (raw || '未记') : rc) + '）',
    '果：开机 ／ 定时那两条任务或仍旧形 ⇒ 可能仍有控制台窗一闪',
    '去处：' + path.join(localDir(), 'install_tasks.log')
  ]);
  return { rc: rc };
}


// 器之核（**唯自测用之** —— 产品之径 ⛔ 重解版号：⛔ 二处各写）
function payloadVersionByRead() {
  try {
    const t = fs.readFileSync(versionPy(), 'utf8');
    const m = t.match(/^__version__\s*=\s*u?["']([^"']+)["']/m);
    return m ? m[1] : null;
  } catch (e) { return null; }
}

// ---------------------------------------------------------------- 探活 ／ 起停
/* 探活（**一处定形** · `identity.js`）：唯 `127.0.0.1` · ⛔ 出机。 */
function probeHealthAt(port) { return ID.probeHealthAt(port); }
function probeHealth() { return ID.probeHealthAt(PORT); }
async function waitHealth(ms) {
  const t0 = Date.now();
  for (;;) {
    const h = await probeHealth();
    if (h.ok) { return { ok: true, ms: Date.now() - t0, status: h.status }; }
    if (Date.now() - t0 >= ms) { return { ok: false, ms: Date.now() - t0, status: h.status, why: String(h.body).slice(0, 160) }; }
    await sleep(500);
  }
}
function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

/* ⭐ 身份之核（一处定形 · pm_1679 §四）：应答者是否本壳之载荷？⛔ 则静默载旧页。 */
async function serviceIdentity(port) {
  const h = await ID.probeHealthAt(port || PORT);
  if (!h.ok) { return { ok: false, why: 'health-⛔-答', status: h.status, want: versionJson() }; }
  let j = null;
  try { j = JSON.parse(h.body); } catch (e) { return { ok: false, why: 'health-⛔-JSON', want: versionJson() }; }
  refreshBackendDirs(j);
  return ID.evaluateHealth(j, versionJson());
}

async function startService() {
  log('起服：pa_nowindow.py start');
  const r = await runPy([paNowindow(), 'start'], 300000);
  const tail = (r.out || '').trim().split('\n').slice(-2).join(' | ');
  log('start rc=' + r.code + ' :: ' + tail.slice(0, 200));
  const h = await waitHealth(120000);
  log('起后 /health ok=' + h.ok + '（' + h.ms + ' ms）');
  return { start_rc: r.code, health_ok: h.ok, health_ms: h.ms, tail: tail.slice(0, 200) };
}
async function stopService() {
  log('停服：pa_nowindow.py stop');
  const r = await runPy([paNowindow(), 'stop'], 180000);
  const tail = (r.out || '').trim().split('\n').slice(-2).join(' | ');
  log('stop rc=' + r.code + ' :: ' + tail.slice(0, 200));
  return { stop_rc: r.code, tail: tail.slice(0, 200) };
}

// ---------------------------------------------------------------- ④ 窗态之记忆
function loadWindowState() {
  const d = { width: 1180, height: 800 };
  try {
    const j = JSON.parse(fs.readFileSync(windowStateFile(), 'utf8'));
    ['width', 'height', 'x', 'y'].forEach(function (k) { if (typeof j[k] === 'number') { d[k] = j[k]; } });
  } catch (e) { /* 无 ⇒ 默认 */ }
  return d;
}
function liveWin() { return (win && !win.isDestroyed()) ? win : null; }

function showMain() {
  if (!liveWin()) { createWindow(); }
  const w = liveWin();
  if (!w) { return; }
  try { if (w.isMinimized()) { w.restore(); } } catch (e) { /* 照退 */ }
  w.show();
  w.focus();
}

function saveWindowState() {
  const w = liveWin();
  if (!w) { return; }
  try {
    const b = w.getNormalBounds();
    fs.mkdirSync(localDir(), { recursive: true });
    fs.writeFileSync(windowStateFile(), JSON.stringify(
      { width: b.width, height: b.height, x: b.x, y: b.y }, null, 1), 'utf8');
  } catch (e) { log('窗态之存 ⛔ 得：' + (e && e.message)); }
}

// ---------------------------------------------------------------- ⑤ 落点目录之开（桥之壳侧）
async function openFeedbackDir() {
  const d = feedbackDir();
  try {
    fs.mkdirSync(d, { recursive: true });
    const err = await shell.openPath(d);
    if (err) { return { ok: false, code: 'E_OPEN', message: String(err) }; }
    return { ok: true, path: d };
  } catch (e) {
    return { ok: false, code: 'E_SHELL', message: String((e && e.message) || e) };
  }
}

// ---------------------------------------------------------------- 窗
let IDENTITY = null;   // 身份之判之果（一处）—— 非 null 且 !ok ⇒ ⛔ 载载荷之页

let win = null;
let tray = null;
let trayMenu = null;
let appMenu = null;
let isQuitting = false;
let paBrowserView = null;
let recWin = null;
let screenPick = { id: '', audio: false };
let browserLastBounds = null;
let browserHtmlFull = false;
const SCREEN_AUTOSELECT = process.env.PA_SCREEN_AUTOSELECT === '1';
const PA_BROWSER_PART = 'persist:pa-web';
const st = { window: false, page_loaded: false, url: null, title: null, load_error: null };

/* 人话之页（⛔ 载载荷之页 · ⛔ 白屏）—— 一处定形。 */
function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
function msgPageHtml(title, lines) {
  return 'data:text/html;charset=utf-8,' + encodeURIComponent('<h2>' + esc(title) + '</h2>'
    + (lines || []).map(function (t) { return '<p>' + esc(t) + '</p>'; }).join(''));
}


/* ── 内置浏览器 P0（WebContentsView · 独立 session · 无 Node） ── */
function ensureBrowserView() {
  const w = liveWin();
  if (!w) { return null; }
  if (paBrowserView && !paBrowserView.webContents.isDestroyed()) { return paBrowserView; }
  try {
    const ses = session.fromPartition(PA_BROWSER_PART);
    ses.setPermissionRequestHandler(function (_wc, permission, cb) {
      // WebContentsView 的 requestFullscreen 也要走权限；只放行 fullscreen，其它一律拒。
      cb(String(permission || '') === 'fullscreen');
    });
    try {
      ses.setPermissionCheckHandler(function (_wc, permission) {
        return String(permission || '') === 'fullscreen';
      });
    } catch (e) { }
    paBrowserView = new WebContentsView({
      webPreferences: {
        session: ses, nodeIntegration: false, contextIsolation: true,
        sandbox: true, webSecurity: true, spellcheck: false, backgroundThrottling: false
      }
    });
    try { paBrowserView.webContents.setBackgroundThrottling(false); } catch (e) { }
    paBrowserView.setBackgroundColor('#0d1117');
    w.contentView.addChildView(paBrowserView);
    paBrowserView.webContents.setWindowOpenHandler(function (details) {
      try {
        var u = String((details && details.url) || '');
        if (/^https?:\/\//i.test(u)) {
          setTimeout(function () {
            try { if (paBrowserView && !paBrowserView.webContents.isDestroyed()) { paBrowserView.webContents.loadURL(u); } } catch (e) { }
          }, 0);
        }
      } catch (e) { }
      return { action: 'deny' };
    });
    paBrowserView.webContents.on('will-navigate', function (e, url) {
      if (!/^https?:\/\//i.test(String(url || ''))) { e.preventDefault(); }
    });
    paBrowserView.webContents.on('before-input-event', function (e, input) {
      try {
        if (String(input && input.key) === 'Escape' && browserHtmlFull) {
          e.preventDefault();
          try { paBrowserView.webContents.executeJavaScript('if(document.fullscreenElement){document.exitFullscreen();}', true); } catch (err2) { }
          setBrowserFull(false);
        }
      } catch (err) { }
    });
    var ping = function () {
      try { if (liveWin()) { liveWin().webContents.send('pa:browser-ping'); } } catch (e) { }
    };
    paBrowserView.webContents.on('did-finish-load', ping);
    paBrowserView.webContents.on('did-navigate', ping);
    paBrowserView.webContents.on('page-title-updated', ping);
    paBrowserView.webContents.on('enter-html-full-screen', function () {
      try {
        var w = liveWin(); if (!w || !paBrowserView) { return; }
        browserHtmlFull = true;
        var c = w.getContentBounds();
        paBrowserView.setBounds({ x: 0, y: 0, width: c.width, height: c.height });
        paBrowserView.setVisible(true);
      } catch (e) { }
    });
    paBrowserView.webContents.on('leave-html-full-screen', function () {
      try {
        var w = liveWin(); if (!w) { return; }
        browserHtmlFull = false;
        if (paBrowserView && browserLastBounds) { paBrowserView.setBounds(browserLastBounds); }
      } catch (e) { }
    });
    paBrowserView.setVisible(false);
    log('浏览器 P0：WebContentsView 已立（partition=' + PA_BROWSER_PART + '）');
  } catch (e) {
    log('浏览器 P0：⛔ 立（' + ((e && e.message) || e) + '）');
    paBrowserView = null;
  }
  return paBrowserView;
}

function browserBounds(b) {
  const w = liveWin();
  if (!w) { return { x: 0, y: 0, width: 0, height: 0 }; }
  const c = w.getContentBounds();
  const x = Math.max(0, Math.round(Number((b && b.x) || 0)));
  const y = Math.max(0, Math.round(Number((b && b.y) || 0)));
  const width = Math.max(0, Math.min(Math.round(Number((b && b.width) || 0)), c.width - x));
  const height = Math.max(0, Math.min(Math.round(Number((b && b.height) || 0)), c.height - y));
  return { x: x, y: y, width: width, height: height };
}

function browserHide() {
  try { if (paBrowserView) { paBrowserView.setVisible(false); } } catch (e) { }
}

function setBrowserFull(on) {
  try {
    var w = liveWin(); if (!w || !paBrowserView) { return false; }
    browserHtmlFull = on === true;
    if (browserHtmlFull) {
      var c = w.getContentBounds();
      paBrowserView.setBounds({ x: 0, y: 0, width: c.width, height: c.height });
      paBrowserView.setVisible(true);
    } else if (browserLastBounds) {
      paBrowserView.setBounds(browserLastBounds);
    }
    return true;
  } catch (e) { return false; }
}

function browserCloseView() {
  try { if (paBrowserView && liveWin()) { liveWin().contentView.removeChildView(paBrowserView); } } catch (e) { }
  try { if (paBrowserView) { paBrowserView.webContents.close(); } } catch (e) { }
  paBrowserView = null;
}

async function browserRead() {
  const v = ensureBrowserView();
  if (!v) { return { ok: false, error: '浏览器未立' }; }
  const js = `
(() => {
  const vs = Array.from(document.querySelectorAll('video'));
  const ranked = vs.map(function(x){ var r=x.getBoundingClientRect(); return {v:x, area:(r.width||0)*(r.height||0)}; })
    .filter(function(x){ return x.area > 100; }).sort(function(a,b){ return b.area-a.area; });
  const vv = ranked.length ? ranked[0].v : (vs.length ? vs[0] : null);
  const sel = String(window.getSelection ? window.getSelection().toString() : '');
  const root = document.querySelector('article') || document.querySelector('main') || document.querySelector('[role=main]') || document.body;
  const md = document.querySelector('meta[name="description"]') || document.querySelector('meta[property="og:description"]');
  const caps = [];
  let capSrc = '';
  try {
    if (vv && vv.textTracks) {
      for (let i=0;i<vv.textTracks.length;i++) {
        const tt = vv.textTracks[i];
        if (tt && tt.cues) for (let j=0;j<tt.cues.length;j++) {
          const tx = String(tt.cues[j].text || '').trim(); if (tx) caps.push(tx);
        }
      }
    }
  } catch (e) {}
  if (!caps.length) {
    try { const segs = document.querySelectorAll('.ytp-caption-segment'); for (let k=0;k<segs.length;k++) { const t2=String(segs[k].textContent||'').trim(); if(t2) caps.push(t2); } if (segs.length) capSrc='youtube-caption'; } catch (e) {}
  }
  if (!caps.length) {
    try { const trs = document.querySelectorAll('ytd-transcript-segment-renderer'); for (let q=0;q<trs.length;q++) { const t3=String(trs[q].innerText||'').trim(); if(t3) caps.push(t3); } if (trs.length) capSrc='youtube-transcript-panel'; } catch (e) {}
  }
  return {
    url: location.href, title: document.title,
    selection: sel.slice(0, 20000),
    text: (document.body ? document.body.innerText : '').slice(0, 20000),
    mainText: root ? String(root.innerText || '').slice(0, 20000) : '',
    description: md ? String(md.getAttribute('content') || '').slice(0, 4000) : '',
    video: vv ? { src: vv.currentSrc || vv.src || '', poster: vv.poster || '',
      duration: Number(vv.duration || 0), currentTime: Number(vv.currentTime || 0),
      paused: !!vv.paused, width: Number(vv.videoWidth || 0), height: Number(vv.videoHeight || 0) } : null,
    captions: { text: caps.join(String.fromCharCode(10)).slice(0, 30000), source: capSrc, count: caps.length }
  };
})()
`;
  const out = await v.webContents.executeJavaScript(js, false);
  return { ok: true, page: out };
}

function createWindow(msg) {
  const s = loadWindowState();
  win = new BrowserWindow({
    width: s.width, height: s.height, x: s.x, y: s.y,
    minWidth: 900, minHeight: 600,
    title: 'ClawsJoy PA',
    show: false,
    autoHideMenuBar: false,
    icon: path.join(__dirname, 'icon.png'),
    webPreferences: { nodeIntegration: false, contextIsolation: true, preload: path.join(__dirname, 'preload.js') }
  });
  st.window = true;
  if (!SELFTEST) { win.once('ready-to-show', function () { win.show(); }); }
  win.webContents.on('did-finish-load', function () {
    st.page_loaded = true; st.url = win.webContents.getURL(); st.title = win.webContents.getTitle();
    log('页已载：' + st.url);
    // 召出之「发」若遇主窗页未载毕 ⇒ 载毕补送（⛔ 丢字 · ⛔ 假成）
    if (SUM.pendingSend) { const t = SUM.pendingSend; SUM.pendingSend = null; summonPlanInMain(t); }
  });
  win.webContents.on('did-fail-load', function (_e, code, desc, url) {
    st.load_error = code + ' ' + desc + ' ' + url;
    log('页载败：' + st.load_error);
  });
  win.on('close', function () { saveWindowState(); if (!isQuitting && !SELFTEST) { win.hide(); return false; } });
  win.on('closed', function () { paBrowserView = null; });
  try {
    win.webContents.session.setPermissionRequestHandler(function (wc, permission, cb) {
      var u = ''; try { u = wc.getURL() || ''; } catch (e) { }
      cb((permission === 'media' || permission === 'display-capture') && /^http:\/\/127\.0\.0\.1[:/]/.test(u));
    });
    win.webContents.session.setPermissionCheckHandler(function (_wc, permission, origin) {
      return (permission === 'media' || permission === 'display-capture') && /^http:\/\/127\.0\.0\.1[:/]/.test(String(origin || ''));
    });
    win.webContents.session.setDisplayMediaRequestHandler(function (_request, callback) {
      desktopCapturer.getSources({ types: ['screen', 'window'] }).then(function (sources) {
        if (!sources || !sources.length) { callback({}); return; }
        var src = sources[0];
        for (var i = 0; i < sources.length; i++) { if (screenPick.id && sources[i].id === screenPick.id) { src = sources[i]; break; } }
        var out = { video: src };
        if (screenPick.audio && process.platform === 'win32') { out.audio = 'loopback'; }
        callback(out);
      }).catch(function () { callback({}); });
    }, { useSystemPicker: false });
  } catch (e) { log('权限门 ⛔ 立：' + ((e && e.message) || e)); }
  if (msg) { win.loadURL(msgPageHtml('ClawsJoy PA', msg)); }
  else if (PORT) { win.loadURL(paUrl()); }
  else { win.loadURL(msgPageHtml('ClawsJoy PA', ['⛔ 得端口：' + PORT_WHY,
    '因 ＋ 去处：见 %LOCALAPPDATA%\\ClawsJoyPA\\shell\\shell.log'])); }
  log('窗已立（' + s.width + 'x' + s.height + '）');
}

function reloadPage() {
  const w = liveWin();
  if (!w) { return; }
  if (IDENTITY && !IDENTITY.ok) { w.loadURL(msgPageHtml('ClawsJoy PA', ID.identityMessage(IDENTITY))); return; }
  if (PORT) { w.loadURL(paUrl()); }
}

// ------------------------------------------------ ④b 召出（全局热键 ＋ 无框 Summon 浮窗 · PA v1.1.1 S1）
/* 承 docs/reports/_pa_groundwork_20261027/61_PA_v1.1验收_v1.md §四.1（外框 536x123 之 P1 gap：
   原生题栏运行时 ⛔ 可去 ⇒ 真无框须另立 frame:false 之窗 ⇒ 本版立之；主窗 ⛔ 缩形 · ⛔ 动其态）
   ／ docs/design/v9_pa_window_prd_v1.md §3.1（520x84 · 召出 < 100ms · Esc 收 · 草稿留 5 分钟）
   ／ 59_PA_v1.1迭代单_v1.md §二 S1（注册失败 ⇒ 托盘「召出」兜底 · ⛔ 静默失效）。
   **一处定形**：
     * 热键之串唯 SUMMON_ACC；浮窗之尺唯 SUMMON_BOX（520x84 ＝ PRD §3.1 之含 1px 边）；
     * 浮窗之形唯 shell/summon.html —— 其 Summon 之六行照 web/pa/faces/window.js 之 summonHtml()
       （⚠ 二源之险明书：web 之页 ⛔ 可入此窗 —— 否则外框非 520x84）；
     * 浮窗之式唯 payload 之 pa.css ＋ pa_v3.css ＋ SUMMON_OVERLAY_CSS（壳侧 insertCSS · ⛔ 改 web 一字）；
     * 浮窗之行唯 payload 之 web/pa/faces/summon.js（壳侧 executeJavaScript 载之 ⇒ paWinSummonOpen/Close
       ／ 草稿 5 分钟 ／ Enter 发 ／ Esc 收 皆仍其一处之形）；
     * 「发」之桥：summon.js 之 paWinPlan ⇒ shell/summon.html 之桥 ⇒ IPC pa:summon-send ⇒ 主窗
       executeJavaScript(paWinPlan(…))（计划卡仍出一处：主窗之页）。
   ⚠ 界（明书）：① 召出必收键盘焦点（PRD §8「焦点在输入框」）；失焦即收；收后 hide() ⇒ 焦点自归前台之应用；
     ② 本版 ⛔ 变 Summon 之形（陪／办／查 三芯片照旧）；③ 浮窗之页 ⛔ 载整页 PA（一方载荷之页已热於主窗）。 */
const SUMMON_ACC = 'CommandOrControl+Shift+Space';
const SUMMON_ACC_LABEL = 'Ctrl+Shift+Space';
const SUMMON_ENTRY_ID = 'pa-summon-entry';
const SUMMON_BOX = { width: 520, height: 84 };
const SUMMON_MARGIN = 16;               // 默认贴右下角：距工作区右/下各 16px
const SUMMON_OPEN_TIMEOUT_MS = 800;
const SUMMON_POS_FILE = path.join(process.env.LOCALAPPDATA || __dirname, 'ClawsJoyPA', 'summon_pos.json');

/* 浮窗之式（壳侧 · ⛔ 改 web）：窗即 520x84 之透明无框 ⇒ 页内 .pa-summon 须成「满窗之一件」，
   底色透明（圆角 14 由 pa_v3.css 出），余皆无。 */
const SUMMON_OVERLAY_CSS = [
  'html,body{width:100%;height:100%;margin:0!important;padding:0!important;overflow:hidden!important;background:transparent!important}',
  '.pa-summon{position:fixed!important;left:0!important;top:0!important;right:0!important;bottom:0!important;'
    + 'transform:none!important;width:100%!important;max-width:none!important;height:100%!important;min-height:0!important;'
    + 'margin:0!important;box-sizing:border-box!important;box-shadow:none!important;overflow:hidden!important}',
  '.pa-summon[hidden]{display:none!important}',
  '.pa-summon,.pa-summon *{-webkit-app-region:drag}',
  '.pa-summon input,.pa-summon textarea,.pa-summon button,.pa-summon .pa-chips,.pa-summon .pa-summon-foot,.pa-summon .pa-summon-foot *{-webkit-app-region:no-drag}'
].join('\n');

/* 页内之三步（**一处定形** —— ⛔ 于他处再拼）：
   open ⇒ 调页内 paWinSummonOpen()（草稿 ／ 焦点 ／ 计时皆其出）；
   收 ⇒ 调页内 paWinSummonClose(true)（保留草稿 5 分钟 · PRD §3.1）；
   态 ⇒ 只读「#paSummon.hidden」——页内自收（Enter 发 ／ Esc）由壳侧轮询认领（⛔ 改页内之码）。 */
const SUMMON_OPEN_JS = '(function(){try{'
  + 'var s=document.getElementById("paSummon");'
  + 'if(!s){return{ok:false,why:"no-summon-el"};}'
  + 'if(typeof window.paWinSummonOpen==="function"){window.paWinSummonOpen();}'
  + 'else{s.hidden=false;s.classList.add("on");}'
  + 'var inp=document.getElementById("paSummonIn");if(inp){try{inp.focus();}catch(e){}}'
  + 'var b=s.getBoundingClientRect();'
  + 'return{ok:true,ms:Math.round(((window.paWinPerf&&window.paWinPerf.summonMs)||0)*10)/10,'
  + 'w:Math.round(b.width),h:Math.round(b.height),'
  + 'active:(document.activeElement&&document.activeElement.id)||""};'
  + '}catch(e){return{ok:false,why:String((e&&e.message)||e)};}})()';
const SUMMON_CLOSE_JS = '(function(){try{'
  + 'if(typeof window.paWinSummonClose==="function"){window.paWinSummonClose(true);}'
  + '}catch(e){}return true;})()';
const SUMMON_POLL_JS = '(function(){var s=document.getElementById("paSummon");return !!(s&&s.hidden);})()';

let summonWin = null;
const SUM = {
  ready: false,      // 浮窗之页已载（summon.js 已跑）
  visible: false,    // 召出之态（壳侧 · 唯此一处）
  pending: false,    // 未就绪 ⇒ 就绪再召
  pendingSend: null, // 主窗页未载毕时「发」之暂存
  hotkey: false,     // 全局热键是否注成（⛔ 成 ⇒ 托盘兜底）
  cssKey: null,      // insertCSS 之 key（重载即换）
  tick: null,        // 页内自收之认领（150ms）
  lastToggleAt: 0,   // 键之双至（全局热键 ∧ 页内监听）⇒ 唯取其一
  openedAt: 0
};

function summonEntryLabel() {
  return SUM.hotkey ? ('召出（' + SUMMON_ACC_LABEL + '）') : '召出（热键 ⛔ · 点此召出）';
}
function refreshSummonEntry() {
  const menus = [trayMenu, appMenu];
  for (let i = 0; i < menus.length; i++) {
    if (!menus[i]) { continue; }
    const it = menus[i].getMenuItemById(SUMMON_ENTRY_ID);
    if (it) { it.label = summonEntryLabel(); }
  }
}

/* 载荷之径（浮窗之式 ／ 行皆自 ROOT 出 —— ⛔ 依外之仓根 · 一处取读） */

function showRecControl() {
  try {
    if (recWin && !recWin.isDestroyed()) { recWin.show(); recWin.focus(); return recWin; }
    const wa = screen.getPrimaryDisplay().workArea;
    const w = 248, h = 56;
    recWin = new BrowserWindow({
      width: w, height: h,
      x: wa.x + wa.width - w - 24,
      y: wa.y + wa.height - h - 24,
      frame: false, resizable: false, movable: true, minimizable: false,
      maximizable: false, fullscreenable: false, skipTaskbar: true,
      alwaysOnTop: true, show: false, backgroundColor: '#00000000',
      webPreferences: { nodeIntegration: false, contextIsolation: true, preload: path.join(__dirname, 'preload.js') }
    });
    recWin.setAlwaysOnTop(true, 'screen-saver');
    try { recWin.setContentProtection(true); } catch (e) { }
    recWin.on('closed', function () { recWin = null; });
    recWin.loadFile(path.join(__dirname, 'record.html'));
    recWin.once('ready-to-show', function () { try { recWin.show(); } catch (e) { } });
    return recWin;
  } catch (e) { log('录屏控制条 ⛔ 起：' + ((e && e.message) || e)); return null; }
}
function hideRecControl() {
  try { if (recWin && !recWin.isDestroyed()) { recWin.close(); } } catch (e) { }
  recWin = null;
}

function summonHtmlFile() { return path.join(__dirname, 'summon.html'); }
function webAsset(rel) { return path.join(rootDir(), 'web', rel); }

function loadSummonPos() {
  try {
    const raw = fs.readFileSync(SUMMON_POS_FILE, 'utf8');
    const o = JSON.parse(raw);
    if (o && Number.isFinite(o.x) && Number.isFinite(o.y)) { return { x: o.x, y: o.y }; }
  } catch (e) { /* 无档 ／ 坏档 ⇒ 用默认右下 */ }
  return null;
}

function saveSummonPos() {
  if (!summonWin || summonWin.isDestroyed() || !SUM.visible) { return; }
  try {
    const b = summonWin.getBounds();
    fs.mkdirSync(path.dirname(SUMMON_POS_FILE), { recursive: true });
    fs.writeFileSync(SUMMON_POS_FILE, JSON.stringify({ x: b.x, y: b.y }), 'utf8');
  } catch (e) { log('召出：位之存 ⛔ 得（' + ((e && e.message) || e) + '）'); }
}

let summonPosSaveTimer = null;
function scheduleSaveSummonPos() {
  if (summonPosSaveTimer) { clearTimeout(summonPosSaveTimer); }
  summonPosSaveTimer = setTimeout(function () { summonPosSaveTimer = null; saveSummonPos(); }, 350);
}

function summonBounds() {
  let wa = null;
  try {
    const d = screen.getDisplayNearestPoint(screen.getCursorScreenPoint());
    if (d && d.workArea) { wa = d.workArea; }
  } catch (e) { log('召出：屏之读 ⛔ 得（' + ((e && e.message) || e) + '）⇒ 用默认位'); }
  if (!wa) { return { x: 0, y: 0, width: SUMMON_BOX.width, height: SUMMON_BOX.height }; }
  const saved = loadSummonPos();
  if (saved) {
    return {
      x: Math.max(wa.x, Math.min(saved.x, wa.x + wa.width - SUMMON_BOX.width)),
      y: Math.max(wa.y, Math.min(saved.y, wa.y + wa.height - SUMMON_BOX.height)),
      width: SUMMON_BOX.width, height: SUMMON_BOX.height
    };
  }
  return {
    x: wa.x + wa.width - SUMMON_BOX.width - SUMMON_MARGIN,
    y: wa.y + wa.height - SUMMON_BOX.height - SUMMON_MARGIN,
    width: SUMMON_BOX.width, height: SUMMON_BOX.height
  };
}

function summonRace(p, ms) {
  return new Promise(function (resolve, reject) {
    let done = false;
    const to = setTimeout(function () { if (!done) { done = true; resolve(null); } }, ms);
    p.then(function (v) { if (!done) { done = true; clearTimeout(to); resolve(v); } },
           function (e) { if (!done) { done = true; clearTimeout(to); reject(e); } });
  });
}

/* 立浮窗（⛔ 入 SELFTEST）：frame:false ＋ transparent ＋ 520x84 ⇒ 外框 ＝ 内容 ＝ 520x84（题栏 0）。
   ⛔ parent（父窗一隐则子隐 ⇒ 与「任意前台可召」相左）；skipTaskbar ＋ alwaysOnTop ＝ 浮层之态。 */
function createSummonWindow() {
  if (summonWin && !summonWin.isDestroyed()) { return summonWin; }
  summonWin = new BrowserWindow({
    width: SUMMON_BOX.width, height: SUMMON_BOX.height,
    frame: false, transparent: true, resizable: false, movable: true,
    minimizable: false, maximizable: false, fullscreenable: false,
    skipTaskbar: true, hasShadow: false, show: false, focusable: true,
    backgroundColor: '#00000000',
    title: 'ClawsJoy PA · 召出',
    webPreferences: { nodeIntegration: false, contextIsolation: true, preload: path.join(__dirname, 'preload.js') }
  });
  summonWin.setAlwaysOnTop(true);
  summonWin.on('moved', scheduleSaveSummonPos);
  SUM.cssKey = null;
  summonWin.on('blur', function () {
    if (!SUM.visible) { return; }
    if (Date.now() - SUM.openedAt < 300) { return; }   // 召出之瞬（窗之激活未定）⇒ ⛔ 自收
    summonHide('blur');
  });
  summonWin.on('hide', function () { if (SUM.visible) { summonHide('hide'); } });
  summonWin.webContents.on('before-input-event', function (e, input) {
    if (input.type !== 'keyDown') { return; }
    // Esc 收 ／ Ctrl+Shift+Space 再按收（页内 summon.js 亦听此二键 ⇒ 壳侧先收 · ⛔ 「收而又开」）
    if (input.key === 'Escape' || input.code === 'Escape') {
      if (SUM.visible) { e.preventDefault(); summonHide('esc'); }
      return;
    }
    if ((input.control || input.meta) && input.shift && (input.code === 'Space' || input.key === ' ')) {
      SUM.lastToggleAt = Date.now();   // 全局热键若随后亦至 ⇒ 此键唯取其一
      e.preventDefault();
      if (SUM.visible) { summonHide('hotkey-key'); }
    }
  });
  summonWin.webContents.on('did-finish-load', function () { summonInitOverlay(); });
  summonWin.loadFile(summonHtmlFile());
  log('召出浮窗：立（外框 520x84 · frame:false · 透明 · 置顶）');
  return summonWin;
}

/* 浮窗之页：式自载荷之 pa.css ／ pa_v3.css（一处之形）＋ 行自 payload 之 summon.js（一处之能）。 */
async function summonInitOverlay() {
  const w = summonWin;
  if (!w || w.isDestroyed()) { return; }
  const parts = [];
  ['pa/pa.css', 'pa/pa_v3.css'].forEach(function (rel) {
    try { parts.push(fs.readFileSync(webAsset(rel), 'utf8')); }
    catch (e) { log('召出浮窗：式 ⛔ 读（' + rel + '）：' + ((e && e.message) || e)); }
  });
  parts.push(SUMMON_OVERLAY_CSS);
  try {
    if (SUM.cssKey) {
      try { Promise.resolve(w.webContents.removeInsertedCSS(SUM.cssKey)).catch(function () { /* 旧 key 或已失效 */ }); }
      catch (e) { /* 旧 key 或已失效 */ }
    }
    SUM.cssKey = await w.webContents.insertCSS(parts.join('\n'), { cssOrigin: 'user' });
  } catch (e) {
    SUM.cssKey = null;
    log('召出浮窗：式注入 ⛔ 得：' + ((e && e.message) || e));
  }
  let js = null;
  try { js = fs.readFileSync(webAsset('pa/faces/summon.js'), 'utf8'); }
  catch (e) { log('召出浮窗：summon.js ⛔ 读：' + ((e && e.message) || e)); }
  if (!js) {
    log('召出浮窗：⛔ 就绪（无 summon.js）⇒ 热键 ／ 托盘之召出将 ⛔ 成');
    return;
  }
  try {
    await w.webContents.executeJavaScript(js + '\n;window.paWinSummonBindKeys && window.paWinSummonBindKeys();', false);
    SUM.ready = true;
    log('召出浮窗：就绪（summon.js 已载 · 外框 520x84）');
    if (SUM.pending) { SUM.pending = false; summonToggle('deferred'); }
  } catch (e) {
    log('召出浮窗：summon.js ⛔ 载：' + ((e && e.message) || e));
  }
}

/* 召出（<100ms 之径：一窗已热 ＋ 一次 setBounds/show ＋ 一次 executeJavaScript ⇒ ⛔ 盘 ／ ⛔ 网 ／ ⛔ 新页）。 */
async function summonShow(why) {
  if (SUM.visible) { return true; }
  if (!summonWin || summonWin.isDestroyed()) {
    if (SELFTEST) { return false; }
    createSummonWindow();
    SUM.pending = true;
    log('召出：浮窗未立 ⇒ 立之 · 待就绪再召（' + why + '）');
    return false;
  }
  if (!SUM.ready) {
    SUM.pending = true;
    log('召出：浮窗未就绪 ⇒ 待就绪再召（' + why + '）');
    return false;
  }
  const t0 = Date.now();
  SUM.visible = true;
  SUM.openedAt = t0;
  try {
    summonWin.setBounds(summonBounds());
    summonWin.setAlwaysOnTop(true);
    summonWin.show();
    summonWin.focus();
    const r = await summonRace(summonWin.webContents.executeJavaScript(SUMMON_OPEN_JS, false), SUMMON_OPEN_TIMEOUT_MS);
    if (!r || !r.ok) {
      log('召出：页内 ⛔ 得召出（' + ((r && r.why) || 'timeout') + '）');
      summonHide('open-failed');
      return false;
    }
    if (SUM.tick) { clearInterval(SUM.tick); }
    SUM.tick = setInterval(summonPoll, 150);
    const ob = summonWin.getBounds();
    const cb = summonWin.getContentBounds();
    log('召出：' + why + ' ⇒ 热键→显 ' + (Date.now() - t0) + ' ms ／ 页内 ' + r.ms + ' ms ／ 外框 '
      + ob.width + 'x' + ob.height + ' ／ 内容 ' + cb.width + 'x' + cb.height + ' ／ 盒 ' + r.w + 'x' + r.h
      + ' ／ 焦点 ' + (r.active || '—'));
    return true;
  } catch (e) {
    log('召出：⛔ 得（' + ((e && e.message) || e) + '）');
    summonHide('error');
    return false;
  }
}

/* 收（Esc ／ 失焦 ／ 再按 ／ 页内自收 ／ 发 ／ 退出）：页内收（草稿留 5 分钟）＋ 窗隐（焦点自归前台）。 */
function summonHide(why) {
  if (!SUM.visible) { return; }
  SUM.visible = false;
  if (SUM.tick) { clearInterval(SUM.tick); SUM.tick = null; }
  const w = summonWin;
  if (w && !w.isDestroyed()) {
    try {
      const q = w.webContents.executeJavaScript(SUMMON_CLOSE_JS, false);
      if (q && q.catch) { q.catch(function (e) { log('召出：页内收 ⛔ 得（' + ((e && e.message) || e) + '）'); }); }
    } catch (e) { /* 页已亡 ⇒ 唯隐窗 */ }
    try { w.hide(); } catch (e) { log('召出：隐窗 ⛔ 得：' + ((e && e.message) || e)); }
  }
  log('召出：收（' + why + '）');
}

/* 页内自收之认领：Enter 发（⇒ 主窗出计划卡）／ 页内 Esc ⇒ #paSummon.hidden = true ⇒ 壳侧隐窗。 */
function summonPoll() {
  const w = summonWin;
  if (!SUM.visible || !w || w.isDestroyed()) { return; }
  let q = null;
  try { q = w.webContents.executeJavaScript(SUMMON_POLL_JS, false); }
  catch (e) { summonHide('poll-error'); return; }
  if (!q || !q.then) { return; }
  q.then(function (hidden) {
    if (hidden && SUM.visible) { summonHide('page'); }
  }).catch(function (e) {
    log('召出：态之读 ⛔ 得（' + ((e && e.message) || e) + '）⇒ 收');
    summonHide('poll-error');
  });
}

/* 热键 ／ 托盘之共入口（唯此一函 —— ⛔ 二处各写）。 */
function summonToggle(why) {
  const now = Date.now();
  if (now - SUM.lastToggleAt < 250) { return; }   // 键之双至：全局热键 ∧ 页内监听 ⇒ 唯取其一
  SUM.lastToggleAt = now;
  if (SUM.visible) { summonHide(why); return; }
  summonShow(why).catch(function (e) { log('召出 ⛔ 得：' + ((e && e.message) || e)); });
}

/* 「发」之桥（浮窗 ⇒ 主窗）：计划卡仍出一处（主窗之页之 paWinPlan）。
   ⚠ 唯纳 summonWin 之 IPC（⛔ 他窗冒充）；文字 ⛔ 入日志（只记字数）。 */
function summonPlanInMain(txt) {
  if (!win || win.isDestroyed()) {
    log('召出：主窗未立 ⇒ 文字未送（⛔ 假成）');
    return { ok: false, code: 'E_NOWIN' };
  }
  const js = '(function(){try{'
    + 'if(typeof window.paWinPlan==="function"){window.paWinPlan(' + JSON.stringify(txt) + ');return true;}'
    + 'if(typeof window.paWinSay==="function"){window.paWinSay("召出收到，但主窗 ⛔ 就绪 ⇒ ⛔ 计划卡");}'
    + 'return false;}catch(e){return false;}})()';
  try {
    if (win.isMinimized()) { win.restore(); }
    win.show();
    win.focus();
    win.webContents.executeJavaScript(js, false).then(function (ok) {
      if (!ok) { log('召出：主窗 ⛔ 得 paWinPlan ⇒ 文字未成卡'); }
    }).catch(function (e) { log('召出：主窗之送 ⛔ 得：' + ((e && e.message) || e)); });
    return { ok: true };
  } catch (e) {
    log('召出：主窗之送 ⛔ 得：' + ((e && e.message) || e));
    return { ok: false, code: 'E_SEND' };
  }
}
function summonDeliverFromOverlay(text) {
  const txt = String(text == null ? '' : text).trim();
  if (!txt) { return { ok: false, code: 'E_EMPTY' }; }
  log('召出：发（' + txt.length + ' 字）⇒ 主窗出计划卡');
  summonHide('send');
  if (!win || win.isDestroyed()) {
    log('召出：主窗未立 ⇒ 文字未送（⛔ 假成）');
    return { ok: false, code: 'E_NOWIN' };
  }
  if (!st.page_loaded) {
    SUM.pendingSend = txt;
    log('召出：主窗页未载毕 ⇒ 待载毕再送');
    return { ok: true, deferred: true };
  }
  return summonPlanInMain(txt);
}

function registerSummonHotkey() {
  let ok = false;
  try {
    ok = globalShortcut.register(SUMMON_ACC, function () { summonToggle('hotkey'); });
  } catch (e) {
    log('召出热键：注册异常 —— ' + ((e && e.message) || e));
  }
  SUM.hotkey = !!ok;
  if (ok) {
    log('召出热键已注册：' + SUMMON_ACC + ' ⇒ Summon（全局）');
  } else {
    log('⛔ 召出热键注册失败：' + SUMMON_ACC + ' ⇒ 以托盘菜单「召出」兜底（⛔ 静默失效）');
  }
  refreshSummonEntry();
  return !!ok;
}
function unregisterSummonHotkey() {
  try {
    globalShortcut.unregisterAll();
    log(SUM.hotkey ? '召出热键已注销（退出）' : '召出热键：未注成 ⇒ 退出无须注销');
  } catch (e) { log('召出热键注销 ⛔ 得：' + ((e && e.message) || e)); }
}

// ---------------------------------------------------------------- 托盘 ＋ 菜单
// ---------------------------------------------------------------- 托盘 ＋ 菜单
function trayIcon() {
  let img = nativeImage.createFromPath(path.join(__dirname, 'icon.png'));
  return img.isEmpty() ? nativeImage.createEmpty() : img;
}
function buildTray() {
  tray = new Tray(trayIcon());
  const fb = [
    { label: '打开留言板', click: function () { showMain(); reloadPage(); } },
    { label: '打开落点目录（留言收发处）', click: async function () {
        const r = await openFeedbackDir();
        log('openFeedbackDir ⇒ ' + JSON.stringify(r));
      } },
    { label: '打开日志目录', click: async function () { await shell.openPath(logsDir()); } }
  ];
  trayMenu = Menu.buildFromTemplate([
    { label: '显示', click: function () { showMain(); } },
    { label: '隐藏', click: function () { const w = liveWin(); if (w) { w.hide(); } } },
    // ⭐ 召出：热键之兜底（注册失败亦 ⛔ 静默失效 —— 承 59_PA_v1.1迭代单 §二 S1）
    { id: SUMMON_ENTRY_ID, label: summonEntryLabel(), click: function () { summonToggle('tray'); } },
    { type: 'separator' },
    { label: '启动服务', click: function () { startService(); } },
    { label: '停止服务', click: async function () { await stopService(); } },
    { label: '重启服务', click: async function () { await stopService(); await startService(); reloadPage(); } },
    { type: 'separator' },
    { label: '留言 / 反馈', submenu: fb },
    { type: 'separator' },
    { id: UPDATE_ENTRY_ID, label: UP.entryLabel(null), click: function () { onUpdateClick(); } },
    { id: SHELL_UPD_ID, label: '检查更新（壳层）', click: function () { onShellUpdateClick(); } },
    { type: 'separator' },
    { label: '退出', click: function () { isQuitting = true; saveWindowState(); app.quit(); } }
  ]);
  tray.setToolTip('ClawsJoy PA');
  tray.setContextMenu(trayMenu);
  tray.on('double-click', function () { showMain(); });
  log('托盘已立');
}
function buildAppMenu() {
  appMenu = Menu.buildFromTemplate([
    { label: 'ClawsJoy', submenu: [
      { id: UPDATE_ENTRY_ID, label: UP.entryLabel(null), click: function () { onUpdateClick(); } },
      { id: SHELL_UPD_ID, label: '检查更新（壳层）', click: function () { onShellUpdateClick(); } },
      { type: 'separator' },
      { label: '退出', click: function () { isQuitting = true; saveWindowState(); app.quit(); } } ] },
    { label: '视图', submenu: [ { role: 'reload' }, { role: 'toggleDevTools' }, { type: 'separator' },
      { role: 'resetZoom' }, { role: 'zoomIn' }, { role: 'zoomOut' }, { type: 'separator' },
      { role: 'togglefullscreen' } ] },
    { label: '留言 / 反馈', submenu: [
      { label: '打开留言板', click: function () { showMain(); reloadPage(); } },
      { label: '打开落点目录（留言收发处）', click: async function () { const r = await openFeedbackDir(); log('openFeedbackDir ⇒ ' + JSON.stringify(r)); } },
      { label: '打开日志目录', click: async function () { await shell.openPath(logsDir()); } } ] }
  ]);
  Menu.setApplicationMenu(appMenu);
}

// ---------------------------------------------------------------- 载荷层之更新（入口 · 一处定形）
/* 入口之律（pm_1684 §二）：
   * 其源唯 `GET /health.update`（**一处读** ⇒ ⛔ 自算 ／ ⛔ 出网自取清单）。
   * 其动唯调「载荷内之器」（`shell/update.js:updaterArgv` —— **一处定形** ／ ⛔ 二处各拼）。
   * ⛔ 于「非本壳之服」之上施增量（须先过 `identity.js` 之判 —— pm_1679 §四）。
   * 「凡等待 ⇒ 进度 ＋ 时长 ＋ 因 ＋ 去处」（pm_1617 §一.3）—— 进 ／ 时入菜单之题 ／ 日志；
     结果 ／ 因 ／ 去处入「人话」之窗。
*/
const UPDATE_ENTRY_ID = 'pa-update-entry';
let updState = { readable: false, available: false };
let updBusy = false;
let updT0 = 0;
let updTick = null;

function updateEntryLabel() {
  if (updBusy) { return '更新中…（' + Math.round((Date.now() - updT0) / 1000) + ' s）'; }
  return UP.entryLabel(updState);
}
function refreshUpdateMenu() {
  const menus = [trayMenu, appMenu];
  for (let i = 0; i < menus.length; i++) {
    if (!menus[i]) { continue; }
    const it = menus[i].getMenuItemById(UPDATE_ENTRY_ID);
    if (!it) { continue; }
    it.label = updateEntryLabel();
    it.enabled = !updBusy;
  }
}
async function readUpdateState() {
  try { updState = await UP.readState(PORT); }
  catch (e) { updState = { readable: false, available: false, why: 'read: ' + (e && e.message) }; }
  return updState;
}
function updateDest() { return shellLogFile(); }

async function showLines(title, lines) {
  const ls = lines || [];
  log('人话（' + title + '）：' + ls.join(' ｜ '));
  const opt = { type: 'info', title: 'ClawsJoy PA', message: title, detail: ls.join('\n'),
                buttons: ['好'], noLink: true };
  try {
    const _w = liveWin();
    if (_w) { await dialog.showMessageBox(_w, opt); } else { await dialog.showMessageBox(opt); }
  } catch (e) { log('弹窗 ⛔ 得（其因已入日志）：' + (e && e.message)); }
}

/* 入口之实（**唯此一函** —— 二处菜单共调 · ⛔ 二处各写） */
async function onUpdateClick() {
  if (updBusy) {
    await showLines('更新中', ['正在更新 ⇒ 请候其毕（进度 ／ 时长见于菜单之题 ∧ 日志）',
                              '去处：' + updateDest()]);
    return;
  }
  await readUpdateState();
  const st = updState;
  if (!st.readable) { await showLines('⛔ 更新', [UP.entryWhy(st, IDENTITY), '去处：' + updateDest()]); return; }
  if (!IDENTITY || !IDENTITY.ok) { await showLines('⛔ 更新', [UP.entryWhy(st, IDENTITY), '去处：' + updateDest()]); return; }
  if (!st.available) {
    await showLines('更新', ['已是最新（' + (st.current || '—') + '）⇒ ⛔ 须更新', '去处：' + updateDest()]);
    return;
  }
  updBusy = true; updT0 = Date.now();
  updTick = setInterval(refreshUpdateMenu, 1000);
  refreshUpdateMenu();
  log('更新：起 ｜ ' + UP.entryLabel(st) + ' ｜ root=' + rootDir());
  let run = null;
  try {
    run = await UP.updatePayload({ pyExe: pyExe(), root: rootDir(), port: PORT,
                                   state: st, identity: IDENTITY, onLine: log });
  } catch (e) {
    run = { phase: 'failed', ok: false, reason: '壳侧之跑 ⛔ 得：' + (e && e.message), why: '',
            elapsed_s: (Date.now() - updT0) / 1000 };
  }
  updBusy = false;
  if (updTick) { clearInterval(updTick); updTick = null; }
  log('更新：毕 ⇒ ' + run.phase + '（code=' + run.code + '）');
  await readUpdateState();
  refreshUpdateMenu();
  await showLines(run.ok ? '更新完成' : '更新 ⛔ 成', UP.statusLines(run, run.elapsed_s, updateDest()));
  if (run.ok) { reloadPage(); }
}

// ------------------------------------------------ 壳层之更新（electron-updater · 策唯在 shell_update.js）
/* 一处定形（承 pm_1885 §三 ／ pm_1886 §一 ／ pm_1890 §一 ／ pm_1896 §三）：
 *   * **策**（态机 ／ 人话 ／ 门）唯在 `shell_update.js`（**纯** ⇒ 可单测）；本档唯**注入** electron-updater ＋ 接 IPC。
 *   * **A 式**：有新版 ⇒ 下载（可显进度）；下载毕 ⇒ 唯**人点**（面之钮 ∨ 本菜单）方装 ⇒ ⛔ 偷重启。
 *   * 「推」唯唤面**再拉**（⛔ 传态 —— 免得「拉与推不一」而用户见二真相 · pm_1890 §一.2）。
 *   * ⛔ 动 `app-update.yml` 之四栏（pm_1889 §一：不签名之正解在「本来未声明校验」）。
 */
const SHELL_UPD_ID = 'pa-shell-update-entry';
let ShellUpd = null;

function shellUpdater() {
  if (ShellUpd) { return ShellUpd; }
  let up = null;
  if (PACKAGED) {
    try { up = require('electron-updater').autoUpdater; }
    catch (e) { log('壳层之更新：⛔ 见 electron-updater（' + ((e && e.message) || e) + '）⇒ 态 ＝ unsupported'); }
  } else {
    log('壳层之更新：开发态（⛔ 打包）⇒ 态 ＝ unsupported（⛔ 真跑更新器 —— 免误触）');
  }
  ShellUpd = SU.createController({
    updater: up, current: app.getVersion(), packaged: PACKAGED, log: log,
    notify: function () {
      try { if (win && !win.isDestroyed()) { win.webContents.send('pa:shell-update-ping'); } }
      catch (e) { /* 推之侧之错 ⛔ 阻壳 */ }
      refreshShellUpdateMenu();
    }
  });
  log('壳层之更新之策已立：态 ＝ ' + ShellUpd.state().phase);
  return ShellUpd;
}

function shellUpdateLabel() {
  const st = shellUpdater().state();
  if (st.phase === 'downloaded') { return '重启并安装新版（壳 ' + (st.latest || '') + '）'; }
  if (st.phase === 'available' || st.phase === 'downloading') { return '壳层：下载新版中…'; }
  if (st.phase === 'checking') { return '壳层：查新版中…'; }
  if (st.phase === 'installing') { return '壳层：正在安装（本程序将重启）…'; }
  if (st.phase === 'unsupported') { return '检查更新（壳层）· 本壳 ⛔ 带更新器'; }
  if (st.phase === 'failed') { return '检查更新（壳层）· 上次 ⛔ 成'; }
  return '检查更新（壳层）';
}

function refreshShellUpdateMenu() {
  const st = shellUpdater().state();
  const menus = [trayMenu, appMenu];
  for (let i = 0; i < menus.length; i++) {
    if (!menus[i]) { continue; }
    const it = menus[i].getMenuItemById(SHELL_UPD_ID);
    if (!it) { continue; }
    it.label = shellUpdateLabel();
    it.enabled = (st.phase === 'downloaded') || (st.phase === 'idle') || (st.phase === 'failed');
  }
}

/* 菜单之点：已下毕 ⇒ 装（**唯人点** · 明书在其题）；余 ⇒ 查。 */
async function onShellUpdateClick() {
  const st = shellUpdater().state();
  if (st.phase === 'downloaded') {
    log('壳层之装：人点 ⇒ quitAndInstall（将重启）');
    log('壳层之装 ⇒ ' + JSON.stringify(shellUpdater().install()));
    return;
  }
  log('壳层之查 ⇒ ' + JSON.stringify(shellUpdater().check()));
}

// ---------------------------------------------------------------- 自测（⛔ 入产品之面）
/* 自测之桩（唯自测 · ⛔ 入产品之路）：扮一「他之 PA」应答 `/health`。 */
function startStub(opt) {
  return new Promise(function (resolve) {
    const o = opt || {};
    const doc = o.omitBuild
      ? { status: 'healthy', version: '9.0.0' }
      : { status: 'healthy', version: '9.0.0',
          build: { available: true, path: 'D:\\OTHER\\ClawsJoyPA\\version.json', version: '9.0.0' },
          update: o.update || { available: false, current_version: '9.0.0', latest_version: null, size_bytes: 0, files: 0 } };
    const body = JSON.stringify(doc);
    const srv = http.createServer(function (req, res) {
      if (req.url && req.url.indexOf('/health') === 0) {
        res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(body);
      } else { res.writeHead(404); res.end('no'); }
    });
    srv.listen(0, '127.0.0.1', function () { resolve({ server: srv, port: srv.address().port }); });
  });
}
function stopStub(s) { try { if (s && s.server) { s.server.close(); } } catch (e) { } }

async function selfTest() {
  const r = { root: rootDir(), py: pyExe(), root_ok: fs.existsSync(rootDir()), py_ok: fs.existsSync(pyExe()) };
  // ⭐ 护栏（我一手之训）：自测**必**指明 ROOT ⇒ ⛔ 落到开发之「实载荷」上（否则会起停 ／ 改他根之实例）
  if (!PACKAGED && !process.env.CLAWSJOY_ROOT) {
    r.guard = '⛔ 自测须给 CLAWSJOY_ROOT（未打包时）—— 本进程退出（⛔ 触他根）';
    log(r.guard);
    console.log('SHELL_RESULT ' + JSON.stringify(r));
    isQuitting = true; app.quit();
    return r;
  }
  r.port = await readPort();
  log('自测：port=' + r.port + (PORT_WHY ? (' ／ ' + PORT_WHY) : ''));
  r.feedback_dir_shell = feedbackDir();
  const pr = await runPy(['-c', 'import sys;sys.path.insert(0, r"' + rootDir() + '");' +
    'from core.lib.feedback_target import feedback_dir as f;print(f(r"' + rootDir() + '"))'], 300000);
  const pl = (pr.out || '').trim().split('\n').filter(function (x) { return x.trim(); });
  r.feedback_dir_backend = pl.length ? pl[pl.length - 1].trim() : null;
  r.feedback_dir_agrees = (r.feedback_dir_shell === r.feedback_dir_backend);
  r.first_run = await firstRunCheck();
  r.payload_version = payloadVersionByRead();
  r.version_agrees = (r.first_run.version === r.payload_version);
  const h0 = await probeHealth();
  r.health_before = h0.status;
  r.start = await startService();
  // ⭐ §四 之齿（正控 ＋ 反控二 · pm_1679 §四.2）：本载荷 ⇒ 载页；他之载荷 ⇒ 人话 ＋ 去处。
  r.identity = await serviceIdentity();
  r.identity_positive = !!(r.identity && r.identity.ok);
  r.dec_positive = ID.decidePage(r.identity).load;
  r.feedback_dir_shell_after = feedbackDir();
  r.feedback_dir_from_health = BACKEND_DIRS.feedback;
  const _sa = await startStub({ omitBuild: false });
  r.identity_foreign = await serviceIdentity(_sa.port);
  r.identity_foreign_caught = !!(r.identity_foreign && !r.identity_foreign.ok
    && r.identity_foreign.why === 'foreign-root');
  const _df = ID.decidePage(r.identity_foreign);
  r.dec_foreign = _df.load;
  r.dec_foreign_msg_ok = (_df.load === 'msg')
    && ((_df.msg || []).join(' ').indexOf('本机已有一个 PA 在跑') >= 0)
    && ((_df.msg || []).join(' ').indexOf('shell.log') >= 0);
  const _sb = await startStub({ omitBuild: true });
  r.identity_nobuild = await serviceIdentity(_sb.port);
  r.identity_nobuild_caught = !!(r.identity_nobuild && !r.identity_nobuild.ok);
  stopStub(_sa); stopStub(_sb);
  // ⭐ pm_1684 §二.2 之齿（载荷层之更新）：调器之形 ／ 门之正反控 ／ 人话 ／ 真 HTTP 桩 ／ 败之路
  r.update_argv = UP.updaterArgv({ pyExe: pyExe(), root: rootDir() });
  r.update_argv_ok = (r.update_argv.args.length === 8)
    && (r.update_argv.args[3] === UP.scriptPath(rootDir()))
    && (r.update_argv.args[4] === '--root') && (r.update_argv.args[5] === rootDir())
    && (r.update_argv.args[6] === '--json') && (r.update_argv.args[7] === '--go')
    && (r.update_argv.cwd === rootDir()) && (r.update_argv.exe === pyExe());
  const _av = UP.stateFromHealth({ update: { available: true, latest_version: '9.0.3', size_bytes: 72091 } });
  r.upd_avail_label = UP.entryLabel(_av);
  r.upd_avail_on = UP.entryEnabled(_av, { ok: true });
  r.upd_avail_blocked_by_identity = !UP.entryEnabled(_av, { ok: false });
  const _la = UP.stateFromHealth({ update: { available: false, current_version: '9.0.2', note: '已是最新' } });
  r.upd_latest_label = UP.entryLabel(_la);
  r.upd_latest_off = !UP.entryEnabled(_la, { ok: true });
  r.upd_nokey_off = !UP.entryEnabled(UP.stateFromHealth({ status: 'healthy' }), { ok: true });
  const _fr = UP.parseRun(2, '[FAIL] 逐件校 ⛔ 合 ⇒ 整体 ⛔ 落\n[FAIL] **已回滚至 `9.0.1`**（fail-loud）');
  r.upd_fail_phase = _fr.phase;
  r.upd_fail_rb = _fr.rolled_back_to;
  r.upd_fail_lines = UP.statusLines(_fr, 3.2, null);
  const _fmsg = r.upd_fail_lines.join(' ');
  r.upd_fail_msg_ok = (_fmsg.indexOf('已回滚至 9.0.1') >= 0) && (_fmsg.indexOf('去处：') >= 0);
  const _s1 = await startStub({ update: { available: true, latest_version: '9.0.3', size_bytes: 72091 } });
  const _s2 = await startStub({ update: { available: false, current_version: '9.0.2' } });
  const _r1 = await UP.readState(_s1.port);
  const _r2 = await UP.readState(_s2.port);
  stopStub(_s1); stopStub(_s2);
  r.upd_http_avail_on = UP.entryEnabled(_r1, { ok: true });
  r.upd_http_latest_off = !UP.entryEnabled(_r2, { ok: true });
  r.upd_http_latest_label = UP.entryLabel(_r2);
  const _bad = await UP.runUpdate({ pyExe: path.join(rootDir(), 'runtime', 'no-such-python.exe'),
                                    root: rootDir(), timeoutMs: 60000 });
  r.upd_badrun_phase = _bad.phase;
  r.upd_badrun_lines = UP.statusLines(_bad, _bad.elapsed_s, null);
  r.update_state = await UP.readState(r.port);
  r.update_readable = !!(r.update_state && r.update_state.readable);
  const _dec = ID.decidePage(r.identity);
  if (r.port) { createWindow(_dec.load === 'msg' ? _dec.msg : null); }
  await sleep(2500);
  r.page_loaded = st.page_loaded;
  r.url = st.url;
  r.load_error = st.load_error;
  r.open_dir = await Promise.race([openFeedbackDir(), sleep(10000).then(function () {
    return { ok: false, code: 'E_TIMEOUT', message: 'openPath 未在 10 s 内回（**自测之限** · ⛔ 悬）' };
  })]);
  r.stop = await stopService();
  const h1 = await probeHealth();
  r.health_after_stop = h1.status;
  r.restart = await startService();
  if (liveWin()) { saveWindowState(); }
  r.window_state_file = windowStateFile();
  r.window_state_ok = fs.existsSync(windowStateFile());
  // ⭐ pm_1896 §三 之齿（壳层之更新 · 一处定形）：返之形 ＋ unsupported 之判 ＋ 装之门（⛔ 谎报）
  const _su = shellUpdater().state();
  r.shellupd_phase = _su.phase;
  r.shellupd_shape_ok = (typeof _su.ok === 'boolean') && (SU.PHASES.indexOf(_su.phase) >= 0)
    && ('current' in _su) && ('latest' in _su) && ('progress' in _su)
    && (_su.ok ? true : (SU.CODES.indexOf(_su.code) >= 0 && typeof _su.message === 'string'));
  r.shellupd_unsupported = (!PACKAGED) ? (_su.phase === 'unsupported') : true;
  r.shellupd_install_refused = (shellUpdater().install().phase === _su.phase);

  console.log('SHELL_RESULT ' + JSON.stringify(r));
  isQuitting = true;
  app.quit();
  return r;
}

// ---------------------------------------------------------------- 启
/* IPC sender 验证（一处定形）：只认本壳页面（http://127.0.0.1:<PORT>）与
   壳内 summon/record 两个本地页；浏览器视图里的远端页没有 preload ⇒ 无桥。
   ⛔ 不以「有调用」当可信：无 preload 的远程页也必被此闸拦。 */
function ipcSenderUrl(event) {
  try { if (event && event.senderFrame && event.senderFrame.url) { return String(event.senderFrame.url); } } catch (e) { /* 照退 */ }
  try { return String((event && event.sender && event.sender.getURL()) || ''); } catch (e) { return ''; }
}
function ipcSenderTrusted(event) {
  const u = ipcSenderUrl(event);
  if (!u) { return false; }
  if (PORT && u.indexOf('http://127.0.0.1:' + PORT + '/') === 0) { return true; }
  if (u.indexOf('file://') === 0 && /(?:summon|record)\.html(?:[?#]|$)/.test(u)) { return true; }
  return false;
}
const _ipcHandle = ipcMain.handle.bind(ipcMain);
ipcMain.handle = function (channel, fn) {
  return _ipcHandle(channel, function (event) {
    const args = Array.prototype.slice.call(arguments, 1);
    if (!ipcSenderTrusted(event)) {
      log('IPC ⛔ 拒：' + channel + ' ｜ sender=' + ipcSenderUrl(event).slice(0, 160));
      return { ok: false, code: 'E_SENDER', error: 'untrusted ipc sender' };
    }
    return fn.apply(this, [event].concat(args));
  });
};

ipcMain.handle('pa:open-feedback-dir', function () { return openFeedbackDir(); });
// 召出之「发」：唯纳 summonWin 之 IPC（⛔ 他窗冒充）⇒ 交主窗出计划卡（一处）
ipcMain.handle('pa:summon-send', function (event, text) {
  try {
    if (!summonWin || summonWin.isDestroyed() || event.sender !== summonWin.webContents) {
      log('召出：⛔ 采 IPC pa:summon-send（sender 非浮窗）');
      return { ok: false, code: 'E_SENDER' };
    }
  } catch (e) { return { ok: false, code: 'E_SENDER' }; }
  return summonDeliverFromOverlay(text);
});
ipcMain.handle('pa:summon-command', async function (event, cmd) {
  try {
    if (!summonWin || summonWin.isDestroyed() || event.sender !== summonWin.webContents) {
      return { ok: false, code: 'E_SENDER' };
    }
  } catch (e) { return { ok: false, code: 'E_SENDER' }; }
  const c = String(cmd || '');
  showMain();
  const w = liveWin();
  if (!w) { return { ok: false, code: 'E_NO_WINDOW' }; }
  try { w.show(); w.focus(); } catch (e) { }
  const js = c === 'screen'
    ? "try{paWinGo('brain');setTimeout(function(){if(window.paScreenPick)paScreenPick();},260);}catch(e){}"
    : "try{paWinGo('brain');setTimeout(function(){if(window.paBrainVoiceToggle)paBrainVoiceToggle();},260);}catch(e){}";
  try { await w.webContents.executeJavaScript(js, true); }
  catch (e) { log('召出：⛔ 采 summon-command：' + ((e && e.message) || e)); return { ok: false, code: 'E_EXEC' }; }
  setTimeout(function () { try { summonHide(); } catch (e) { } }, 80);
  return { ok: true, cmd: c };
});
ipcMain.handle('pa:rec-show', function () { showRecControl(); return { ok: true }; });
ipcMain.handle('pa:rec-hide', function () { hideRecControl(); return { ok: true }; });
ipcMain.handle('pa:rec-stop', function (event) {
  try {
    if (!recWin || recWin.isDestroyed() || event.sender !== recWin.webContents) {
      return { ok: false, code: 'E_SENDER' };
    }
  } catch (e) { return { ok: false, code: 'E_SENDER' }; }
  hideRecControl();
  const w = liveWin();
  if (w) { try { w.webContents.executeJavaScript("try{if(window.paScreenStop)paScreenStop();}catch(e){}", true); } catch (e) { } }
  return { ok: true };
});
ipcMain.handle('pa:rec-mic', async function (event) {
  try {
    if (!recWin || recWin.isDestroyed() || event.sender !== recWin.webContents) {
      return { ok: false, code: 'E_SENDER' };
    }
  } catch (e) { return { ok: false, code: 'E_SENDER' }; }
  const w = liveWin();
  if (!w) { return { ok: false, code: 'E_NO_WINDOW' }; }
  try {
    const en = await w.webContents.executeJavaScript("window.paScreenToggleMic?paScreenToggleMic():null", true);
    return { ok: true, enabled: en === true };
  } catch (e) { return { ok: false, code: 'E_EXEC' }; }
});
ipcMain.handle('pa:shell-update-state', function () { return shellUpdater().state(); });
ipcMain.handle('pa:shell-update-install', function () { return shellUpdater().install(); });


// ------------------------------------------------ 屏幕录播来源（P0）
ipcMain.handle('pa:screen-select', function (_e, opt) {
  var o = opt || {};
  screenPick = { id: String(o.id || ''), audio: o.audio === true };
  return { ok: true, id: screenPick.id, audio: screenPick.audio };
});
ipcMain.handle('pa:pick-directory', async function () {
  try {
    const w = liveWin();
    const opt = { title: '选择 Markdown 目录', properties: ['openDirectory'] };
    const r = w ? await dialog.showOpenDialog(w, opt) : await dialog.showOpenDialog(opt);
    if (!r || r.canceled || !r.filePaths || !r.filePaths.length) { return { ok: false, canceled: true }; }
    return { ok: true, path: r.filePaths[0] };
  } catch (e) { return { ok: false, error: String((e && e.message) || e) }; }
});
ipcMain.handle('pa:open-path', async function (_e, raw) {
  try {
    var base = path.resolve(process.env.LOCALAPPDATA || '', 'ClawsJoyPA');
    var p = path.resolve(String(raw || ''));
    if (!p || (p !== base && !p.startsWith(base + path.sep))) {
      return { ok: false, error: '只允许打开 PA 本机数据目录内的文件' };
    }
    var ext = path.extname(p).toLowerCase();
    if (['.webm', '.mp4', '.mkv', '.mov', '.wav', '.mp3', '.m4a', '.ogg', '.opus', '.jpg', '.jpeg', '.png', '.pdf'].indexOf(ext) < 0) {
      return { ok: false, error: '不支持打开该类型' };
    }
    if (!fs.existsSync(p)) { return { ok: false, error: '文件不存在' }; }
    var err = await shell.openPath(p);
    return err ? { ok: false, error: String(err) } : { ok: true };
  } catch (e) { return { ok: false, error: String((e && e.message) || e) }; }
});
ipcMain.handle('pa:screen-sources', async function () {
  try {
    const srcs = await desktopCapturer.getSources({
      types: ['screen', 'window'],
      thumbnailSize: { width: 320, height: 180 },
      fetchWindowIcons: true
    });
    return { ok: true, sources: (srcs || []).map(function (s) {
      var thumb = '';
      try { thumb = s.thumbnail && !s.thumbnail.isEmpty() ? s.thumbnail.toDataURL() : ''; } catch (e) { }
      return { id: s.id, name: s.name || '(未命名)', thumbnail: thumb,
               appIcon: (s.appIcon && !s.appIcon.isEmpty()) ? '1' : '' };
    }) };
  } catch (e) {
    return { ok: false, error: String((e && e.message) || e) };
  }
});

// ------------------------------------------------ 内置浏览器 P0（IPC）
ipcMain.handle('pa:browser-show', async function (_e, opt) {
  const o = opt || {};
  const v = ensureBrowserView();
  if (!v) { return { ok: false, error: '浏览器未立' }; }
  try {
    browserLastBounds = browserBounds(o.bounds);
    v.setBounds(browserLastBounds);
    v.setVisible(true);
    var url = String(o.url || '').trim();
    if (url && /^https?:\/\//i.test(url)) {
      if (v.webContents.getURL() !== url) { await v.webContents.loadURL(url); }
    }
    return { ok: true, url: v.webContents.getURL(), title: v.webContents.getTitle() };
  } catch (e) {
    return { ok: false, error: String((e && e.message) || e) };
  }
});
ipcMain.handle('pa:browser-hide', function () { browserHide(); return { ok: true }; });
ipcMain.handle('pa:browser-close', function () { browserCloseView(); return { ok: true }; });
ipcMain.handle('pa:browser-fullscreen', async function (_e, on) {
  var v = ensureBrowserView();
  if (v) {
    try {
      var r = await v.webContents.executeJavaScript("(async()=>{var v=document.querySelector('video'); if(!v) return {ok:false,why:'no-video'}; try { if(document.fullscreenElement){ await document.exitFullscreen(); return {ok:true,exited:true}; } await v.requestFullscreen(); return {ok:true,entered:true}; } catch(e){ return {ok:false,error:String(e&&e.message||e)}; } })()", true);
      if (r && r.ok) { return { ok: true, video: true, fullscreen: !r.exited, exited: !!r.exited }; }
    } catch (e) { }
  }
  var want = (on === true || on === false) ? on : !browserHtmlFull;
  var ok = setBrowserFull(want);
  return { ok: ok, video: false, fullscreen: browserHtmlFull };
});
ipcMain.handle('pa:browser-asr-start', async function () {
  var v = ensureBrowserView();
  if (!v) { return { ok: false, error: '浏览器未立' }; }
  var js = "(() => {\n" +
    "  if (window.__paAsr) { return {ok:false, error:'已在录音'}; }\n" +
    "  const v = document.querySelector('video'); if (!v) { return {ok:false, error:'当前页没有视频'}; }\n" +
    "  try { v.play(); } catch(e) { }\n" +
    "  let st = null, ac = null;\n" +
    "  try {\n" +
    "    const AC = window.AudioContext || window.webkitAudioContext;\n" +
    "    ac = new AC();\n" +
    "    const src = ac.createMediaElementSource(v);\n" +
    "    const dest = ac.createMediaStreamDestination();\n" +
    "    src.connect(dest); src.connect(ac.destination);\n" +
    "    try { ac.resume(); } catch(e) {}\n" +
    "    st = dest.stream;\n" +
    "  } catch(e) {\n" +
    "    try { st = v.captureStream ? v.captureStream() : (v.mozCaptureStream ? v.mozCaptureStream() : null); } catch(e2) {}\n" +
    "  }\n" +
    "  if (!st) { return {ok:false, error:'当前视频不支持音轨捕获'}; }\n" +
    "  const at = st.getAudioTracks(); if (!at.length) { return {ok:false, error:'当前视频没有音轨'}; }\n" +
    "  const as = new MediaStream(at);\n" +
    "  const rec = new MediaRecorder(as, {mimeType:'audio/webm'});\n" +
    "  const chunks = [];\n" +
    "  rec.ondataavailable = function(e){ if(e.data && e.data.size) chunks.push(e.data); };\n" +
    "  rec.start(1000);\n" +
    "  window.__paAsr = {rec:rec, stream:st, chunks:chunks, ac:ac};\n" +
    "  return {ok:true, tracks:at.length, at: Number(v.currentTime || 0), duration: Number(v.duration || 0), paused: !!v.paused, muted: !!v.muted, ended: !!v.ended};\n" +
    "})()";
  try { return await v.webContents.executeJavaScript(js, true); }
  catch (e) { return { ok: false, error: String((e && e.message) || e) }; }
});
ipcMain.handle('pa:browser-asr-stop', async function () {
  var v = ensureBrowserView();
  if (!v) { return { ok: false, error: '浏览器未立' }; }
  var js = "new Promise(function(resolve){\n" +
    "  const a = window.__paAsr; if (!a) { resolve({ok:false,error:'未在录音'}); return; }\n" +
    "  a.rec.onstop = function(){\n" +
    "    try {\n" +
    "      const blob = new Blob(a.chunks, {type: a.rec.mimeType || 'audio/webm'});\n" +
    "      const fr = new FileReader();\n" +
    "      fr.onload = function(){ try{ a.stream.getTracks().forEach(function(t){ t.stop(); }); if(a.ac){ a.ac.close(); } }catch(e){} window.__paAsr = null; resolve({ok:true, data:fr.result, size:blob.size}); };\n" +
    "      fr.readAsDataURL(blob);\n" +
    "    } catch(e) { window.__paAsr = null; resolve({ok:false,error:String(e&&e.message||e)}); }\n" +
    "  };\n" +
    "  try { a.rec.stop(); } catch(e) { window.__paAsr=null; resolve({ok:false,error:String(e&&e.message||e)}); }\n" +
    "})";
  try {
    var r = await v.webContents.executeJavaScript(js, true);
    if (!r || !r.ok) { return r || { ok: false, error: '录音结束失败' }; }
    var b64 = String(r.data || '');
    var comma = b64.indexOf(',');
    if (comma >= 0) { b64 = b64.slice(comma + 1); }
    var buf = Buffer.from(b64, 'base64');
    var fd = new FormData();
    fd.append('file', new Blob([buf], { type: 'audio/webm' }), 'browser-caption.webm');
    var port = process.env.PA_PORT || '5102';
    var resp = await fetch('http://127.0.0.1:' + port + '/v9/pa/notes/transcribe', { method: 'POST', body: fd });
    var data = await resp.json();
    if (!data || !data.ok || !data.transcript) { return { ok: false, error: (data && (data.error || data.message)) || '转写失败' }; }
    return { ok: true, transcript: data.transcript };
  } catch (e) { return { ok: false, error: String((e && e.message) || e) }; }
});
ipcMain.handle('pa:browser-asr-poll', async function () {
  var v = ensureBrowserView();
  if (!v) { return { ok: false, error: '浏览器未立' }; }
  var js = "new Promise(function(resolve){\n" +
    "  const a = window.__paAsr; if (!a) { resolve({ok:false,error:'未在录音'}); return; }\n" +
    "  try {\n" +
    "    const blob = new Blob(a.chunks, {type: a.rec.mimeType || 'audio/webm'});\n" +
    "    if (!blob.size) { var vv0=document.querySelector('video'); resolve({ok:true,data:'',size:0,state:vv0?{currentTime:Number(vv0.currentTime||0),duration:Number(vv0.duration||0),paused:!!vv0.paused,ended:!!vv0.ended,muted:!!vv0.muted}:null}); return; }\n" +
    "    const fr = new FileReader();\n" +
    "    fr.onload = function(){ var vv=document.querySelector('video'); resolve({ok:true, data:fr.result, size:blob.size, state:vv?{currentTime:Number(vv.currentTime||0),duration:Number(vv.duration||0),paused:!!vv.paused,ended:!!vv.ended,muted:!!vv.muted}:null}); };\n" +
    "    fr.readAsDataURL(blob);\n" +
    "  } catch(e) { resolve({ok:false,error:String(e&&e.message||e)}); }\n" +
    "})";
  try {
    var r = await v.webContents.executeJavaScript(js, true);
    if (!r || !r.ok) { return r || { ok: false, error: '取音轨失败' }; }
    if (!r.data) { return { ok: true, size: 0, state: r.state || null }; }
    var b64 = String(r.data || '');
    var comma = b64.indexOf(','); if (comma >= 0) { b64 = b64.slice(comma + 1); }
    var buf = Buffer.from(b64, 'base64');
    var fd = new FormData();
    fd.append('file', new Blob([buf], { type: 'audio/webm' }), 'browser-live.webm');
    var port = process.env.PA_PORT || '5102';
    var resp = await fetch('http://127.0.0.1:' + port + '/v9/pa/notes/transcribe', { method: 'POST', body: fd });
    var data = await resp.json();
    if (!data || !data.ok || !data.transcript) { return { ok: false, error: (data && (data.error || data.message)) || '转写失败' }; }
    return { ok: true, transcript: data.transcript, size: r.size, state: r.state || null };
  } catch (e) { return { ok: false, error: String((e && e.message) || e) }; }
});
ipcMain.handle('pa:browser-go', async function (_e, url) {
  const v = ensureBrowserView();
  if (!v) { return { ok: false, error: '浏览器未立' }; }
  const u = String(url || '').trim();
  if (!/^https?:\/\//i.test(u)) { return { ok: false, error: '只允许 http/https' }; }
  try { await v.webContents.loadURL(u); return { ok: true }; }
  catch (e) { return { ok: false, error: String((e && e.message) || e) }; }
});
ipcMain.handle('pa:browser-read', async function () { try { return await browserRead(); } catch (e) { return { ok: false, error: String((e && e.message) || e) }; } });
ipcMain.handle('pa:browser-back', function () { const v = ensureBrowserView(); if (v && v.webContents.canGoBack()) { v.webContents.goBack(); } return { ok: true }; });
ipcMain.handle('pa:browser-forward', function () { const v = ensureBrowserView(); if (v && v.webContents.canGoForward()) { v.webContents.goForward(); } return { ok: true }; });
ipcMain.handle('pa:browser-reload', function () { const v = ensureBrowserView(); if (v) { v.webContents.reload(); } return { ok: true }; });
ipcMain.handle('pa:browser-state', function () {
  const v = ensureBrowserView();
  if (!v) { return { ok: false }; }
  return { ok: true, url: v.webContents.getURL(), title: v.webContents.getTitle(), loading: v.webContents.isLoading() };
});


const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  log('已有实例在 ⇒ 本进程退出（单实例）');
  app.quit();
} else {
  app.setAppUserModelId(APP_ID);
  app.on('second-instance', function () {
    if (SUM.visible) { summonHide('second-instance'); }
    showMain();
  });
  app.on('window-all-closed', function () { if (SELFTEST) { app.quit(); } });
  app.on('before-quit', function () {
    isQuitting = true;
    if (SUM.visible) { summonHide('quit'); }
    try { if (summonWin && !summonWin.isDestroyed()) { summonWin.destroy(); } } catch (e) { /* 照退（⛔ 阻壳） */ }
    saveWindowState();
  });
  app.on('will-quit', function () { unregisterSummonHotkey(); });   // ⭐ 退出必注销（⛔ 留热键于系统）
  app.whenReady().then(async function () {
    log('app ready ｜ packaged=' + PACKAGED + ' ｜ ROOT=' + rootDir());
    if (SELFTEST) { await selfTest(); return; }
    registerSummonHotkey();   // ⭐ 早注（浮窗未就绪时按 ⇒ 记日志并待就绪再召）· 失败 ⇒ 托盘「召出」兜底
    createSummonWindow();     // ⭐ 浮窗早立于启动（页为本地小件 · 无网无服）⇒ 先按亦近热
    await readPort();
    await firstRunCheck();
    await startService();
    IDENTITY = await serviceIdentity();
    log('身份之核：' + JSON.stringify(IDENTITY));
    await readUpdateState();
    refreshUpdateMenu();
    try { shellUpdater().check(); } catch (e) { log('壳层之查 ⛔ 得：' + (e && e.message)); }
    setInterval(function () { readUpdateState().then(refreshUpdateMenu); }, 60000);
    const _dec = ID.decidePage(IDENTITY);
    if (_dec.load === 'msg') { log('⛔ 载载荷之页（他之 PA 应答）⇒ 以「人话 ＋ 去处」代之'); }
    createWindow(_dec.load === 'msg' ? _dec.msg : null);
    try { buildTray(); } catch (e) { log('托盘 ⛔ 得：' + (e && e.message)); }
    buildAppMenu();
    refreshShellUpdateMenu();
    await reportInstallTasksOnce();
  });
}