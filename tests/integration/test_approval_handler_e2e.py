# -*- coding: utf-8 -*-
"""Approval handler E2E: real pending -> approve -> write -> clear.

Pending is seeded into write_gate state (not produced by an organic model tool call);
this covers the approval handler, guard, file write, and state clear.
"""
import time

from flask import Flask

import core.gateway.approval as A
from core.gateway.write_gate import _pending_writes


def test_approval_handler_writes_and_clears(tmp_path):
    target = tmp_path / "approval.txt"
    sid = "approval-handler-test"
    uid = "approval-handler-user"
    _pending_writes[sid] = {
        "id": "e2e-pending-1",
        "tool": "write_file",
        "path": str(target),
        "content": "approval handler e2e",
        "content_preview": "approval handler e2e",
        "ts": time.time(),
        "approved": False,
    }
    app = Flask(__name__)
    with app.test_request_context(
        "/v9/agent/runs/approval",
        method="POST",
        json={
            "user_id": uid,
            "session_id": sid,
            "approve_write": {"id": "e2e-pending-1", "action": "approve"},
            "messages": [],
        },
    ):
        res = A._handle_write_approval(
            uid, sid, [], "", {"id": "e2e-pending-1", "action": "approve"}
        )
        body = res.get_data(as_text=True)
    assert getattr(res, "status_code", None) == 200
    assert "write_confirmed" in body
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "approval handler e2e"
    assert sid not in _pending_writes
