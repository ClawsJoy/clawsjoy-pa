"""P2 跨 session 复盘面板测试: goal/history API + 前端复盘模块"""
import sys

sys.path.insert(0, ".")
import pytest

_SRC = open("routes/session.py", encoding="utf-8").read()
_HTML = open("web/dashboard/workbench.html", encoding="utf-8").read()
_APICLIENT = open("web/dashboard/api-client.js", encoding="utf-8").read()
_REVIEW = open("web/static/js/goal-review.js", encoding="utf-8").read()


def test_goal_history_route_exists():
    """后端应有 GET /v9/goal/history 路由"""
    assert '@bp.route("/v9/goal/history", methods=["GET"])' in _SRC
    assert "def v9_goal_history():" in _SRC


def test_goal_history_reuses_apis():
    """复用 list_goals + get_session_log.derive_turns(不新造数据源)"""
    assert "from core.gateway.goal_state import list_goals" in _SRC
    assert "list_goals(_gh_uid, limit=_gh_limit)" in _SRC
    assert "from core.gateway.session_log import get_session_log" in _SRC
    assert "derive_turns()" in _SRC


def test_goal_history_payload_shape():
    """返回字段含 goal_id/session_id/objective/status/progress/时间 + turns"""
    src = open("routes/session.py", encoding="utf-8").read()
    seg = src[src.index("def v9_goal_history()") :]
    for f in (
        "goal_id",
        "session_id",
        "objective",
        "status",
        "progress",
        "started_at",
        "updated_at",
        "source_turn",
        "turns",
    ):
        assert f'"{f}"' in seg, f"响应应含 {f}"


def test_frontend_goal_review_wired():
    """前端: 复盘 nav + tab + switchTab 钩子 + 模块脚本"""
    assert 'data-tab="goal-review"' in _HTML, "应有复盘 nav 按钮"
    assert 'id="tab-goal-review"' in _HTML, "应有复盘 tab 面板"
    assert "loadGoalReview" in _HTML, "switchTab 应调用 loadGoalReview"
    assert 'src="/web/static/js/goal-review.js"' in _HTML, "应加载 goal-review.js"
    assert 'id="goalStatusFilter"' in _HTML, "应有状态过滤器"
    assert 'id="goalReviewList"' in _HTML, "应有列表容器"


def test_frontend_goal_module_exports():
    """goal-review.js 导出 loadGoalReview/toggleGoalTurns"""
    assert "global.loadGoalReview = loadGoalReview" in _REVIEW
    assert "global.toggleGoalTurns = toggleGoalTurns" in _REVIEW
    assert "API.goal.history" in _REVIEW, "应调用 DSH_API.goal.history"


def test_apiclient_goal_method():
    """api-client.js 应暴露 goal.history"""
    assert "goalApi" in _APICLIENT
    assert "history: (params) => request('/v9/goal/history', { params })" in _APICLIENT
    assert "goal: goalApi" in _APICLIENT


def test_goal_history_last_reason_field():
    """历史 API 返回 last_reason(前端分类失败/暂停任务的真实结束原因)"""
    src = open("routes/session.py", encoding="utf-8").read()
    seg = src[src.index("def v9_goal_history()") :]
    assert '"last_reason"' in seg, "响应应含 last_reason 字段"
    # 从最近 turn 的 reason 提取(倒序取第一个非空)
    assert "_last_rs" in seg and "reversed(_recent)" in seg
