// L3 扫描器（S2 主）· **落地候选（未落）** —— Paseo 侧主动扫「对岸可读」的产出型心跳
// 依据：dsh\2026-09-21-dsh-N1_L3落地设计件_S2为主_v1.md（95d1becb）· L3主动扫候选 498b360c
//       @DSH 写端补丁件（载体 = dsh\_心跳_DSH.jsonl · 6 字段 ts/prod/iter/ev/fail_streak/sha）
//       DS 889 §一-2/3（S2 主 · S3 备 · S1 不单独用）· 891 §一-2（超时 1200 s ＋ 地板 1800 s）· 893 §四（四项必带）
// 性质：新件候选；未改任何产品件、未起进程、未占窗。落地 = 起一个进程（kill 即回滚）。
// 硬约束：① 告警出主机（Paseo → codex queue），不写回被监控盘/队列；
//         ② 冷启动/无基线 ⇒ UNKNOWN（不判绿不判红，不写 0）；③ 每次扫必留痕（防覆盖静默消失）；
//         ④ 同一 episode 只投一次（episode 身份，非时间地板 —— 承 DS ③ 改裁）；⑤ 未标定量只报不判。
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import crypto from 'node:crypto';
import os from 'node:os';
import path from 'node:path';

// —— 路径真源（⛔ 不复述绝对路径；绝对路径只在本块出现一次）——
// 承 CEO 2026-09-28 终裁 §三①（准入普通批）；判据一律引真源，⛔ 不许只加新串
// （那是把 1 个硬编码换成 N 个 —— 判据仍不跟随）。唯一真源 = 环境变量：
//   vault 用与 Python 侧 `core.lib.paths.vault_root()` **同名**的 `PA_VAULT_DIR`；
//   仓库根 `CLAWSJOY_ROOT`；CLI `CODEX_CLI`。⇒ 换树／换机只改环境，⛔ 不改本件。
// 两形态（Windows `D:\` ／ WSL `/mnt/d/`）由 inRoot() 归一后比较 ⇒ 两种写法都认。
const REPO_ROOT = process.env.CLAWSJOY_ROOT || 'D:\\clawsjoy_v9';
const VAULT_ROOT = process.env.PA_VAULT_DIR || 'D:\\Obsidian\\ClawsJoy\\ClawsJoy';
const CODEX_CLI = process.env.CODEX_CLI || 'D:\\npm-global\\node_modules\\@openai\\codex\\bin\\codex.js';
const POLL_DIR = path.join(REPO_ROOT, 'data', 'tmp', 'cdp', '_poll');
const DSH_DIR = path.join(VAULT_ROOT, 'dsh');

export const DEFAULT_CFG = {
  periodSec: 300,          // 扫描周期（须 <= 超时/4，防漏跳）
  timeoutSec: 1200,        // 心跳龄超时（20 min）—— 上界必须 < 既有空窗（1800 s）
  blindfloorSec: 1800,     // 地板：防抖（与现网 [watcher:BLIND] 地板同源）
  prodStreakN: 2,          // prod==0 连续跳数 N（先只报不判 —— N 待读数标定）
  prodStreakAlert: false,  // N 未标定 ⇒ false
  carriers: [
    { id: 'w', label: 'W·采集器', path: path.join(POLL_DIR, 'watch_health.json'),
      fmt: 'json', tsField: 'at', prodField: null, deriveShaField: 'sha' },
    { id: 'l', label: 'L·DSH 巡检', path: path.join(DSH_DIR, '_心跳_DSH.jsonl'),
      fmt: 'jsonl', tsField: 'ts', prodField: 'prod', deriveShaField: null },
  ],
  tracePath: path.join(REPO_ROOT, 'data', 'tmp', 'l3', 'scan_trace.jsonl'),
  traceKeep: 2000,
  alert: { mode: 'paseo', thread: '01a0ae94-cf6a-71b1-9c11-8353373c0943',
           cli: CODEX_CLI },
  forbiddenRoots: [POLL_DIR, DSH_DIR],
};

