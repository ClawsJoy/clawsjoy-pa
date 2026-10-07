# -*- coding: utf-8 -*-
u"""pm_1684 §二 之齿 —— 壳之「载荷层之更新」入口（update.js · 一处定形）。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_shell_update_1684.py -q

判据：
  S1 一处定形 · 纯 node：`main.js` 之 `require('./update')` 唯 1 处 · `update.js` ⛔ 引 `electron`
     · ⛔ 出机（无 `https://` ／ 无 `fetch(` ／ 无 `0.0.0.0` ／ 无 `XMLHttpRequest`）· 唯 `127.0.0.1`
     · 且入壳之 `files` · 且「调器之形」唯 `updaterArgv` 一处（`main.js` ⛔ 自拼器之名 ／ ⛔ 自拼 `--go`）。
  S1b 入口唯一：`function onUpdateClick()` 唯 1 处 · 二处菜单（托盘 ／ 应用菜单）共引 `UPDATE_ENTRY_ID`。
  S2 纯函之正反控（node 台架）：`stateFromHealth` ／ `entryLabel` ／ `entryEnabled` ／ `entryWhy`
     ／ `parseRun` ／ `rolledBackTo` ／ `statusLines`（退路之门：读不得 ／ 异身份 ／ 已最新 ／ 成 ／ 败）。
  S3 真 HTTP 之正反控（node 台架）：二桩之 `/health.update`（有新版 ／ 已最新）⇒ `readState` ⇒ 逐字得判。
  S4 器之真跑之败（node 台架）：坏 exe ⇒ **真 spawn 之败** ⇒ `phase == 'failed'` ∧ 人话有「去处」
     （⛔ 触网 ／ ⛔ 动盘 ／ ⛔ 及 `5102`）。
"""
from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SHELL = ROOT / "shell"
UPD = SHELL / "update.js"
MAIN = SHELL / "main.js"
PKG = SHELL / "package.json"


def _read(p: Path) -> str:
    return io.open(str(p), encoding="utf-8").read()


def _node(src: str) -> dict:
    r = subprocess.run(["node", "-e", src], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=180, cwd=str(SHELL))
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    return json.loads((r.stdout or "").strip().splitlines()[-1])


# ---------- S1 一处定形 · 纯 node ----------

def test_S1_update_js_pure_and_referenced_once():
    t = _read(MAIN)
    assert t.count("require('./update')") == 1, u"调器之形须唯 1 处引"
    d = _read(UPD)
    assert "require('electron')" not in d, u"update.js 须纯 node（供台架直测）"
    for bad in ("https://", "0.0.0.0", "fetch(", "XMLHttpRequest"):
        assert bad not in d, u"update.js ⛔ 得含 " + bad
    assert "host: '127.0.0.1'" in d, u"探活须唯 127.0.0.1"
    pkg = json.loads(_read(PKG))
    assert "update.js" in pkg["build"]["files"], u"须入壳（否则 ⛔ 入 app.asar）"


def test_S1b_updater_argv_is_single_place():
    t = _read(MAIN)
    assert "pa_update.py" not in t, u"器之名唯 update.js 出（main.js ⛔ 自拼）"
    assert "--json', '--go'" not in t, u"器之参表唯 update.js 出（main.js ⛔ 自拼）"
    assert t.count("function updaterArgv") == 0, u"调器之形 ⛔ 于 main.js 立（唯 update.js）"
    assert t.count("UP.updatePayload(") == 1, u"壳之跑唯经 updatePayload"
    d = _read(UPD)
    assert d.count("function updaterArgv") == 1, u"调器之形唯此处出"
    assert d.count("'pa_update.py'") == 1, u"器之名唯 UPD_REL 一处出"


def test_S1c_entry_is_single_place():
    t = _read(MAIN)
    assert t.count("function onUpdateClick()") == 1, u"入口之实唯 1 处"
    assert t.count("UPDATE_ENTRY_ID") >= 3, u"二处菜单须共引同一 id（托盘 ／ 应用菜单）"
    assert "entryWhy" in t, u"⛔ 可点 ⇒ 须出「因」"


# ---------- S2 纯函之正反控 ----------

