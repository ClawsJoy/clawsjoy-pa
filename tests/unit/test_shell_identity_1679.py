# -*- coding: utf-8 -*-
u"""pm_1679 \u00a7\u56db 之\u9f7f \u2014\u2014 \u58f3\u987b\u8fa8\u300c\u4ed6\u4e4b PA\u300d\uff08identity.js \u00b7 \u4e00\u5904\u5b9a\u5f62\uff09\u3002

\u4ee5\u4f55\u5f62\u8c03\u7528\uff1a
  python -X utf8 -B -m pytest tests/unit/test_shell_identity_1679.py -q

\u5224\u636e\uff1a
  S1 \u4e00\u5904\u5b9a\u5f62 \u00b7 \u7eaf node\uff1a`main.js` \u4e4b `require('./identity')` \u552f 1 \u5904 \u00b7 `identity.js` \u26d4 \u5f15 `electron`
     \u00b7 \u26d4 \u51fa\u673a\uff08\u65e0 `https://` \u2044 \u65e0\u5916\u57df\uff09\u00b7 \u4e14\u5165\u58f3\u4e4b `files`\u3002
  S2 \u7eaf\u51fd\u4e4b\u6b63\u53cd\u63a7\uff08node \u53f0\u67b6\uff09\uff1a\u540c\u8def \u21d2 ok\uff1b\u5f02\u8def \u21d2 `foreign-root`\uff1b\u65e0 `build` \u952e\uff08\u65e7\u5305\uff09\u21d2 \u26d4\uff1b
     `available=false` \u21d2 \u26d4\uff1b\u5206\u9694\u7b26 \u2044 \u5927\u5c0f\u5199\u4e4b\u5bb9 \u21d2 ok\uff1b`decidePage`\uff1a ok \u21d2 \u8f7d\u9875 \u00b7 \u975e ok \u21d2 \u4eba\u8bdd\uff0b\u53bb\u5904\uff08`shell.log`\uff09\u3002
  S3 \u771f HTTP \u4e4b\u6b63\u53cd\u63a7\uff08node \u53f0\u67b6\uff09\uff1a\u4e8c\u6869\u4e8e `127.0.0.1:0`\uff08\u540c\u6839 \u2044 \u5f02\u6839\uff09\u21d2 `probeHealthAt` \u21d2 \u9010\u5b57\u5f97\u5224\u3002
"""
from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SHELL = ROOT / "shell"
IDJS = SHELL / "identity.js"
MAIN = SHELL / "main.js"
PKG = SHELL / "package.json"


def _read(p: Path) -> str:
    return io.open(str(p), encoding="utf-8").read()


def _node(src: str) -> dict:
    r = subprocess.run(["node", "-e", src], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120, cwd=str(SHELL))
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    return json.loads((r.stdout or "").strip().splitlines()[-1])


# ---------- S1 \u4e00\u5904\u5b9a\u5f62 \u00b7 \u7eaf node ----------

def test_S1_identity_js_pure_and_referenced_once():
    t = _read(MAIN)
    assert t.count(u"require('./identity')") == 1, u"\u8eab\u4efd\u4e4b\u5224\u987b\u552f 1 \u5904\u5f15"
    d = _read(IDJS)
    assert u"require('electron')" not in d, u"identity.js \u987b\u7eaf node\uff08\u4f9b\u53f0\u67b6\u76f4\u6d4b\uff09"
    for bad in (u"https://", u"0.0.0.0", u"fetch(", u"XMLHttpRequest"):
        assert bad not in d, u"identity.js \u26d4 \u5f97\u542b " + bad
    assert u"host: '127.0.0.1'" in d, u"\u63a2\u6d3b\u987b\u552f 127.0.0.1"
    pkg = json.loads(_read(PKG))
    assert u"identity.js" in pkg["build"]["files"], u"\u987b\u5165\u58f3\uff08\u5426\u5219 \u26d4 \u5165 app.asar\uff09"


