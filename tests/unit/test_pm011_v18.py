# -*- coding: utf-8 -*-
r"""PM-011v18 · §一 扩批的**四个专属门**（CW `b2a5182` · 2026-09-30）。

PM 2026-09-30 11:0x 裁（v18 答件 §一）：把 `core/gateway/sandbox_ops.py` 里那 **7 处**同族
（`request.json or {}`）**并批一次改完，再一次重启**；条件 2：若超出一件的规模 ⇒ 拆回「先重启现盘」。

- v17 已落 2 处（`list` ＋ 共享装饰器 ⇒ 覆盖 read/search/edit/query_index/exec）；
- v18 把剩下 **5 处**改成同一个入口，其中 ⭐ **`checkpoint` / `rollback` 是真正没守卫的两处**
  （装饰器覆盖不到 ⇒ v17 之前它们的空载荷直接落到默认值）。

⭐ 本件的四个专属齿 = `edit` / `query_index` / `checkpoint` / `rollback` 各一个
   （read/search/exec 的齿在 v17 件 `test_pm011_v17.py` 里）。

⛔ **本件不加**「源码里 `request.json or {}` 计数 = 0」那种 invariant 门 ——
   它必然与**每一处**专属齿同时变红 ⇒ 按 PM 的机检 `exclusive`（实际红集 ≡ 期望红集）规则，那叫**搭车**。
   该读数改用 **AST 探针**单独报（见回执），⛔ 不当门。
"""
from __future__ import annotations

import pytest
from flask import Flask

BAD_JSON = b"{not json"


def _err(r):
    j = r.get_json() or {}
    return j.get("error") or ""


class _FakeProc:
    """`subprocess.run` 的替身：⛔ 不碰真 git、⛔ 不写生产面。"""

    def __init__(self, stdout="", returncode=0, stderr=""):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # ⭐ 沙箱根是相对路径 ⇒ 换 cwd 即隔离；⛔ 测试不许写生产数据面。
    monkeypatch.chdir(tmp_path)
    app = Flask(__name__)
    app.config["PROPAGATE_EXCEPTIONS"] = False
    from core.lib.error_handler import register_error_handlers

    register_error_handlers(app)
    from routes.sandbox import bp as _sandbox_bp

    app.register_blueprint(_sandbox_bp)
    return app.test_client()


def _patch_git(monkeypatch, tmp_path):
    """hermetic：把沙箱根指到 tmp（带假 `.git`），并替掉 `subprocess.run` 与 `safe_git_commit`。"""
    import core.gateway.sandbox_ops as so

    sb = tmp_path / "sb"
    (sb / ".git").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(so, "_get_sandbox_base", lambda uid, sid: sb)
    calls = []

    def _fake_run(cmd, **kw):
        calls.append(list(cmd))
        if "rev-parse" in cmd:
            return _FakeProc(stdout="deadbeef\n")
        if "status" in cmd:
            return _FakeProc(stdout=" M a.txt\n")
        return _FakeProc(stdout="")

    monkeypatch.setattr("subprocess.run", _fake_run)
    monkeypatch.setattr(
        "core.gateway.sandbox_git.safe_git_commit",
        lambda base, files, msg, require_toplevel=None: (True, {"reason": ""}),
    )
    return sb, calls


# ============ 门 X2 · `edit`（被装饰 ⇒ 上游先拦；handler 亦自证） ============

def test_x7_wrapped_edit_empty_payload_is_400(client):
    """病：`{}` ⇒ 默认路径/内容冒充调用方意图 ⇒ 改后须 400。"""
    r = client.post("/v9/sandbox/edit", json={})
    assert r.status_code == 400, "空载荷须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert "v9/sandbox/edit" in e and "空载荷" in e, "须定位＋说明：%r" % e


# ============ 门 X2 · `query_index` ============