_HARNESS = r"""
const U = require('./update.js');
const out = {};
out.avail   = U.stateFromHealth({update:{available:true, latest_version:'9.0.3', size_bytes:72091}});
out.latest  = U.stateFromHealth({update:{available:false, current_version:'9.0.2', note:'已是最新'}});
out.nokey   = U.stateFromHealth({status:'healthy'});
out.readng  = U.stateFromHealth({update:null});
out.havail  = U.stateFromHealth({update:{available:true, latest_version:'9.0.3', size_bytes:72091}});
out.label_a = U.entryLabel(U.stateFromHealth({update:{available:true, latest_version:'9.0.3', size_bytes:72091}}));
out.label_l = U.entryLabel(U.stateFromHealth({update:{available:false, current_version:'9.0.2'}}));
out.label_n = U.entryLabel(U.stateFromHealth({status:'healthy'}));
out.on_ok   = U.entryEnabled(out.havail, {ok:true});
out.on_ng   = U.entryEnabled(out.havail, {ok:false});
out.on_non  = U.entryEnabled(out.havail, null);
out.on_lat  = U.entryEnabled(U.stateFromHealth({update:{available:false, current_version:'9.0.2'}}), {ok:true});
out.on_nok  = U.entryEnabled(out.nokey, {ok:true});
out.why_ng  = U.entryWhy(out.havail, {ok:false});
out.why_lat = U.entryWhy(U.stateFromHealth({update:{available:false, current_version:'9.0.2'}}), {ok:true});
out.why_nok = U.entryWhy(out.nokey, {ok:true});
out.rb      = U.rolledBackTo('[FAIL] **已回滚至 ' + String.fromCharCode(96) + '9.0.1' + String.fromCharCode(96) + '**（fail-loud）');
out.p_done  = U.parseRun(0, '[1/10] 清单：v9.0.2\n[10/10] 成：9.0.1 ⇒ 9.0.2\n{\n "ok": true,\n "from": "9.0.1",\n "to": "9.0.2",\n "files": {"n": 5},\n "backup": "b",\n "staged": "s"\n}');
out.p_latest= U.parseRun(0, '[2/10] 已是最新（9.0.2）⇒ ⛔ 动');
out.p_fail  = U.parseRun(2, '[FAIL] 基础版 ⛔ 符：本机 9.0.1 ≠ base_version 9.0.2\n[FAIL] **已回滚至 ' + String.fromCharCode(96) + '9.0.1' + String.fromCharCode(96) + '**（fail-loud）');
out.p_dead  = U.parseRun(-1, '');
out.s_done  = U.statusLines(out.p_done, 12.34, null);
out.s_fail  = U.statusLines(out.p_fail, 3.2, null);
out.s_idle  = U.statusLines({phase:'idle'}, 0, null);
out.size    = [U.sizeText(0), U.sizeText(900), U.sizeText(16978), U.sizeText(824024)];
console.log(JSON.stringify(out));
"""


def test_S2_pure_functions_positive_and_negative():
    u = _node(_HARNESS)
    assert u["avail"]["readable"] is True and u["avail"]["available"] is True, u["avail"]
    assert u["latest"]["readable"] is True and u["latest"]["available"] is False, u["latest"]
    assert u["latest"]["current"] == "9.0.2", u["latest"]
    assert u["nokey"]["readable"] is False and u["nokey"]["why"] == "no-update-key", u["nokey"]
    assert u["readng"]["readable"] is False, u["readng"]
    assert u["label_a"].startswith(u"更新到 9.0.3"), u["label_a"]
    assert u"约 70.4 KB" in u["label_a"], u["label_a"]
    assert u["label_l"] == u"已是最新（9.0.2）", u["label_l"]
    assert u"读数 ⛔ 得" in u["label_n"], u["label_n"]
    assert u["on_ok"] is True, u["on_ok"]
    assert u["on_ng"] is False and u["on_non"] is False, u
    assert u["on_lat"] is False and u["on_nok"] is False, u
    assert u"他之 PA" in u["why_ng"], u["why_ng"]
    assert u["why_lat"] == u"已是最新", u["why_lat"]
    assert u"/health.update" in u["why_nok"], u["why_nok"]
    assert u["rb"] == "9.0.1", u["rb"]
    assert u["p_done"]["phase"] == "done" and u["p_done"]["ok"] is True, u["p_done"]
    assert u["p_done"]["to"] == "9.0.2" and u["p_done"]["from"] == "9.0.1", u["p_done"]
    assert u["p_latest"]["phase"] == "done" and u["p_latest"]["ok"] is True, u["p_latest"]
    assert u"已是最新" in u["p_latest"]["note"], u["p_latest"]
    assert u["p_fail"]["phase"] == "failed" and u["p_fail"]["ok"] is False, u["p_fail"]
    assert u"基础版 ⛔ 符" in u["p_fail"]["reason"], u["p_fail"]
    assert u["p_fail"]["rolled_back_to"] == "9.0.1", u["p_fail"]
    assert u["p_dead"]["phase"] == "failed", u["p_dead"]
    assert u["s_done"][0] == u"状态：已完成" and u["s_done"][1].startswith(u"时长：12.3"), u["s_done"]
    assert u["s_done"][-1].startswith(u"去处："), u["s_done"]
    f = u" ".join(u["s_fail"])
    assert u"状态：失败" in f and u"已回滚至 9.0.1" in f and u"去处：" in f, u["s_fail"]
    assert u["s_idle"][0] == u"状态：无（已是最新）", u["s_idle"]
    assert u["size"] == [u"—", u"900 B", u"16.6 KB", u"804.7 KB"], u["size"]


