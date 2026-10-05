# -*- coding: utf-8 -*-
"""门：Step4 内容核验**判据面收窄**（2026-09-20 · DSH 修 · DS 769/775 裁）。

触发（实测）：A3「建会话即 seed」之后，`collect_written_files` 把**整个沙箱**（实测 5,035 件）
当「写入面」⇒ 旧 Step4 对**每一件**都要求命中任务关键词 ⇒ 连 `config/.env`、`README.md`、
`_diag5.txt` 都被要求含「项目盘点」⇒ **必然全红（假红）**。

裁定的新口径：① `_kws` 空 ⇒ **不判**；② 只对**任务相关产物**判；③ 其余只计数不判；
④ 相关产物**照旧要求命中**（判据有齿）。

该红格＋对照的对照：P2（全库无关）在**旧口径**下必红，在新口径下必绿 ⇒ 影子失配 > 0。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.lib.verification_chain import content_verify  # noqa: E402


def _f(tmp_path, name, text):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')
    return {'path': name, 'absolute': p}


def _old_scope(files, kws):
    """旧口径（全量逐件判）：复现修前行为，作**对照的对照**。"""
    for f in files:
        c = Path(f['absolute']).read_text(encoding='utf-8')
        need = max(1, len(kws) // 2)
        if sum(1 for k in kws if k in c) < need:
            return False
    return True


def test_relevant_artifact_with_keyword_passes(tmp_path):
    files = [_f(tmp_path, '项目盘点报告.md', '# 项目盘点\n本报告为项目盘点结论')]
    r = content_verify(files, task_goal='项目盘点', base_dir=tmp_path)
    assert r['passed'] is True, r


def test_relevant_artifact_without_keyword_fails(tmp_path):
    """该红格：相关产物**缺关键词** ⇒ 必须红（判据有齿）。"""
    files = [_f(tmp_path, '项目盘点报告.md', '# 结论\n内容与关键词无关')]
    r = content_verify(files, task_goal='项目盘点', base_dir=tmp_path)
    assert r['passed'] is False, r


def test_irrelevant_whole_tree_no_longer_red(tmp_path):
    """修前恒红的那一格：全库无关文件 ⇒ 新口径**只计不判**（不再假红）。"""
    files = [_f(tmp_path, 'core/mod_%d.py' % i, 'x = %d' % i) for i in range(200)]
    r = content_verify(files, task_goal='项目盘点', base_dir=tmp_path)
    assert r['passed'] is True, r
    assert r['skipped_irrelevant'] == 200, r
    kws = ['项目盘点']
    assert _old_scope(files, kws) is False, '对照的对照：旧口径应对这格必红'


def test_empty_keywords_not_judged(tmp_path):
    """空不判：任务目标取不出关键词 ⇒ 返回 passed=True 且带说明。"""
    files = [_f(tmp_path, 'x.md', 'anything')]
    r = content_verify(files, task_goal='', base_dir=tmp_path)
    assert r['passed'] is True and '空不判' in str(r.get('skipped')), r

def test_empty_keywords_still_fails_empty_file(tmp_path):
    """该红格（v2 补）：**空不判 ≠ 结构不判** —— 取不出关键词时，**空文件仍须失败**。

    反例来源：v1 把「空不判」实现成**整个判据早退** ⇒ 连「文件不存在／读取失败／内容为空」
    三条结构防线一起跳过 ⇒ 被**既有用例** tests/integration/test_subtask_verify_fix.py::
    test_content_verify_empty_still_fails 抓红（全量门实测：2 failed / 1929 passed）。
    """
    files = [_f(tmp_path, 'output.md', '')]
    r = content_verify(files, task_goal='写文件 output.md 内容为数据', base_dir=tmp_path)
    assert r['passed'] is False, r
    assert any('空' in str(x.get('error', '')) for x in r['failed']), r['failed']