def test_x8_wrapped_query_index_empty_payload_is_400(client):
    """病：`{}` ⇒ 旧行为是 **200** ＋ `{"success": false, "error": "query 必填"}`（HTTP 码与结果不符）。"""
    r = client.post("/v9/sandbox/query_index", json={})
    assert r.status_code == 400, "空载荷须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert "v9/sandbox/query_index" in e and "空载荷" in e, "须定位＋说明：%r" % e


# ============ 门 X2 · `checkpoint`（⭐ v17 之前**无守卫**） ============

def test_x9_checkpoint_empty_payload_is_400(client):
    """病：`{}` ⇒ `message` 落默认「Auto checkpoint」⇒ **台账面留下一条没人下过的令**。"""
    r = client.post("/v9/sandbox/checkpoint", json={})
    assert r.status_code == 400, "空载荷须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert "v9/sandbox/checkpoint" in e and "空载荷" in e, "须定位＋说明：%r" % e


def test_x9b_checkpoint_non_dict_is_400(client):
    r = client.post("/v9/sandbox/checkpoint", json=["x"])
    assert r.status_code == 400, "非对象须 400（实测 %s）" % r.status_code
    e = _err(r)
    assert "v9/sandbox/checkpoint" in e and "需要 JSON 对象" in e and "list" in e, "须定位＋报形状：%r" % e


# ============ 门 X2 · `rollback`（⭐ v17 之前**无守卫**；默认 target 是破坏性的） ============

def test_x10_rollback_empty_payload_is_400(client):
    """病：`{}` ⇒ `target` 落默认 `HEAD~1` ⇒ **`git reset --hard`**（默认值冒充调用方意图，且破坏性）。"""
    r = client.post("/v9/sandbox/rollback", json={})
    assert r.status_code == 400, "空载荷须 400（实测 %s）：%s" % (r.status_code, r.data[:200])
    e = _err(r)
    assert "v9/sandbox/rollback" in e and "空载荷" in e, "须定位＋说明：%r" % e


def test_x10b_rollback_non_dict_is_400(client):
    r = client.post("/v9/sandbox/rollback", json=["x"])
    assert r.status_code == 400, "非对象须 400（实测 %s）" % r.status_code
    e = _err(r)
    assert "v9/sandbox/rollback" in e and "需要 JSON 对象" in e, "须定位＋报形状：%r" % e


def test_x10c_rollback_bad_json_is_400(client):
    r = client.post("/v9/sandbox/rollback", data=BAD_JSON, content_type="application/json")
    assert r.status_code == 400, "坏 JSON 须 400（实测 %s）" % r.status_code
    assert "不是合法 JSON" in _err(r), _err(r)


# ============ 对照臂（⛔ 守卫不许误伤正经调用） ============

def test_x11_checkpoint_good_shape_arm_200(client, tmp_path, monkeypatch):
    """好形状 ⇒ 200；hermetic（subprocess / safe_git_commit 全替身，⛔ 不碰真仓库）。"""
    _patch_git(monkeypatch, tmp_path)
    r = client.post(
        "/v9/sandbox/checkpoint",
        json={"user_id": "u", "session_id": "s", "message": "caller-supplied msg"},
    )
    assert r.status_code == 200, "好形状须 200（实测 %s）：%s" % (r.status_code, r.data[:200])
    j = r.get_json() or {}
    assert j.get("success") is True and j.get("hash") == "deadbeef", j


def test_x12_rollback_good_shape_uses_caller_target(client, tmp_path, monkeypatch):
    """⭐ 对照臂的重点：`target` **必须是调用方给的那个**（⛔ 不是默认 `HEAD~1`）。"""
    _sb, calls = _patch_git(monkeypatch, tmp_path)
    r = client.post(
        "/v9/sandbox/rollback",
        json={"user_id": "u", "session_id": "s", "target": "v42-tag"},
    )
    assert r.status_code == 200, "好形状须 200（实测 %s）：%s" % (r.status_code, r.data[:200])
    assert (r.get_json() or {}).get("success") is True, r.data[:200]
    assert ["git", "reset", "--hard", "v42-tag"] in calls, "target 未用调用方给的：%r" % (calls,)
