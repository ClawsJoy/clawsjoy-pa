'use strict';
/*
 * identity.js —— 「应答之 /health 是否本壳之载荷」之判（**一处定形** · 承 pm_1679 §四）。
 *
 * 其险（承 pm_1679 §四.1）：净机或有旧版之 PA 在跑（同端口）⇒ 壳之首启起不来自己之服
 *   ⇒ 而 `GET /health` **仍成**（旧服务应答）⇒ 壳若直载页 ⇒ **静默载旧页** ＝「未知 ⛔ 充已知」之族。
 * 其判（一处定形）：起服后核 `build.path` ≡ 壳内载荷之 `<root>/version.json`
 *   （旧包 ⛔ 有 `/health.build` ⇒ 一问即辨）。
 * ⛔ 出机：唯 `127.0.0.1` 之探活。 | ⛔ electron：本档唯纯 node ⇒ 供 `node` 台架直测（正反控）。
 */
const http = require('http');
const path = require('path');

const HEALTH_MS = 2500;

function normPath(p) {
  try { return path.resolve(String(p)).replace(/[\\/]+$/, '').toLowerCase(); }
  catch (e) { return null; }
}

function probeHealthAt(port, timeoutMs) {
  return new Promise(function (resolve) {
    if (!port) { resolve({ ok: false, status: 0, body: 'no-port' }); return; }
    const req = http.get({ host: '127.0.0.1', port: port, path: '/health', timeout: timeoutMs || HEALTH_MS },
      function (res) {
        let b = '';
        res.on('data', function (d) { b += d; });
        res.on('end', function () { resolve({ ok: res.statusCode === 200, status: res.statusCode, body: b }); });
      });
    req.on('error', function (e) { resolve({ ok: false, status: 0, body: String((e && e.message) || e) }); });
    req.on('timeout', function () { req.destroy(); resolve({ ok: false, status: 0, body: 'timeout' }); });
  });
}

function evaluateHealth(body, wantPath) {
  let j = null;
  if (typeof body === 'string') {
    try { j = JSON.parse(body); }
    catch (e) { return { ok: false, why: 'health-⛔-JSON', got: null, want: wantPath }; }
  } else { j = body || null; }
  const b = (j && j.build) || null;
  if (!b || b.available !== true || !b.path) {
    return { ok: false, why: 'no-build-键', got: (j && j.version) || null, want: wantPath };
  }
  if (normPath(b.path) !== normPath(wantPath)) {
    return { ok: false, why: 'foreign-root', got: String(b.path), want: wantPath };
  }
  return { ok: true, why: '', got: String(b.path), want: wantPath };
}

function identityMessage(v) {
  const w = (v && v.want) || '';
  const g = (v && v.got) ? v.got : '（⛔ 读）';
  return [
    '本机已有一个 PA 在跑（**不是这一个**）⇒ 本壳 ⛔ 载其页。',
    '因：壳内载荷之装根 ＝ ' + w + '；而应答者之装根 ＝ ' + g
      + '（' + ((v && v.why) || '') + '）',
    '去处：先把它关掉（其托盘 ⇒ 退出 ⁄ 卸载旧版）再看本壳；',
    '本壳之日志 ⇒ %LOCALAPPDATA%\\ClawsJoyPA\\shell\\shell.log'
  ];
}

function decidePage(v) {
  if (v && v.ok) { return { load: 'page' }; }
  return { load: 'msg', msg: identityMessage(v || { why: 'health-⛔-答' }) };
}

module.exports = { normPath: normPath, probeHealthAt: probeHealthAt, evaluateHealth: evaluateHealth,
                   identityMessage: identityMessage, decidePage: decidePage };
