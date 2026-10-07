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
const ID = require('./identity');   // ⭐ 身份之判（**一处定形** · pm_1679 §四）
const UP = require('./update');     // ⭐ 载荷层之更新之器（**一处定形** · pm_1684 §二）

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
let IDENTITY = null;   // 身份之判之果（一处）—— 非 null 且 !ok ⇒ ⛔ 载载荷之页

let win = null;
let tray = null;
let trayMenu = null;
let appMenu = null;
let isQuitting = false;
const st = { window: false, page_loaded: false, url: null, title: null, load_error: null };

/* 人话之页（⛔ 载载荷之页 · ⛔ 白屏）—— 一处定形。 */
function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
function msgPageHtml(title, lines) {
  return 'data:text/html;charset=utf-8,' + encodeURIComponent('<h2>' + esc(title) + '</h2>'
    + (lines || []).map(function (t) { return '<p>' + esc(t) + '</p>'; }).join(''));
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
  });
  win.webContents.on('did-fail-load', function (_e, code, desc, url) {
    st.load_error = code + ' ' + desc + ' ' + url;
    log('页载败：' + st.load_error);
  });
  win.on('close', function () { saveWindowState(); if (!isQuitting && !SELFTEST) { win.hide(); return false; } });
  if (msg) { win.loadURL(msgPageHtml('ClawsJoy PA', msg)); }
  else if (PORT) { win.loadURL(paUrl()); }
  else { win.loadURL(msgPageHtml('ClawsJoy PA', ['⛔ 得端口：' + PORT_WHY,
    '因 ＋ 去处：见 %LOCALAPPDATA%\\ClawsJoyPA\\shell\\shell.log'])); }
  log('窗已立（' + s.width + 'x' + s.height + '）');
}

function reloadPage() {
  if (!win) { return; }
  if (IDENTITY && !IDENTITY.ok) { win.loadURL(msgPageHtml('ClawsJoy PA', ID.identityMessage(IDENTITY))); return; }
  if (PORT) { win.loadURL(paUrl()); }
}

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
  trayMenu = Menu.buildFromTemplate([
    { label: '显示', click: function () { if (win) { win.show(); } } },
    { label: '隐藏', click: function () { if (win) { win.hide(); } } },
    { type: 'separator' },
    { label: '启动服务', click: function () { startService(); } },
    { label: '停止服务', click: async function () { await stopService(); } },
    { label: '重启服务', click: async function () { await stopService(); await startService(); reloadPage(); } },
    { type: 'separator' },
    { label: '留言 / 反馈', submenu: fb },
    { type: 'separator' },
    { id: UPDATE_ENTRY_ID, label: UP.entryLabel(null), click: function () { onUpdateClick(); } },
    { label: '检查更新（壳层）', click: function () { checkShellUpdate(); } },
    { type: 'separator' },
    { label: '退出', click: function () { isQuitting = true; saveWindowState(); app.quit(); } }
  ]);
  tray.setToolTip('ClawsJoy PA');
  tray.setContextMenu(trayMenu);
  tray.on('double-click', function () { if (win) { win.show(); win.focus(); } });
  log('托盘已立');
}
function buildAppMenu() {
  appMenu = Menu.buildFromTemplate([
    { label: 'ClawsJoy', submenu: [
      { id: UPDATE_ENTRY_ID, label: UP.entryLabel(null), click: function () { onUpdateClick(); } },
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
    if (win) { await dialog.showMessageBox(win, opt); } else { await dialog.showMessageBox(opt); }
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
    IDENTITY = await serviceIdentity();
    log('身份之核：' + JSON.stringify(IDENTITY));
    await readUpdateState();
    refreshUpdateMenu();
    setInterval(function () { readUpdateState().then(refreshUpdateMenu); }, 60000);
    const _dec = ID.decidePage(IDENTITY);
    if (_dec.load === 'msg') { log('⛔ 载载荷之页（他之 PA 应答）⇒ 以「人话 ＋ 去处」代之'); }
    createWindow(_dec.load === 'msg' ? _dec.msg : null);
    try { buildTray(); } catch (e) { log('托盘 ⛔ 得：' + (e && e.message)); }
    buildAppMenu();
  });
}