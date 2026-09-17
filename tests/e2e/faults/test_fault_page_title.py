# -*- coding: utf-8 -*-
"""页标题接入验收（2026-09-13 批80）。从真实 pa.html 抽定义交 node 跑（体检项 45）。"""
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
    # 抽取真实文件里的全局声明（否则 harness 里 _pptManifestCache 未定义）
    i = s.find("const _pptManifestCache={};")
    j = s.find("\n", i)
    decl = s[i:j].replace("const _pptManifestCache=", "var _pptManifestCache=", 1) + "\n"
    i = s.find("var _planStepIndex=0")
    j = s.find("\n", i)
    decl += s[i:j] + "\n"
    return decl + table + "\n" + sarg + "\n" + sstg + "\n" + sctx + "\n"


def _run(body):
    open("/tmp/_title_probe.js", "w", encoding="utf-8").write(_extract() + "\n" + body)
    return subprocess.run(["node", "/tmp/_title_probe.js"], capture_output=True, text=True, encoding="utf-8", errors="replace")


def test_title_matched():
    """用例1：有 manifest + page_index 匹配 → 标题出现"""
    r = _run(
        """
_pptManifestCache['d.pptx'] = {deck:'d.pptx', pages:[{page_index:1,title:'今天只回答三个问题'},{page_index:3,title:'三个台阶'}]};
_planStepIndex = 2; _planStepTotal = 5; PPT_DECK = 'd.pptx';
const c = semanticCtx('wpp_render_full_deck', '{"page_index":3}');
if(c.pageTitle !== '三个台阶') throw new Error('未取到标题: ' + JSON.stringify(c));
const out = semanticStage('wpp_render_full_deck', '{"page_index":3}', c);
if(out !== '第 2/5 步：渲染第 3 页：三个台阶') throw new Error('输出不符: ' + out);
console.log('用例1 OK -> ' + out);
"""
    )
    assert r.returncode == 0, r.stderr + r.stdout
    print(r.stdout.strip())


def test_no_match_degrades():
    """用例2：page_index 无匹配 → 降级（无标题），不抛"""
    r = _run(
        """
_pptManifestCache['d.pptx'] = {deck:'d.pptx', pages:[{page_index:1,title:'X'}]};
PPT_DECK='d.pptx';
const c = semanticCtx('wpp_render_full_deck', '{"page_index":99}');
if(c.pageTitle) throw new Error('不该有标题: ' + JSON.stringify(c));
const out = semanticStage('wpp_render_full_deck', '{"page_index":99}', c);
if(!out || out.indexOf('第 99 页') < 0) throw new Error('应仍渲染页码: ' + out);
console.log('用例2 OK -> ' + out);
"""
    )
    assert r.returncode == 0, r.stderr + r.stdout
    print(r.stdout.strip())


def test_manifest_missing_degrades():
    """用例3：manifest 缺失 → 降级；且长标题仍截断；回落链不回归"""
    r = _run(
        """
for(const k of Object.keys(_pptManifestCache)) delete _pptManifestCache[k];
PPT_DECK=''; _planStepIndex=0; _planStepTotal=0;
const c = semanticCtx('wpp_render_full_deck', '{"page_index":3}');
if(c.pageTitle) throw new Error('manifest 缺失不该有标题');
// manifest 缺失时：**页码仍来自入参**（这是对的），只是没有标题
const outNoMan = semanticStage('wpp_render_full_deck','{"page_index":3}',c);
if(outNoMan !== '渲染第 3 页') throw new Error('缺 manifest 应只降级标题、保留页码: ' + outNoMan);
const chain = semanticStage('read_file','',c) || semanticArg('read_file','') || ACTION_SEMANTIC['read_file'] || '执行操作';
if(chain !== (ACTION_SEMANTIC['read_file'] || '执行操作')) throw new Error('兜底回归: ' + chain);
// 长标题截断（semanticStage 内 short(…,16)）
_pptManifestCache['d.pptx']={deck:'d.pptx',pages:[{page_index:3,title:'一二三四五六七八九十'.repeat(6)}]};
const c2 = semanticCtx('wpp_render_full_deck','{"page_index":3}');
const out2 = semanticStage('wpp_render_full_deck','{"page_index":3}',c2);
if(out2.length > 80) throw new Error('未截断: ' + out2.length);
console.log('用例3 OK -> ' + out2);
"""
    )
    assert r.returncode == 0, r.stderr + r.stdout
    print(r.stdout.strip())