const iso = (ms) => new Date(ms).toISOString();
const inRoot = (p, root) => {
  const a = String(p).toLowerCase().replace(/\//g, '\\'), b = String(root).toLowerCase().replace(/\//g, '\\');
  return a === b || a.startsWith(b.endsWith('\\') ? b : b + '\\');
};
export const defaultReadFile = (p) => fs.readFileSync(p, 'utf8');

// —— 配置机检（fail-loud：不符即拒扫）——
export function checkConfig(cfg = DEFAULT_CFG) {
  const errors = [];
  if (cfg.periodSec * 4 > cfg.timeoutSec) errors.push({ code: 'period_too_long', msg: '周期 > 超时/4 ⇒ 会漏跳' });
  if (cfg.periodSec + cfg.timeoutSec >= cfg.blindfloorSec)
    errors.push({ code: 'cover_eaten', msg: '周期+超时 >= 地板 ⇒ 检出被地板吞（统一反例③）' });
  if (!Array.isArray(cfg.carriers) || cfg.carriers.length < 2)
    errors.push({ code: 'single_side', msg: '只配一处载体 ⇒ 单侧盲区（统一反例④）' });
  if (cfg.alert?.mode !== 'paseo') errors.push({ code: 'alert_not_out_of_host', msg: '交付面必须出主机' });
  for (const p of [cfg.tracePath].filter(Boolean))
    for (const r of cfg.forbiddenRoots || [])
      if (inRoot(p, r)) errors.push({ code: 'write_back', msg: '留痕落进被监控盘/队列：' + p });
  return { ok: errors.length === 0, errors };
}

// —— 载体读（读不到 ⇒ UNKNOWN，不当绿）——
export function readCarrier(c, readFile = defaultReadFile) {
  let text;
  try { text = readFile(c.path); }
  catch (e) { return { ok: false, unknown: 'read_fail', detail: String((e && e.message) || e).slice(0, 160) }; }
  if (text == null || text === '') return { ok: false, unknown: 'missing', detail: 'empty/absent' };
  let rec = null, tail = null;
  try {
    if (c.fmt === 'jsonl') {
      const lines = text.split(/\r?\n/).filter((s) => s.trim().length);
      if (!lines.length) return { ok: false, unknown: 'empty', detail: '0 lines' };
      tail = lines.slice(-500);
      rec = JSON.parse(lines[lines.length - 1]);
    } else { rec = JSON.parse(text); }
  } catch (e) { return { ok: false, unknown: 'parse_fail', detail: String((e && e.message) || e).slice(0, 160) }; }
  const tsMs = Date.parse(rec[c.tsField]);
  if (!Number.isFinite(tsMs)) return { ok: false, unknown: 'no_ts', detail: 'ts=' + String(rec[c.tsField]) };
  let prodStreak = null;
  if (c.prodField && tail) {
    prodStreak = 0;
    for (let i = tail.length - 1; i >= 0; i--) {
      let r; try { r = JSON.parse(tail[i]); } catch (e) { break; }
      if (Number(r[c.prodField]) === 0) prodStreak++; else break;
    }
  }
  return { ok: true, rec, tsMs, prodStreak, tailLines: tail ? tail.length : null };
}

function fileSha8(p) {
  try { return crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex').slice(0, 8); }
  catch (e) { return null; }
}

// —— 单侧判 ——
export function judgeSide(c, cfg, nowMs, readFile = defaultReadFile, prevSide = null) {
  const base = { id: c.id, label: c.label, path: c.path, carrier_sha8: fileSha8(c.path) };
  const r = readCarrier(c, readFile);
  if (!r.ok) return Object.assign({}, base, { verdict: 'unknown', unknown: r.unknown, detail: r.detail, alert: null, report: null });
  const rec = r.rec;
  const s = Object.assign({}, base, {
    verdict: 'ok', age_sec: Math.round((nowMs - r.tsMs) / 1000), ts: iso(r.tsMs), scanned_at: iso(nowMs),
    ev: rec.ev === undefined ? null : rec.ev, fail_streak: rec.fail_streak === undefined ? null : rec.fail_streak,
    iter: rec.iter === undefined ? null : rec.iter, sha: rec.sha === undefined ? null : rec.sha,
    prod: c.prodField ? (rec[c.prodField] === undefined ? null : rec[c.prodField]) : null,
    prod_source: c.prodField ? 'carrier' : 'derived', prod_streak: r.prodStreak,
    alert: null, report: null,
  });
  if (!c.prodField) {                       // 载体无 prod 字段 ⇒ 派生，且只报不判（不冒充载体自述）
    const prevSha = prevSide ? prevSide.sha : null;
    s.prod_derived = prevSha == null ? null : (String(prevSha) === String(s.sha) ? 0 : 1);
    s.report = { code: 'prod_derived', note: prevSha == null ? 'no_baseline' : 'sha_cmp', value: s.prod_derived };
  }
  if (s.age_sec > cfg.timeoutSec) {
    s.verdict = 'alert';
    s.alert = { reason: 'heartbeat_stale', ep: 'ts:' + s.ts, age_sec: s.age_sec, timeout_sec: cfg.timeoutSec };
    return s;
  }
  const pfs = prevSide ? prevSide.fail_streak : null;
  if (s.fail_streak !== null && pfs !== null && Number(s.fail_streak) > Number(pfs)) {
    s.verdict = 'alert';
    s.alert = { reason: 'fail_streak_rise', ep: String(pfs) + '->' + String(s.fail_streak), from: pfs, to: s.fail_streak };
    return s;
  }
  if (s.prod_source === 'carrier' && s.prod_streak !== null && s.prod_streak >= cfg.prodStreakN) {
    s.report = { code: 'prod_streak', n: cfg.prodStreakN, streak: s.prod_streak };
    if (cfg.prodStreakAlert) { s.verdict = 'alert'; s.alert = { reason: 'prod_streak', ep: 'streak:' + s.prod_streak, streak: s.prod_streak }; }
  }
  return s;
}

// —— 告警文本（四项必带；缺一即判据红）——
export function alertText(cfg, side, a) {
  const age = a.age_sec === undefined ? 'UNKNOWN' : a.age_sec + 's';
  const unk = a.reason === 'heartbeat_stale' ? '否（龄已知）' : '否';
  return [
    '[L3][' + side.id + '] ' + a.reason + ' — 产出型心跳判出异常',
    '① 心跳龄：' + age + '（扫于 ' + side.scanned_at + '；载体 ts=' + side.ts + '；差 ' + age + '）',
    '② 载体：' + side.path + ' ｜ 载体件 sha8=' + (side.carrier_sha8 || 'UNKNOWN') + ' ｜ 记录内 sha=' + (side.sha || 'UNKNOWN'),
    '③ 产出型证据：prod=' + String(side.prod) + '（来源=' + side.prod_source + '；连续 0 跳=' + String(side.prod_streak) + '）· ev=' + String(side.ev) + ' · fail_streak=' + String(side.fail_streak) + ' · iter=' + String(side.iter),
    '④ UNKNOWN 语义：' + unk + '；无基线 ⇒ 报 UNKNOWN，不判绿不判红（L-06）',
  ].join('\n');
}

// —— 一轮扫（纯函数；I/O 全部注入）——
export function evaluate(cfg, prev, nowMs, readFile = defaultReadFile) {
  const sides = {};
  for (const c of cfg.carriers) {
    const p = prev && prev.sides ? prev.sides[c.id] || null : null;
    sides[c.id] = judgeSide(c, cfg, nowMs, readFile, p);
  }
  const alerts = [], reports = [], unknowns = [];
  for (const id of Object.keys(sides)) {
    const s = sides[id];
    if (s.alert) alerts.push(Object.assign({ side: id, delivered: false }, s.alert));
    if (s.report) reports.push(Object.assign({ side: id }, s.report));
    if (s.verdict === 'unknown') unknowns.push({ side: id, unknown: s.unknown, detail: s.detail });
  }
  const verdict = alerts.length ? 'alert' : (unknowns.length ? 'unknown' : 'ok');
  return { at: iso(nowMs), verdict, sides, alerts, reports, unknowns };
}

// —— 同 episode 只投一次（episode 身份 ⇒ 非时间地板）——
export function shouldDeliver(prevAlert, a) {
  if (!prevAlert) return true;
  return prevAlert.ep !== a.ep;
}

export function readTraceTail(tracePath, n = 1) {
  try {
    const lines = fs.readFileSync(tracePath, 'utf8').split(/\r?\n/).filter((s) => s.trim().length);
    return { lines: lines.slice(-n).map((s) => JSON.parse(s)), total: lines.length };
  } catch (e) { return { lines: [], total: 0 }; }
}

export function writeTrace(cfg, rec) {
  fs.appendFileSync(cfg.tracePath, JSON.stringify(rec) + '\n', 'utf8');
  let n = 0;
  try { n = fs.readFileSync(cfg.tracePath, 'utf8').split(/\r?\n/).filter((s) => s.trim().length).length; } catch (e) { return; }
  if (n > cfg.traceKeep) {                        // 只在超限时轮转（保末 500 行）—— 防覆盖静默消失（L-47）
    const all = fs.readFileSync(cfg.tracePath, 'utf8').split(/\r?\n/).filter((s) => s.trim().length);
    fs.writeFileSync(cfg.tracePath, all.slice(-500).join('\n') + '\n', 'utf8');
  }
}

// —— 一轮扫 + 投递 + 留痕（I/O 编排）——
export function scanOnce(cfg = DEFAULT_CFG, nowMs = Date.now(), deps = {}) {
  const exec = deps.exec || ((args) => execFileSync('node', args, { encoding: 'utf8', timeout: 60000, windowsHide: true }));
  const readFile = deps.readFile || defaultReadFile;
  const cc = checkConfig(cfg);
  const prevTail = deps.prev !== undefined ? deps.prev : (readTraceTail(cfg.tracePath, 1).lines.slice(-1)[0] || null);
  const ev = evaluate(cfg, prevTail, nowMs, readFile);
  const prevAlerts = (prevTail && prevTail.alerts) || [];
  const delivered = [];
  for (const a of ev.alerts) {
    const p = prevAlerts.find((x) => x.side === a.side && x.reason === a.reason) || null;
    if (!shouldDeliver(p, a)) { a.delivered = false; a.suppressed = 'same_episode'; continue; }
    const msg = alertText(cfg, ev.sides[a.side], a);
    try { exec([cfg.alert.cli, 'queue', '--thread', cfg.alert.thread, '--message', msg]); a.delivered = true; }
    catch (e) { a.delivered = false; a.delivery_error = String((e && e.message) || e).slice(0, 200); }
    delivered.push(a);
  }
  ev.cfg_errors = cc.errors;
  ev.prev_at = prevTail ? prevTail.at : null;
  writeTrace(cfg, { at: ev.at, verdict: ev.verdict, sides: ev.sides, alerts: ev.alerts, reports: ev.reports, unknowns: ev.unknowns });
  return ev;
}

// —— CLI（直接跑才进循环；--once 单轮；--selftest 只检配置）——
const isMain = (() => { try { return import.meta.url === new URL('file://' + process.argv[1].replace(/\\/g, '/')).href; } catch (e) { return false; } })();
if (isMain) {
  const cc = checkConfig(DEFAULT_CFG);
  if (!cc.ok) { console.error('[L3] 配置机检不过 ⇒ 拒扫：' + JSON.stringify(cc.errors)); process.exit(2); }
  if (process.argv.includes('--selftest')) { console.log('[L3] 配置机检 OK'); process.exit(0); }
  const once = process.argv.includes('--once');
  // --dry：只读现网载体、**不投递**（exec 打桩）、留痕落系统临时目录（不动产品面）
  const dry = process.argv.includes('--dry');
  const dryCfg = dry ? Object.assign({}, DEFAULT_CFG, { tracePath: path.join(os.tmpdir(), 'l3_dry_trace.jsonl') }) : DEFAULT_CFG;
  const tick = () => {
    const deps = dry ? { exec: (a) => ('DRY_NO_DELIVER:' + a[2]) } : {};
    const r = scanOnce(dryCfg, Date.now(), deps);
    console.log(JSON.stringify({ at: r.at, dry, verdict: r.verdict,
      sides: Object.keys(r.sides).map((k) => ({ id: k, v: r.sides[k].verdict, age_sec: r.sides[k].age_sec,
        ev: r.sides[k].ev, prod: r.sides[k].prod, prod_source: r.sides[k].prod_source, prod_streak: r.sides[k].prod_streak,
        fail_streak: r.sides[k].fail_streak, unknown: r.sides[k].unknown })),
      alerts: r.alerts.length, reports: r.reports.length, unknowns: r.unknowns.length }));
  };
  tick();
  if (!once) setInterval(tick, DEFAULT_CFG.periodSec * 1000);
}