def test_S1b_main_page_load_is_single_place_and_gated():
    t = _read(MAIN)
    assert u"function createWindow(msg) {" in t, u"\u9875\u4e4b\u8f7d\u987b\u7ecf\u4e00\u5904\uff08\u53d7\u8eab\u4efd\u4e4b\u5224\u4e4b\u7ba1\uff09"
    assert u"if (msg) { win.loadURL(msgPageHtml(" in t, u"\u975e\u672c\u8f7d\u8377 \u21d2 \u4eba\u8bdd\u4e4b\u9875\uff08\u26d4 \u8f7d\u8f7d\u8377\u4e4b\u9875\uff09"
    assert u"IDENTITY && !IDENTITY.ok" in t, u"reload \u987b\u53d7\u8eab\u4efd\u4e4b\u7ba1"


# ---------- S2 \u7eaf\u51fd ----------

_HARNESS = u"""
const ID = require('./identity.js');
const W = 'D:\\\\a\\\\version.json';
const h = (o) => JSON.stringify(o);
const out = {};
out.same      = ID.evaluateHealth(h({build:{available:true,path:'D:\\\\a\\\\version.json'}}), W);
out.foreign   = ID.evaluateHealth(h({build:{available:true,path:'D:\\\\OTHER\\\\version.json'}}), W);
out.nobuild   = ID.evaluateHealth(h({version:'9.0.0'}), W);
out.unavail   = ID.evaluateHealth(h({build:{available:false,path:'D:\\\\a\\\\version.json'}}), W);
out.sep_case  = ID.evaluateHealth(h({build:{available:true,path:'d:/A/version.json'}}), W);
out.notjson   = ID.evaluateHealth('not-json', W);
out.dec_ok    = ID.decidePage({ok:true});
out.dec_ng    = ID.decidePage({ok:false,why:'foreign-root',got:'D:\\\\OTHER\\\\version.json',want:W});
console.log(JSON.stringify(out));
"""


def test_S2_pure_functions_positive_and_negative():
    u = _node(_HARNESS)
    assert u["same"]["ok"] is True, u["same"]
    assert u["foreign"]["ok"] is False and u["foreign"]["why"] == "foreign-root", u["foreign"]
    assert u["nobuild"]["ok"] is False and u["nobuild"]["why"] == "no-build-\u952e", u["nobuild"]
    assert u["unavail"]["ok"] is False, u["unavail"]
    assert u["sep_case"]["ok"] is True, u["sep_case"]
    assert u["notjson"]["ok"] is False, u["notjson"]
    assert u["dec_ok"]["load"] == "page", u["dec_ok"]
    m = u["dec_ng"]["msg"]
    assert u["dec_ng"]["load"] == "msg", u["dec_ng"]
    assert u"\u672c\u673a\u5df2\u6709\u4e00\u4e2a PA \u5728\u8dd1" in m[0], m
    assert u"shell.log" in m[3], m


# ---------- S3 \u771f HTTP ----------

_HTTP = u"""
const ID = require('./identity.js');
const http = require('http');
const W = 'D:\\\\a\\\\version.json';
function stub(path) {
  return new Promise((res) => {
    const s = http.createServer((q, r) => {
      r.writeHead(200, {'Content-Type':'application/json'});
      r.end(JSON.stringify({status:'healthy', version:'9.0.0', build:{available:true, path:path}}));
    });
    s.listen(0, '127.0.0.1', () => res({s, port:s.address().port}));
  });
}
(async () => {
  const a = await stub('D:\\\\a\\\\version.json');
  const b = await stub('D:\\\\OTHER\\\\version.json');
  const out = {};
  out.same = await ID.probeHealthAt(a.port).then((h) => ID.evaluateHealth(h.body, W));
  out.foreign = await ID.probeHealthAt(b.port).then((h) => ID.evaluateHealth(h.body, W));
  out.dead = await ID.probeHealthAt(9).then((h) => ID.evaluateHealth(h.body, W));
  a.s.close(); b.s.close();
  console.log(JSON.stringify(out));
})();
"""


@pytest.mark.skipif(not (SHELL / "identity.js").is_file(), reason="\u65e0 identity.js")
def test_S3_real_http_positive_and_negative():
    u = _node(_HTTP)
    assert u["same"]["ok"] is True, u["same"]
    assert u["foreign"]["ok"] is False and u["foreign"]["why"] == "foreign-root", u["foreign"]
    assert u["foreign"]["got"].endswith(u"OTHER\\version.json"), u["foreign"]
    assert u["dead"]["ok"] is False, u["dead"]