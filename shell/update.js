'use strict';
/*
 * update.js —— 「载荷层之更新」之壳侧（**一处定形** · pm_1684 §二）。
 *
 * 其律：
 *   * **纯 node**：⛔ `electron` ／ ⛔ 出网 —— 唯 `127.0.0.1` 之读（可单测 · 承 identity.js）。
 *   * **读数唯 `/health.update`**（一处读 · 承「读一处 · 动分端」）⇒ ⛔ 自取清单 ／ ⛔ 自算。
 *   * **调器之形唯此处出**：`<载荷>\runtime\python.exe -X utf8 -B <载荷>\scripts\win_pa\pa_update.py
 *     --root <载荷> --json --go`（root ＝ 载荷之根 ⇒ **一处定形**）。
 *   * **凡等待 ⇒ 进度 ＋ 时长 ＋ 因 ＋ 去处**（pm_1617 §一.3）⇒ ⛔ 以「转圈」充之。
 *
 * 端之分（pm_1640 §一.2）：本档唯「读 ／ 调器」；面内按钮之端 `POST /v9/pa/update` 归载荷层
 *   （pm_1684 §四）—— 二物 ⛔ 相撞（壳之入口 ⛔ 倚该端）。
 * ⛔ 本档 ⛔ 载「用户面之版」—— 版之读唯 `/health`（pan 之唯一版 · 承 pm_1683 §二）。
 */
const http = require('http');
const path = require('path');
const child = require('child_process');

const HEALTH_MS = 2500;
const UPD_REL = ['scripts', 'win_pa', 'pa_update.py'];

function scriptPath(root) { return path.join.apply(path, [root].concat(UPD_REL)); }

/* ---------------------------------------------------------------- 读数（唯 /health.update） */
function sizeText(n) {
  const b = Number(n || 0);
  if (!b) { return '—'; }
  if (b < 1024) { return b + ' B'; }
  if (b < 1048576) { return (b / 1024).toFixed(1) + ' KB'; }
  return (b / 1048576).toFixed(2) + ' MB';
}

function stateFromHealth(j) {
  const u = (j && j.update) || null;
  if (!u) {
    return { readable: false, available: false, latest: null, current: null,
             files: 0, sizeBytes: 0, channel: null, note: '', noteWhy: '', why: 'no-update-key' };
  }
  const st = { readable: true, available: u.available === true,
               latest: u.latest_version || null, current: u.current_version || null,
               files: Number(u.files || 0), sizeBytes: Number(u.size_bytes || 0),
               channel: u.channel || null, note: String(u.note || ''), noteWhy: String(u.note_why || ''),
               why: '' };
  if (!st.available && !st.current) { st.why = 'unknown'; }
  return st;
}

function entryLabel(st) {
  if (!st || !st.readable) { return '检查更新（读数 ⛔ 得）'; }
  if (st.available) {
    return '更新到 ' + (st.latest || '新版') + '（约 ' + sizeText(st.sizeBytes) + '）';
  }
  return '已是最新（' + (st.current || '—') + '）';
}

/* 入口可否点：读得 ∧ 有新版 ∧ 身份既过（⛔ 于「非本壳之服」之上施增量） */
function entryEnabled(st, identity) {
  return !!(st && st.readable && st.available && identity && identity.ok);
}

function entryWhy(st, identity) {
  if (!st || !st.readable) { return '读 /health.update ⛔ 得 ⇒ 服未起？'; }
  if (!identity || !identity.ok) { return '本壳 ⛔ 载他之 PA ⇒ ⛔ 更新'; }
  if (!st.available) { return '已是最新'; }
  return '';
}

/* ---------------------------------------------------------------- 读 /health（唯 127.0.0.1） */
function probeHealth(port, timeoutMs) {
  return new Promise(function (resolve) {
    if (!port) { resolve({ ok: false, status: 0, body: 'no-port' }); return; }
    const req = http.get({ host: '127.0.0.1', port: port, path: '/health',
                           timeout: timeoutMs || HEALTH_MS },
      function (res) {
        let b = '';
        res.on('data', function (d) { b += d; });
        res.on('end', function () { resolve({ ok: res.statusCode === 200, status: res.statusCode, body: b }); });
      });
    req.on('error', function (e) { resolve({ ok: false, status: 0, body: String((e && e.message) || e) }); });
    req.on('timeout', function () { req.destroy(); resolve({ ok: false, status: 0, body: 'timeout' }); });
  });
}

async function readState(port, timeoutMs) {
  const h = await probeHealth(port, timeoutMs);
  if (!h.ok) { return { readable: false, available: false, why: 'health-' + h.status, raw: h }; }
  let j = null;
  try { j = JSON.parse(h.body); }
  catch (e) { return { readable: false, available: false, why: 'health-not-json', raw: h }; }
  const st = stateFromHealth(j);
  st.raw = j;
  return st;
}

/* ---------------------------------------------------------------- 调器之形（一处定形） */
function updaterArgv(o) {
  return { exe: o.pyExe, cwd: o.root,
           args: ['-X', 'utf8', '-B', scriptPath(o.root), '--root', o.root, '--json', '--go'] };
}

