"""task-183：DSH 向导设置页静态断言（容器／GET／单一操作条／内联路径／云端切换／本地不支持）。"""

import shutil
import subprocess
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
    for el in ('id="paDshStatus"', 'id="paDshBody"', 'id="paDshSteps"',
               'id="paDshPathRow"', 'id="paDshPathIn"', 'id="paDshPathSaveBtn"',
               'id="paDshKeyIn"', 'id="paDshKeyRow"'):
        assert el in page, el
    for word in ("重新检测", "填写 dsh 路径", "配置云端", "使用本地"):
        assert word in page, word
    assert "外部运行时 · DSH" in page


def test_action_bar_is_single_row_no_generated_duplicate_buttons():
    page = _page()
    # 四个动作各只出现一次（旧版页脚与卡片各有一份 ⇒ 用户看到两排按钮）
    assert page.count('onclick="paDshCloud()"') == 1
    assert page.count('onclick="paDshLocal()"') == 1
    assert page.count('onclick="paDshRetry()"') == 1
    assert page.count('onclick="paDshPath()"') == 1
    # 动作钮由 HTML 一处定形 ⇒ JS 不再生成带 onclick 的按钮
    src = _keys()
    assert 'onclick="paDshCloud()"' not in src
    assert 'onclick="paDshLocal()"' not in src


def test_keys_has_load_probe_retry_and_busy_guard():
    src = _keys()
    assert "function paDshLoad(force)" in src
    assert "API + '/v9/pa/runtimes/dsh'" in src
    assert "'/v9/pa/runtimes/dsh/path'" in src
    assert "function paDshRetry()" in src
    assert "if(paDshBusy)" in src
    assert "paDshBusySet" in src
    for field in ("d.path", "d.version", "d.key_present", "d.local_supported", "d.install_steps"):
        assert field in src, field


def test_path_uses_inline_form_not_window_prompt():
    src = _keys()
    assert "window.prompt" not in src
    assert "paDshPathRow" in src
    assert "paDshPathSave()" in src
    assert "paDshPathCancel()" in src
    assert "function paDshPathSave()" in src
    assert "function paDshPathCancel()" in src


def test_cloud_points_to_dedicated_dsh_key_not_pa_provider():
    src = _keys()
    assert "async function paDshCloud()" in src
    assert "paDshKeyIn" in src
    assert "DSH 使用自己的独立 key" in src
    # 不再把 PA provider 密钥当成 DSH key
    block = src.split("async function paDshCloud()", 1)[1].split("async function paDshKeySave()", 1)[0]
    assert "paKeyPick(" not in block
    assert "paKeyStateText(" not in block
    assert "paKeyOpen(" not in block
    # 不 POST key、不触发运行（保存/清除在独立函数）
    assert "/v9/pa/harness/key" not in block
    assert "/v9/pa/runtimes/dsh/path" not in block
    # 打开密钥面时不得重拉 DSH 状态（否则刚给的用户提示被「读数中…」盖掉）
    open_block = src.split("function paKeyOpen(){", 1)[1]
    assert "paDshLoad()" not in open_block[:1200]


def test_dsh_local_explicitly_unsupported_and_pa_local_available():
    src = _keys()
    assert "DSH 的本地 provider 目前未支持" in src
    assert "不假装可用" in src
    assert "PA 自己的本地 Ollama 已可用" in src


@pytest.mark.skipif(shutil.which("node") is None, reason="node 不在")
def test_node_check_keys():
    p = subprocess.run(
        ["node", "--check", str(KEYS)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30
    )
    assert p.returncode == 0, (p.stdout, p.stderr)
