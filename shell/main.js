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
const { app, BrowserWindow, Tray, Menu, shell, dialog, ipcMain, nativeImage } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');

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
function feedbackDir() {
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
  // ⭐ **径之形唯后端一处出**：逐字复现 `os.path.join(root, dir)`（＝ `root` ＋ 分隔符 ＋ `dir` 之原字）
  //   ⇒ ⛔ 用 `path.join`（它会归一 ／ 转 `\`）—— 否则面之「开后端之径否」之校必假红
  //   （页：`p !== dir` ⇒ ⚠）。⚠ 后端之默认 `data/pa/feedback` 含正斜杠 ⇒ 我一手逮之「混分隔符」
  //   亦现于用户面（`去处：自行打开 …\data/pa/feedback`）—— 其修须动 `core/**`（载荷之件 ⇒ 升版号 · 候 PM 裁）。
  const abs = /^[A-Za-z]:[\\/]/.test(d) || d.indexOf('\\\\') === 0 || d.charAt(0) === '/';
  return abs ? d : (rootDir() + path.sep + d);
}

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
function paUrl() { return PORT ? ('http://127.0.0.1:' + PORT + '/web/pa.html') : ''; }

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

// 器之核（**唯自测用之** —— 产品之径 ⛔ 重解版号：⛔ 二处各写）
function payloadVersionByRead() {
  try {
    const t = fs.readFileSync(versionPy(), 'utf8');
    const m = t.match(/^__version__\s*=\s*u?["']([^"']+)["']/m);
    return m ? m[1] : null;
  } catch (e) { return null; }
}

// ---------------------------------------------------------------- 探活 ／ 起停
function probeHealth() {
  return new Promise(function (resolve) {
    if (!PORT) { resolve({ ok: false, status: 0, body: 'no-port' }); return; }
    const req = http.get({ host: '127.0.0.1', port: PORT, path: '/health', timeout: 2500 }, function (res) {
      let b = '';
      res.on('data', function (d) { b += d; });
      res.on('end', function () { resolve({ ok: res.statusCode === 200, status: res.statusCode, body: b }); });
    });
    req.on('error', function (e) { resolve({ ok: false, status: 0, body: String(e && e.message) }); });
    req.on('timeout', function () { req.destroy(); resolve({ ok: false, status: 0, body: 'timeout' }); });
  });
}
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
function saveWindowState() {
  if (!win) { return; }
  try {
    const b = win.getNormalBounds();
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
let win = null;
let tray = null;
let isQuitting = false;
const st = { window: false, page_loaded: false, url: null, title: null, load_error: null };

function createWindow() {
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
  });
  win.webContents.on('did-fail-load', function (_e, code, desc, url) {
    st.load_error = code + ' ' + desc + ' ' + url;
    log('页载败：' + st.load_error);
  });
  win.on('close', function () { saveWindowState(); if (!isQuitting && !SELFTEST) { win.hide(); return false; } });
  if (PORT) { win.loadURL(paUrl()); } else { win.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(
    '<h2>ClawsJoy PA</h2><p>⛔ 得端口：' + PORT_WHY + '</p><p>因 ＋ 去处：见 %LOCALAPPDATA%\\ClawsJoyPA\\shell\\shell.log</p>')); }
  log('窗已立（' + s.width + 'x' + s.height + '）');
}

function reloadPage() { if (win && PORT) { win.loadURL(paUrl()); } }

