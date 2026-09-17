# -*- coding: utf-8 -*-
"""断点②修验收（2026-09-13 批85）：目录类 arg 不再回落。从真实 pa.html 抽定义（体检项 45）。"""
import subprocess


def _extract():
    s = open("web/pa.html", encoding="utf-8").read()
    i = s.find("const ACTION_SEMANTIC={")
    j = s.find("\n};", i)
    out = s[i : j + 3].replace("const ACTION_SEMANTIC=", "var ACTION_SEMANTIC=", 1) + "\n"
    i = s.find("function semanticArg(tool, arg){")
    j = s.find("\n}", i)
    out += s[i : j + 2] + "\n"
    i = s.find("function semanticStage(tool, arg, ctx){")
    j = s.find("/* ctx 采集", i)
    out += s[i:j]
    return out


def _run(body):
    open("/tmp/_dir_probe.js", "w", encoding="utf-8").write(_extract() + "\n" + body)
    return subprocess.run(["node", "/tmp/_dir_probe.js"], capture_output=True, text=True)


def test_1_dir_arg_no_longer_null():
    """用例1：目录类 arg → 返回「查看目录 X」而非 null"""
    r = _run(
        """
const c = {};
const out = semanticStage('list_dir', 'data/reports', c);
if(out === null) throw new Error('目录类 arg 仍回落');
if(out.indexOf('查看目录') < 0) throw new Error('语义不对: ' + out);
if(out.indexOf('data/reports') < 0) throw new Error('未引用 arg 原文: ' + out);
const out2 = semanticStage('list_dir', 'data/reports', {stepIndex:1, stepTotal:4});
if(out2.indexOf('第 1/4 步') < 0) throw new Error('未带步骤: ' + out2);
console.log('用例1 OK -> ' + out + ' || ' + out2);
"""
    )
    assert r.returncode == 0, r.stderr + r.stdout
    print(r.stdout.strip())


def test_2_file_arg_unchanged():
    """用例2：文件类 arg → 仍返回「读取 X」（不被新分支抢走）"""
    r = _run(
        """
const out = semanticStage('read_file', 'data/reports/_probe3.md', {});
if(!out || out.indexOf('读取') < 0 || out.indexOf('_probe3.md') < 0) throw new Error('文件类回归: ' + out);
console.log('用例2 OK -> ' + out);
"""
    )
    assert r.returncode == 0, r.stderr + r.stdout
    print(r.stdout.strip())


def test_3_others_still_fall_back():
    """用例3：其他 → 仍回落；空 arg 仍 null；长文本仍截断"""
    r = _run(
        """
if(semanticStage('read_file','',{}) !== null) throw new Error('空 arg 应回落');
if(semanticStage('list_dir','',{}) !== null) throw new Error('空 arg 目录应回落');
if(semanticStage('web_search','',{}) !== null) throw new Error('空 arg 搜索应回落');
if(semanticStage('unknown_tool_xyz','',{}) !== null) throw new Error('未知工具应回落');
const long = 'data/' + 'a'.repeat(200);
const out = semanticStage('list_dir', long, {});
if(out.length > 80) throw new Error('未截断: ' + out.length);
const chain = semanticStage('read_file','',{}) || semanticArg('read_file','') || ACTION_SEMANTIC['read_file'] || '执行操作';
if(chain !== (ACTION_SEMANTIC['read_file'] || '执行操作')) throw new Error('兜底回归: ' + chain);
console.log('用例3 OK len=' + out.length + ' chain=' + chain);
"""
    )
    assert r.returncode == 0, r.stderr + r.stdout
    print(r.stdout.strip())