# ---------- S3 真 HTTP 之正反控 ----------

_HTTP = r"""
const U = require('./update.js');
const http = require('http');
function stub(update) {
  return new Promise((res) => {
    const s = http.createServer((q, r) => {
      r.writeHead(200, {'Content-Type':'application/json'});
      r.end(JSON.stringify({status:'healthy', version:'9.0.1', update}));
    });
    s.listen(0, '127.0.0.1', () => res({s, port:s.address().port}));
  });
}
(async () => {
  const a = await stub({available:true, latest_version:'9.0.3', size_bytes:72091, files:7});
  const b = await stub({available:false, current_version:'9.0.2', note:'已是最新'});
  const c = await stub(undefined);
  const out = {};
  out.a = await U.readState(a.port);
  out.b = await U.readState(b.port);
  out.c = await U.readState(c.port);
  out.dead = await U.readState(9);
  out.a_on = U.entryEnabled(out.a, {ok:true});
  out.b_off = !U.entryEnabled(out.b, {ok:true});
  out.a_label = U.entryLabel(out.a);
  out.b_label = U.entryLabel(out.b);
  a.s.close(); b.s.close(); c.s.close();
  console.log(JSON.stringify(out));
})();
"""


@pytest.mark.skipif(not (SHELL / "update.js").is_file(), reason=u"无 update.js")
def test_S3_real_http_positive_and_negative():
    u = _node(_HTTP)
    assert u["a"]["readable"] is True and u["a"]["available"] is True, u["a"]
    assert u["a"]["latest"] == "9.0.3" and u["a"]["sizeBytes"] == 72091, u["a"]
    assert u["a_on"] is True, u["a"]
    assert u["a_label"].startswith(u"更新到 9.0.3"), u["a_label"]
    assert u["b"]["readable"] is True and u["b"]["available"] is False, u["b"]
    assert u["b_off"] is True, u["b"]
    assert u["b_label"] == u"已是最新（9.0.2）", u["b_label"]
    assert u["c"]["readable"] is False and u["c"]["why"] == "no-update-key", u["c"]
    assert u["dead"]["readable"] is False, u["dead"]


# ---------- S4 器之真跑之败 ----------

_BADRUN = r"""
const U = require('./update.js');
const path = require('path');
(async () => {
  const root = process.cwd().replace(/[\\/]shell$/, '');
  const t0 = Date.now();
  const run = await U.runUpdate({ pyExe: path.join(root, 'runtime', 'no-such-python.exe'),
                                  root: root, timeoutMs: 30000 });
  const out = { phase: run.phase, code: run.code, lines: U.statusLines(run, run.elapsed_s, null),
                ms: Date.now() - t0 };
  console.log(JSON.stringify(out));
})();
"""


def test_S4_real_spawn_failure_is_loud():
    u = _node(_BADRUN)
    assert u["phase"] == "failed", u
    assert u["code"] != 0, u
    f = u" ".join(u["lines"])
    assert u"状态：失败" in f and u"去处：" in f, u
    assert u["ms"] < 30000, u