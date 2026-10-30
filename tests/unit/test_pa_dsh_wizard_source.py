"""task-183：DSH 向导设置页静态断言（容器/GET/四钮/本地不支持/云端 key/install_steps）。"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "web" / "pa.html"
KEYS = ROOT / "web" / "pa" / "faces" / "keys.js"


def _page():
    return PAGE.read_text(encoding="utf-8")


def _keys():
    return KEYS.read_text(encoding="utf-8")


def test_page_has_dsh_wizard_after_keys():
    page = _page()
    i_keys = page.find('id="paKeys"')
    i_wiz = page.find('id="paDshWizard"')
    assert i_keys > 0 and i_wiz > i_keys, "DSH 向导须在密钥面之后"
    assert 'id="paDshStatus"' in page
    assert 'id="paDshBody"' in page
    assert 'id="paDshSteps"' in page
    for word in ("重新检测", "填写 dsh 路径", "配置云端", "使用本地"):
        assert word in page
    assert "外部运行时 · DSH" in page


def test_keys_has_load_retry_path_cloud_local_and_probe():
    src = _keys()
    assert "function paDshLoad(force)" in src
    assert "API + '/v9/pa/runtimes/dsh'" in src
    assert "'/v9/pa/runtimes/dsh/path'" in src
    assert "function paDshRetry()" in src
    assert "function paDshPath()" in src
    assert "function paDshCloud()" in src
    assert "function paDshLocal()" in src
    for field in ("d.path", "d.version", "d.key_present", "d.local_supported", "d.install_steps"):
        assert field in src, field


def test_dsh_local_explicitly_unsupported_and_cloud_needs_key():
    src = _keys()
    assert "DSH 本地 provider 未支持" in src
    assert "不假装可用" in src
    assert "本地 Ollama 已可用" in src
    assert "云端 API：需 provider key" in src
    assert "paKeyOpen()" in src
    assert "paDshLoad()" in src.split("function paKeyOpen(){", 1)[1][:1200]


@pytest.mark.skipif(shutil.which("node") is None, reason="node 不在")
def test_node_check_keys():
    p = subprocess.run(
        ["node", "--check", str(KEYS)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30
    )
    assert p.returncode == 0, (p.stdout, p.stderr)
