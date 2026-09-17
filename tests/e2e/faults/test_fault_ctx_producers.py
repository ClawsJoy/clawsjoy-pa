# -*- coding: utf-8 -*-
"""ctx 生产端接入验收（2026-09-13 批79），纯函数层。从真实 pa.html 抽定义（体检项 45）。"""
import subprocess


def _extract():
    s = open("web/pa.html", encoding="utf-8").read()
    i = s.find("const ACTION_SEMANTIC={")
    j = s.find("\n};", i)
    table = s[i : j + 3].replace("const ACTION_SEMANTIC=", "var ACTION_SEMANTIC=", 1)
    i = s.find("function semanticArg(tool, arg){")
    j = s.find("\n}", i)
    sarg = s[i : j + 2]
    i = s.find("function semanticStage(tool, arg, ctx){")
    j = s.find("/* ctx 采集", i)
    sstg = s[i:j]
    i = s.find("function semanticCtx(tool, arg){")
    j = s.find("  return c;\n}", i)
    sctx = s[i : j + len("  return c;\n}")]
    return table + "\n" + sarg + "\n" + sstg + "\n" + sctx + "\n"


def _run(body):
    code = _extract() + "\n" + body
    open("/tmp/_ctx_probe.js", "w", encoding="utf-8").write(code)
    return subprocess.run(["node", "/tmp/_ctx_probe.js"], capture_output=True, text=True)


def test_plan_step_reaches_semanticCtx():
    """计划步骤写入后 semanticCtx 能读到 → 语义串带「第 N/M 步」"""
    r = _run(
        """
_planStepIndex = 2; _planStepTotal = 5;
const c = semanticCtx();
if(c.stepIndex !== 2 || c.stepTotal !== 5) throw new Error('semanticCtx 未读到步骤: ' + JSON.stringify(c));
const out = semanticStage('wpp_render_full_deck','{"page_index":3}', c);
if(!out || out.indexOf('第 2/5 步') < 0) throw new Error('未带步骤: ' + out);
console.log('步骤OK ctx=' + JSON.stringify(c) + ' out=' + out);
"""
    )
    assert r.returncode == 0, r.stderr + r.stdout
    print("用例1:", r.stdout.strip())


def test_deck_reaches_semanticCtx():
    """PPT_DECK 写入后 semanticCtx 能读到 → 无页码时用 deck 兜底"""
    r = _run(
        """
_planStepIndex = 0; _planStepTotal = 0; PPT_DECK = 'V6讲义_14页.pptx';
const c = semanticCtx();
if(c.deck !== 'V6讲义_14页.pptx') throw new Error('semanticCtx 未读到 deck: ' + JSON.stringify(c));
const out = semanticStage('wpp_render_full_deck','{}', c);
if(!out || out.indexOf('V6讲义') < 0) throw new Error('deck 兜底失效: ' + out);
console.log('deckOK ctx=' + JSON.stringify(c) + ' out=' + out);
"""
    )
    assert r.returncode == 0, r.stderr + r.stdout
    print("用例2:", r.stdout.strip())


def test_still_falls_back_when_empty():
    """回落不回归：生产端没写时 ctx 仍空、仍回落固定短语"""
    r = _run(
        """
_planStepIndex = 0; _planStepTotal = 0; PPT_DECK = '';
const c = semanticCtx();
if(semanticStage('wpp_render_full_deck','{}', c) !== null) throw new Error('空 ctx 应回落');
const chain = semanticStage('read_file','',c) || semanticArg('read_file','') || ACTION_SEMANTIC['read_file'] || '执行操作';
if(chain !== (ACTION_SEMANTIC['read_file'] || '执行操作')) throw new Error('兜底链回归: ' + chain);
console.log('回落OK ctx=' + JSON.stringify(c) + ' chain=' + chain);
"""
    )
    assert r.returncode == 0, r.stderr + r.stdout
    print("用例3:", r.stdout.strip())