/* ---------------------------------------------------------------- 输出之解（一处定形） */
function lastJson(text) {
  const ls = String(text || '').split('\n');
  for (let i = ls.length - 1; i >= 0; i--) {
    if (!/^\s*\{/.test(ls[i])) { continue; }
    try {
      return JSON.parse(ls.slice(i).filter(function (l) { return !/^\s*\[/.test(l); }).join('\n'));
    } catch (e) { /* 续前寻 */ }
  }
  return null;
}
function firstLine(text, re) {
  const ls = String(text || '').split('\n');
  for (let i = 0; i < ls.length; i++) { if (re.test(ls[i])) { return ls[i].trim(); } }
  return '';
}
function lastLine(text, re) {
  const ls = String(text || '').split('\n');
  for (let i = ls.length - 1; i >= 0; i--) { if (re.test(ls[i])) { return ls[i].trim(); } }
  return '';
}
function rolledBackTo(text) {
  const m = String(text || '').match(/已回滚至\s*`?([^`（）\s]+)`?/);
  return m ? m[1] : null;
}

function parseRun(code, text) {
  const j = lastJson(text);
  if (code === 0) {
    if (j && j.ok === true) {
      return { phase: 'done', ok: true, from: j.from || null, to: j.to || null,
               note: '已升到 ' + (j.to || ''), why: '' };
    }
    const l = lastLine(text, /已是最新/);
    return { phase: 'done', ok: true, from: null, to: null,
             note: l || '已是最新（⛔ 动）', why: '' };
  }
  const rb = rolledBackTo(text);
  const fl = firstLine(text, /\[FAIL\]/);
  return { phase: 'failed', ok: false, from: null, to: null,
           reason: fl || ('更新失败（rc=' + code + '）'),
           rolled_back_to: rb,
           why: rb ? ('已回滚至 ' + rb) : '未见回滚之句' };
}

/* ---------------------------------------------------------------- 人话（进度 ＋ 时长 ＋ 因 ＋ 去处） */
function statusLines(run, elapsedS, dest) {
  const out = [];
  const ph = (run && run.phase) || 'running';
  out.push('状态：' + (ph === 'done' ? '已完成' : (ph === 'failed' ? '失败' : (ph === 'idle' ? '无（已是最新）' : '进行中'))));
  out.push('时长：' + (Number(elapsedS || 0)).toFixed(1) + ' 秒');
  if (run && run.note) { out.push('结果：' + run.note); }
  if (run && run.reason) { out.push('因：' + run.reason); }
  if (run && run.why) { out.push(run.why); }
  out.push('去处：' + (dest || '%LOCALAPPDATA%\\ClawsJoyPA\\shell\\shell.log'));
  return out;
}

/* ---------------------------------------------------------------- 跑器（一处定形） */
function runUpdate(o) {
  return new Promise(function (resolve) {
    const spec = updaterArgv(o);
    let out = '';
    let done = false;
    const t0 = Date.now();
    const to = o.timeoutMs || 900000;
    let timer = null;
    const finish = function (code, why) {
      if (done) { return; }
      done = true;
      if (timer) { clearTimeout(timer); }
      const run = parseRun(code, out);
      run.code = code;
      run.spawn_why = why || '';
      run.elapsed_s = (Date.now() - t0) / 1000;
      run.out = out;
      resolve(run);
    };
    let p = null;
    try {
      p = child.spawn(spec.exe, spec.args, { cwd: spec.cwd, windowsHide: true });
    } catch (e) { finish(-1, 'SPAWN: ' + (e && e.message)); return; }
    timer = setTimeout(function () { try { p.kill(); } catch (e) { /* 已亡 */ } finish(-1, 'TIMEOUT'); }, to);
    const feed = function (d) {
      const s = d.toString('utf8');
      out += s;
      if (o.onLine) { try { o.onLine(s); } catch (e) { /* 报之侧之错 ⛔ 阻更新 */ } }
    };
    p.stdout.on('data', feed);
    p.stderr.on('data', feed);
    p.on('error', function (e) { finish(-1, 'ERROR: ' + (e && e.message)); });
    p.on('close', function (code) { finish(code, ''); });
  });
}

/* 一步：读 ⇒ 门 ⇒ 跑（壳侧唯用此入口） */
async function updatePayload(o) {
  const st = o.state || await readState(o.port, o.healthMs);
  if (!st.readable) {
    return { phase: 'failed', ok: false, reason: '读 /health.update ⛔ 得',
             why: String(st.why || ''), refused: 'no-read' };
  }
  if (!entryEnabled(st, o.identity)) {
    const why = entryWhy(st, o.identity);
    if (st.available) { return { phase: 'failed', ok: false, reason: why, refused: why }; }
    return { phase: 'idle', ok: false, refused: why, note: '已是最新（' + (st.current || '') + '）' };
  }
  return runUpdate(o);
}

module.exports = {
  sizeText: sizeText, stateFromHealth: stateFromHealth, entryLabel: entryLabel,
  entryEnabled: entryEnabled, entryWhy: entryWhy, probeHealth: probeHealth, readState: readState,
  scriptPath: scriptPath, updaterArgv: updaterArgv, lastJson: lastJson, firstLine: firstLine,
  lastLine: lastLine, rolledBackTo: rolledBackTo, parseRun: parseRun, statusLines: statusLines,
  runUpdate: runUpdate, updatePayload: updatePayload
};