// ---------------------------------------------------------------- 托盘 ＋ 菜单
function trayIcon() {
  let img = nativeImage.createFromPath(path.join(__dirname, 'icon.png'));
  return img.isEmpty() ? nativeImage.createEmpty() : img;
}
function buildTray() {
  tray = new Tray(trayIcon());
  const fb = [
    { label: '打开留言板', click: function () { if (!win) { createWindow(); } else { win.show(); } reloadPage(); } },
    { label: '打开落点目录（留言收发处）', click: async function () {
        const r = await openFeedbackDir();
        log('openFeedbackDir ⇒ ' + JSON.stringify(r));
      } },
    { label: '打开日志目录', click: async function () { await shell.openPath(logsDir()); } }
  ];
  const menu = Menu.buildFromTemplate([
    { label: '显示', click: function () { if (win) { win.show(); } } },
    { label: '隐藏', click: function () { if (win) { win.hide(); } } },
    { type: 'separator' },
    { label: '启动服务', click: function () { startService(); } },
    { label: '停止服务', click: async function () { await stopService(); } },
    { label: '重启服务', click: async function () { await stopService(); await startService(); reloadPage(); } },
    { type: 'separator' },
    { label: '留言 / 反馈', submenu: fb },
    { type: 'separator' },
    { label: '检查更新（壳层）', click: function () { checkShellUpdate(); } },
    { type: 'separator' },
    { label: '退出', click: function () { isQuitting = true; saveWindowState(); app.quit(); } }
  ]);
  tray.setToolTip('ClawsJoy PA');
  tray.setContextMenu(menu);
  tray.on('double-click', function () { if (win) { win.show(); win.focus(); } });
  log('托盘已立');
}
function buildAppMenu() {
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    { label: 'ClawsJoy', submenu: [
      { label: '检查更新（壳层）', click: function () { checkShellUpdate(); } },
      { type: 'separator' },
      { label: '退出', click: function () { isQuitting = true; saveWindowState(); app.quit(); } } ] },
    { label: '视图', submenu: [ { role: 'reload' }, { role: 'toggleDevTools' }, { type: 'separator' },
      { role: 'resetZoom' }, { role: 'zoomIn' }, { role: 'zoomOut' }, { type: 'separator' },
      { role: 'togglefullscreen' } ] },
    { label: '留言 / 反馈', submenu: [
      { label: '打开留言板', click: function () { if (!win) { createWindow(); } else { win.show(); } reloadPage(); } },
      { label: '打开落点目录（留言收发处）', click: async function () { const r = await openFeedbackDir(); log('openFeedbackDir ⇒ ' + JSON.stringify(r)); } },
      { label: '打开日志目录', click: async function () { await shell.openPath(logsDir()); } } ] }
  ]));
}

// ---------------------------------------------------------------- 壳层之更新（electron-updater · ⛔ 与载荷层相撞）
function checkShellUpdate() {
  let autoUpdater = null;
  try { autoUpdater = require('electron-updater').autoUpdater; }
  catch (e) { log('⛔ 见 electron-updater（壳层之更新 ⛔ 可查）：' + (e && e.message)); return { ok: false, why: 'no-updater' }; }
  try {
    autoUpdater.autoDownload = false;
    autoUpdater.on('update-available', function (i) { log('壳层：有新版 ' + (i && i.version)); });
    autoUpdater.on('update-not-available', function () { log('壳层：已是最新'); });
    autoUpdater.on('error', function (e) { log('壳层之查败（⛔ 充「已是最新」）：' + (e && e.message)); });
    autoUpdater.checkForUpdates();
    return { ok: true };
  } catch (e) { log('壳层之查 ⛔ 得：' + (e && e.message)); return { ok: false, why: String(e && e.message) }; }
}

// ---------------------------------------------------------------- 自测（⛔ 入产品之面）
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
  if (r.port) { createWindow(); }
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
  if (win) { saveWindowState(); }
  r.window_state_file = windowStateFile();
  r.window_state_ok = fs.existsSync(windowStateFile());
  console.log('SHELL_RESULT ' + JSON.stringify(r));
  isQuitting = true;
  app.quit();
  return r;
}

// ---------------------------------------------------------------- 启
ipcMain.handle('pa:open-feedback-dir', function () { return openFeedbackDir(); });

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  log('已有实例在 ⇒ 本进程退出（单实例）');
  app.quit();
} else {
  app.setAppUserModelId(APP_ID);
  app.on('second-instance', function () { if (win) { if (win.isMinimized()) { win.restore(); } win.show(); win.focus(); } });
  app.on('window-all-closed', function () { if (SELFTEST) { app.quit(); } });
  app.on('before-quit', function () { isQuitting = true; saveWindowState(); });
  app.whenReady().then(async function () {
    log('app ready ｜ packaged=' + PACKAGED + ' ｜ ROOT=' + rootDir());
    if (SELFTEST) { await selfTest(); return; }
    await readPort();
    await firstRunCheck();
    await startService();
    createWindow();
    try { buildTray(); } catch (e) { log('托盘 ⛔ 得：' + (e && e.message)); }
    buildAppMenu();
  });
}