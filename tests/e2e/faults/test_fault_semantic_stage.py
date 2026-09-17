# -*- coding: utf-8 -*-
"""故障注入 #18：带上下文的语义阶段（2026-09-13 批78，选项 a）。

第一段：纯函数验收，**不需浏览器**。
**用被改的对象本身**（web/pa.html）抽取函数后跑 —— 体检项 45。
"""
import json
import os
import re
import subprocess
import sys

import pytest

PA = "web/pa.html"


def _extract_js():
    """从真实的 web/pa.html 里抽出三个定义（move 而非 retype）。"""
    s = open(PA, encoding="utf-8").read()
    out = {}

    i = s.find("const ACTION_SEMANTIC={")
    j = s.find("\n};", i)
    assert i > 0 and j > i, "未找到 ACTION_SEMANTIC"
    out["table"] = s[i : j + 3].replace("const ACTION_SEMANTIC=", "var ACTION_SEMANTIC=", 1)

    i = s.find("function semanticArg(tool, arg){")
    j = s.find("\n}", i)
    assert i > 0 and j > i, "未找到 semanticArg"
    out["semanticArg"] = s[i : j + 2]

    i = s.find("function semanticStage(tool, arg, ctx){")
    j = s.find("/* ctx 采集", i)
    assert i > 0 and j > i, "未找到 semanticStage"
    out["semanticStage"] = s[i:j]
    return out


def _run_node(body):
    js = _extract_js()
    code = js["table"] + "\n" + js["semanticArg"] + "\n" + js["semanticStage"] + "\n" + body
    p = "/tmp/_sem_stage_probe.js"
    open(p, "w", encoding="utf-8").write(code)
    r = subprocess.run(["node", p], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r


def test_1_context_page_and_step():
    """用例1：wpp_render_full_deck(page=3) + 计划步骤 + 页标题 → 「第 2/5 步：渲染第 3 页：三个台阶」"""
    r = _run_node(
        """
const ctx = {stepIndex:2, stepTotal:5, pageTitle:'三个台阶'};
const out = semanticStage('wpp_render_full_deck', '{"page_index":3}', ctx);
console.log(out);
if(!out || out.indexOf('第 3 页') < 0) throw new Error('缺页码: ' + out);
if(out.indexOf('三个台阶') < 0) throw new Error('缺页标题: ' + out);
if(out.indexOf('第 2/5 步') < 0) throw new Error('缺步骤归属: ' + out);
"""
    )
    assert r.returncode == 0, r.stderr + r.stdout
    print("用例1 输出:", r.stdout.strip())


def test_2_fallback_no_regression():
    """用例2：上下文取不到 → 必须回落固定短语，**不能空串、不能抛错**（风险1）。"""
    r = _run_node(
        """
const cases = [
  ['wpp_render_full_deck', ''],
  ['read_file', ''],
  ['web_search', ''],
  ['unknown_tool_xyz', '']
];
for(const [t,a] of cases){
  const v = semanticStage(t, a, {});
  if(v !== null) throw new Error('应回落为 null 但得到: ' + JSON.stringify(v) + ' tool=' + t);
}
const chain = semanticStage('read_file','',{}) || semanticArg('read_file','') || ACTION_SEMANTIC['read_file'] || '执行操作';
if(chain !== (ACTION_SEMANTIC['read_file'] || '执行操作')) throw new Error('兜底链回归: ' + chain);
const chain2 = semanticStage('unknown_tool_xyz','',{}) || ACTION_SEMANTIC['unknown_tool_xyz'] || '执行操作';
if(chain2 !== '执行操作') throw new Error('未知工具兜底回归: ' + chain2);
console.log('回落OK chain=' + chain + ' chain2=' + chain2);
"""
    )
    assert r.returncode == 0, r.stderr + r.stdout
    print("用例2 输出:", r.stdout.strip())


def test_3_missing_manifest_and_long_text():
    """用例3：缺 manifest/页标题 降级 + 长文本截断（风险2/3）+ 异常不抛。"""
    r = _run_node(
        """
// 缺 manifest：无 deck、无 pageTitle → 回落
if(semanticStage('wpp_render_full_deck','{}',{}) !== null) throw new Error('缺上下文应回落');
// 有 deck 无页标题 → 用 deck 兜底
const withDeck = semanticStage('wpp_render_full_deck','{}',{deck:'V6讲义_14页.pptx'});
if(!withDeck || withDeck.indexOf('V6讲义') < 0) throw new Error('deck 兜底失效: ' + withDeck);
// 长文本截断：标题 100 字 → 输出长度必须有限（日志不爆）
const long = '一二三四五六七八九十'.repeat(10);
const out = semanticStage('wpp_render_full_deck','{"page_index":3}',{pageTitle:long});
if(out.length > 80) throw new Error('未截断，长度=' + out.length);
if(out.indexOf('…') < 0) throw new Error('未见截断标记');
// 异常不抛：ctx 塞入会炸 getter 的对象
const bomb = {}; Object.defineProperty(bomb,'stepIndex',{get(){ throw new Error('boom'); }});
const v = semanticStage('read_file','a.md',bomb);
if(v === undefined) throw new Error('异常未回落');
console.log('降级OK len=' + out.length + ' bomb=' + JSON.stringify(v));
"""
    )
    assert r.returncode == 0, r.stderr + r.stdout
    print("用例3 输出:", r.stdout.strip())
