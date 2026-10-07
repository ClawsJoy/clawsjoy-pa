# -*- coding: utf-8 -*-
"""种子闸接线门（老板裁 2026-09-29「甲」案 · 判据升格）。

判据：凡「要 X 在场才放行」的闸 ⇒ ① X 必须有**生产写入方** ② 必须有**反例门**（未接线即判红）。
反例（本门要治的真事）：`sandbox_seed.seed_sandbox` 长期**零调用者** ⇒ 闸在、口不在 ⇒
  每个会话每个回合被短路 ⇒ 前端「服务暂不可用」＋无回执（2026-09-29 一手实测）。

夹具说明：⛔ 不用 pytest 的 `tmp_path`（本机 %TEMP%\\pytest-of-<user> 拒绝访问，WinError 5）；
  改用仓内 `data/tmp/` 下自建 scratch，用例结束只清**本用例自建**的目录。
"""
import io
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRATCH = ROOT / 'data' / 'tmp'


def _src(rel):
    return io.open(ROOT / rel, encoding='utf-8').read()


@pytest.fixture
def workdir():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix='seedgate_test_', dir=str(SCRATCH)))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_entry_wires_seed_on_create():
    """① 生产写入方：回合入口必须调用 ensure_seeded（未接线 ⇒ 红）。"""
    s = _src('core/gateway/v9_chat/entry.py')
    assert 'seed_on_create import ensure_seeded' in s, '回合入口未接 ensure_seeded ⇒ seed 闸将全线拦'
    assert '_ensure_seeded(' in s, '接了 import 却没调用 ⇒ 红'


def test_seed_sandbox_has_production_caller():
    """② 播种器必须有生产调用方（仅定义、无调用 ⇒ 红）。"""
    s = _src('core/gateway/seed_on_create.py')
    assert 'seed_sandbox(' in s, 'seed_sandbox 无生产调用方 ⇒ 闸在口不在'


def test_gate_blocks_unseeded(workdir):
    """反例：未 seed ⇒ 必拦（fail-closed）。"""
    from core.gateway.sandbox_seed import check_seed, task_entry_gate
    sb = workdir / 'u' / 's' / 'clawsjoy_dev'
    sb.mkdir(parents=True)
    assert check_seed(sb)['ok'] is False
    g = task_entry_gate('u', 's', root=str(workdir))
    assert g['allowed'] is False and g['status'] == 'blocked'


def _fake_source(workdir):
    src = workdir / 'src'
    for rel in ('core/a.py', 'web/b.js', 'tools/c.bin'):
        p = src / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('x=1\n', encoding='utf-8')
    (src / 'README.md').write_text('# demo\n', encoding='utf-8')
    return src


def test_seed_then_gate_allows_and_tool_excluded(workdir):
    """正例：播种后放行；且 SEED_EXCLUDE 生效（tools 不入沙箱）。"""
    from core.gateway.sandbox_seed import check_seed, seed_sandbox, task_entry_gate
    src = _fake_source(workdir)
    sb = workdir / 'u' / 's' / 'clawsjoy_dev'
    seed_sandbox(sb, src, commit='t')
    assert (sb / 'core' / 'a.py').exists()
    assert not (sb / 'tools').exists(), 'SEED_EXCLUDE 未生效（tools 被拷进沙箱）'
    assert check_seed(sb)['ok'] is True
    assert task_entry_gate('u', 's', root=str(workdir))['allowed'] is True


def test_anchor_is_source_not_sandbox(workdir):
    """换锚反例（核心）：沙箱被写 ⇒ 仍放行（旧语义「接了就自锁」必须已治死）。"""
    from core.gateway.sandbox_seed import check_seed, seed_sandbox
    src = _fake_source(workdir)
    sb = workdir / 'u' / 's' / 'clawsjoy_dev'
    seed_sandbox(sb, src, commit='t')
    (sb / 'core' / 'new_file.md').write_text('written by agent\n', encoding='utf-8')
    r = check_seed(sb)
    assert r['ok'] is True, '沙箱一写就被拦 ⇒ 换锚未生效（自锁）'
    assert r['evidence']['sandbox_manifest_current'] > 0