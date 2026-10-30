"""task-154：PA 前端 send/status 接 /v9/agent/runs 之静态断言（node --check + 源断言）.

不执行 DOM；只读两件源，防端点/轮询/取消/fallback 被回退。
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SEND = ROOT / "web" / "pa" / "faces" / "send.js"
STATUS = ROOT / "web" / "pa" / "faces" / "status.js"


def _send():
    return SEND.read_text(encoding="utf-8")


def _status():
    return STATUS.read_text(encoding="utf-8")


def test_work_dev_route_uses_runs_with_flag():
    src = _send()
    assert "var PA_RUN_API = 1;" in src
    assert "(state.mode==='work' || state.mode==='dev')" in src
    assert "return await sendAgentViaRuns(t, _utext);" in src
    assert "async function sendAgentViaRuns(" in src


def test_submit_contract_has_client_request_id_and_model():
    src = _send()
    assert "client_request_id" in src
    assert "task:_paRunsContextTask(t,userText)" in src
    assert "paModelSel()" in src
    assert "API+'/v9/agent/runs'" in src
    assert "r.status===429" in src and "queue_full" in src


def test_polling_after_seq_and_backoff():
    src = _send()
    assert "?after_seq=" in src
    assert "next_after_seq" in src
    assert "let delay=500;" in src
    assert "delay=1000;" in src
    assert "setTimeout(res,delay);" in src
    assert "async function _paPollRun(" in src


def test_done_extracts_output_content_and_records_turn():
    src = _send()
    assert "out.content" in src
    assert "addMsg('assistant',content" in src
    assert "recordPaTurn(t.id,userText,content" in src
    assert "paSetState('done')" in src


def test_failed_and_cancelled_visible():
    src = _send()
    assert "d.state==='failed'" in src or "st==='failed'" in src
    assert "_why" in src and "d.code" in src
    assert "st==='cancelled'" in src
    assert "paSetState('cancelled','已取消')" in src


def test_cancel_uses_runs_cancel_not_only_abort():
    src = _send()
    assert "async function paCancelRun(runId)" in src
    assert "API+'/v9/agent/runs/'+encodeURIComponent(runId)+'/cancel'" in src
    assert "paCancelRun(_rid)" in src, "paStop 必须接 runs cancel"
    assert "window.paStop.__paRunsWrapped" in src


def test_old_sse_fallback_preserved():
    src = _send()
    assert "API+'/v9/agent/chat'" in src
    assert "readSSE(resp)" in src
    assert "PA_RUN_API" in src
    assert "fallback" in src.lower()


def test_status_has_queued_and_cancelled():
    src = _status()
    assert "queued:" in src
    assert "cancelled:" in src
    assert "PA_TERMINAL = {idle:1, done:1, failed:1, stopped:1, cancelled:1}" in src
    assert "paRun.state==='queued'" in src or "paRun.state==='approval' || paRun.state==='queued'" in src


def test_lastrun_written_on_submit():
    src = _send()
    assert "PA_LAST_RUN_KEY = 'pa.lastRun'" in src
    assert "localStorage.setItem(PA_LAST_RUN_KEY" in src
    assert "run_id:d.run_id" in src and "session_id:t.id" in src and "at:Date.now()" in src


def test_restore_reads_get_and_continues_poll_or_terminal():
    src = _send()
    assert "async function paRestoreLastRun(" in src
    assert "localStorage.getItem(PA_LAST_RUN_KEY)" in src
    assert "API+'/v9/agent/runs/'+encodeURIComponent(rec.run_id)" in src
    assert "d.state==='queued' || d.state==='running'" in src
    assert "await _paPollRun(rec.run_id,t,'')" in src
    assert "_paApplyRunState(d)" in src
    # 终态恢复只显示状态行，⛔ 重复落消息（restore 函数内无 addMsg/recordPaTurn）
    body = src.split("async function paRestoreLastRun(", 1)[1].split("async function sendAgentViaRuns(", 1)[0]
    assert "addMsg(" not in body and "recordPaTurn(" not in body


def test_restore_clears_only_on_404_and_init_hook():
    src = _send()
    assert "if(r.status===404)" in src
    assert "localStorage.removeItem(PA_LAST_RUN_KEY)" in src
    assert src.count("removeItem(PA_LAST_RUN_KEY)") == 1, "唯 404 清 lastRun"
    assert "document.addEventListener('DOMContentLoaded'" in src
    assert "setTimeout(paRestoreLastRun, 0)" in src


def test_single_send_chain_work_dev_no_silent_fallback():
    src = _send()
    body = src.split("async function sendAgent(t, userText){", 1)[1].split("/* ===== P0-3", 1)[0]
    assert "if(state.mode==='work' || state.mode==='dev'){" in body
    assert "return await sendAgentViaRuns(t, _utext);" in body
    assert "Number(PA_RUN_API) !== 0" not in body, "work/dev 禁止按 flag 落旧 SSE"


def test_selfdesc_bypasses_stop_card_for_runs_only():
    path = ROOT / "web" / "pa" / "faces" / "selfdesc.js"
    src = path.read_text(encoding="utf-8")
    assert "function _paWorkDevRunsDirect()" in src
    assert "if(_paWorkDevRunsDirect()) return _runOrOrig(this, arguments);" in src
    assert "stopAsk({" in src
    i_direct = src.find("if(_paWorkDevRunsDirect()) return _runOrOrig(this, arguments);")
    i_card = src.find("stopAsk({", i_direct)
    assert i_direct > 0 and i_card > i_direct


def test_stopping_copy_and_terminal_states():
    src = _send()
    assert "paSetState('stopping','停止中…')" in src
    st = _status()
    for key, label in (("stopping:", "停止中"), ("stopped:", "已停止"), ("cancelled:", "已取消")):
        assert key in st and label in st
    assert "PA_TERMINAL = {idle:1, done:1, failed:1, stopped:1, cancelled:1}" in st


def test_runs_context_recent8_exclude_current_truncate_task():
    src = _send()
    assert "function _paRunsContextTask(t,userText)" in src
    assert ".slice(-8)" in src, "最近 8 条"
    assert "String(m.content||'').trim()===cur.trim()" in src, "排除当前 userText 重复"
    assert ".slice(0,800)" in src, "每条截断 800 字"
    assert "【最近对话（上下文）】" in src
    assert "'老板：'" in src and "'PA：'" in src
    assert "【当前任务】" in src
    assert "（对话说明：老板即用户本人）" in src, "本地模型称谓提示"
    assert "task:_paRunsContextTask(t,userText)" in src, "runs task 必须带上下文"


@pytest.mark.skipif(shutil.which("node") is None, reason="node 不在")
def test_node_check_both_files():
    for path in (SEND, STATUS):
        p = subprocess.run(
            ["node", "--check", str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        assert p.returncode == 0, (path.name, p.stdout, p.stderr)
