# -*- coding: utf-8 -*-
"""PM-011 前置件 · 顶栏权限徽标「三态」门（2026-09-30 · CW b2a5182）。

病（PM 裁定原文）：`permission.json` 与 `boss_grant.json` **都不存在**，顶栏却显示
「权限: 标准」⇒ **默认值假装成读数**（与 437 假绿 ／ 验收-B「过期 0」／ `_jsonl_lines` 的 `0` 同族）。

判据（PM §三，逐条）：
  J1  ②③ 文件均不存在 ⇒ 顶栏**必须出现「未授予」**，且 ⛔ 不得只显示「标准」；
  J2  存在**真实**授予文件 ⇒ 文案**必须含来源路径**；
  J3  读不到 ⇒ 文案**与 ⒜⒝ 均不相同**。
反例门：删/挪授予文件 ⇒ 顶栏**必须**从 ⒜ 变 ⒝（⛔ 不许停在一个像读数的「标准」）。

本件**不复制代码**：前端判据从 `web/pa.html` 原文抽出 `paPermBadge` 用 node 真跑；
后端判据走**真路由**（Flask test_client ＋ 临时 PA_DATA_DIR），⛔ 不 mock 掉被审对象。
"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
PA = ROOT / "web" / "pa.html"
SCRATCH = ROOT / "data" / "tmp" / "_pm011_badge"
UNDEF = "__UNDEF__"        # JSON 表达不出 undefined ⇒ 具名哨兵

G_NOFILE = {"pa": {"path": "data\\v9\\pa\\permission.json", "exists": False},
            "pes": {"path": "data\\v9\\pes\\boss_grant.json", "exists": False}}
G_PA_FILE = {"pa": {"path": "data\\v9\\pa\\permission.json", "exists": True},
             "pes": {"path": "data\\v9\\pes\\boss_grant.json", "exists": False}}
G_BOTH = {"pa": {"path": "data\\v9\\pa\\permission.json", "exists": True},
          "pes": {"path": "data\\v9\\pes\\boss_grant.json", "exists": True}}


# 判据正文只写一处，测试与齿共用同一条断言（⛔ 不写两份 ⇒ 免漂移）
def _j1_ok(text: str) -> bool:
    return ("未授予" in text) and ("默认档" in text) and (not text.startswith("权限: 标准"))


def _j2_ok(text: str, path: str) -> bool:
    return path in text


def _j3_ok(unread: str, a: str, b: str) -> bool:
    return ("面不可读" in unread) and (unread != a) and (unread != b)


def _pa() -> str:
    return io.open(PA, encoding="utf-8").read()


def _fn(src: str, name: str) -> str:
    """按花括号配平抽出 `function name(...){...}` 原文。"""
    i = src.find("function " + name + "(")
    assert i > 0, "未找到函数 " + name
    d, opened, e = 0, False, i
    while e < len(src):
        c = src[e]
        if c == "{":
            d += 1
            opened = True
        elif c == "}":
            d -= 1
            if opened and d == 0:
                return src[i:e + 1]
        e += 1
    raise AssertionError("函数 " + name + " 花括号不配平")


def _render(cases: dict, fn_src: str = None) -> dict:
    """cases: name -> [modePerm, level, grant, err]（err 用 UNDEF 表示 undefined）。"""
    fn = fn_src if fn_src is not None else _fn(_pa(), "paPermBadge")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    js = (fn + "\n"
          "const SCEN=" + json.dumps(cases, ensure_ascii=False) + ";\n"
          "const out={};\n"
          "for(const k of Object.keys(SCEN)){const a=SCEN[k];"
          " out[k]=paPermBadge(a[0],a[1],a[2],(a[3]===" + json.dumps(UNDEF) + "?undefined:a[3]));}\n"
          "console.log(JSON.stringify(out));\n")
    f = SCRATCH / "badge_harness.js"
    io.open(f, "w", encoding="utf-8", newline="\n").write(js)
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    r = subprocess.run([exe, str(f)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, "node 失败 rc=%s\n%s" % (r.returncode, r.stderr[-600:])
    return json.loads(r.stdout.strip().splitlines()[-1])


# ============================ 前端：三态 ============================

def test_j1_no_grant_file_must_say_not_granted():
    t = _render({"nofile": ["标准", "标准", G_NOFILE, None]})["nofile"]
    assert _j1_ok(t), "J1：②③ 都不存在，顶栏竟没说「未授予（默认档）」：%r" % t


def test_j2_real_file_must_show_source_path():
    t = _render({"pafile": ["标准", "只读", G_PA_FILE, None]})["pafile"]
    assert _j2_ok(t, G_PA_FILE["pa"]["path"]), "J2：有真文件却不给来源路径：%r" % t
    assert "只读" in t, "J2：该档要取后端给的 level：%r" % t


def test_j2b_both_files_are_listed_without_merging():
    """两处授予**语义不同**（PM §四）⇒ 都在就都要列出来，⛔ 不合并成一个数。"""
    t = _render({"both": ["标准", "标准", G_BOTH, None]})["both"]
    assert _j2_ok(t, G_BOTH["pa"]["path"]) and _j2_ok(t, G_BOTH["pes"]["path"])


def test_j3_unreadable_differs_from_a_and_b():
    out = _render({"nofile": ["标准", "标准", G_NOFILE, None],
                   "pafile": ["标准", "标准", G_PA_FILE, None],
                   "unread": ["标准", None, None, "pa_state_corrupt"]})
    assert _j3_ok(out["unread"], out["pafile"], out["nofile"]), \
        "J3：读不到要标「面不可读」且与 ⒜/⒝ 均不同：%r" % out["unread"]


def test_pending_state_is_not_pretending_to_be_a_reading():
    """请求还没回来时，⛔ 不许先显示一个像读数的档位。"""
    t = _render({"pending": ["标准", None, None, UNDEF]})["pending"]
    assert "权限: 标准" not in t, "还没取到就显示了档位：%r" % t


# ============================ 反例门（删/挪授予文件） ============================

def test_neg_flip_file_present_to_absent_changes_badge():
    """反例门：文件在 ⇒ ⒜；文件挪走 ⇒ **必须**变 ⒝。⛔ 不许两边同一句。"""
    out = _render({"present": ["标准", "标准", G_PA_FILE, None],
                   "absent": ["标准", "标准", G_NOFILE, None]})
    present, absent = out["present"], out["absent"]
    assert present != absent, "反例失效：文件在不在，顶栏文案一样"
    assert _j2_ok(present, G_PA_FILE["pa"]["path"])
    assert _j1_ok(absent)


def test_neg_teeth_mutant_without_not_granted_is_caught():
    """齿：把「未授予」从**判据函数体**里挖掉 ⇒ **J1 必须判红**（⛔ 不是「挖了还能过」）。"""
    src = _fn(_pa(), "paPermBadge")
    mutant = src.replace("未授予", "标准")
    assert mutant != src, "改不动 ⇒ 这条齿是假的"
    t = _render({"nofile": ["标准", "标准", G_NOFILE, None]}, fn_src=mutant)["nofile"]
    assert not _j1_ok(t), "齿失效：挖掉「未授予」，J1 竟然还过（判据没真依赖它）"


def test_static_badge_no_longer_hardcodes_mode_perm():
    src = _pa()
    assert "$('modePerm').textContent = '权限: '+cfg.perm" not in src, "旧写法还在（默认值当读数）"
    assert "function paPermBadge(" in src and "function fetchPaGrant(" in src
    assert "fetchPaGrant();" in src, "loadCfg 没接上新取数"


def test_static_abort_is_not_silently_swallowed():
    """PM §五：`catch` 必须**分流** AbortError，⛔ 不许与其他异常一起吞。"""
    src = _pa()
    assert "if(e.name!=='AbortError'){ addMsg('assistant','⚠ 连不上后端" not in src, "还是统一吞"
    assert "e.name==='AbortError'" in src and "paSetState('stopped'" in src


# ============================ 后端：真路由的来源面 ============================

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    (tmp_path / "pa").mkdir(parents=True, exist_ok=True)
    app = Flask(__name__)
    from core.pa.gateway_routes import register_pa_routes
    register_pa_routes(app)
    return app.test_client()


def test_route_reports_absent_files_as_absent(client):
    d = client.get("/v9/pa/permission").get_json()
    assert d["ok"] is True and d["level"] == "标准", "level 契约不许动"
    g = d["grant"]
    assert g["pa"]["exists"] is False, "没有文件却说有 ⇒ 这就是「默认值假装成读数」"
    assert g["pes"]["exists"] is False
    assert g["pa"]["path"] and g["pes"]["path"], "必须给路径（前端要显示来源）"


def test_route_反例门_写文件后_exists_必须翻面(client, tmp_path):
    """真反例门：**写一个真授予文件** ⇒ exists 必须 True；删掉 ⇒ 必须回 False。"""
    p = tmp_path / "pa" / "permission.json"
    p.write_text(json.dumps({"level": "只读"}), encoding="utf-8")
    d = client.get("/v9/pa/permission").get_json()
    assert d["grant"]["pa"]["exists"] is True, "文件真在盘上，exists 却是 False"
    assert d["level"] == "只读", "该档要跟着生效值走"

    p.unlink()
    d2 = client.get("/v9/pa/permission").get_json()
    assert d2["grant"]["pa"]["exists"] is False
    assert d2["level"] == "标准"


def test_route_corrupt_still_409_not_200(client, tmp_path):
    """承既有钉死的契约（X-16）：坏状态回 409 ＋ 可读提示，⛔ 不是 200 假绿。"""
    p = tmp_path / "pa" / "permission.json"
    p.write_text("{ 半截", encoding="utf-8")
    r = client.get("/v9/pa/permission")
    assert r.status_code == 409, "坏状态不得回 200"
    d = r.get_json()
    assert d["ok"] is False and d["error"] == "pa_state_corrupt"
    assert d.get("message") and d.get("hint")