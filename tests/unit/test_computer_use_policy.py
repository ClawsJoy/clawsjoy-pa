# -*- coding: utf-8 -*-
"""computer_use 写动作治理策略测试（2026-09-10，白皮书 v1）

契约（铁律）: 宁可不做，不能做错。默认拒绝。不确定就是拒绝。
"""
import sys

sys.path.insert(0, ".")
import pytest

sys.path.insert(0, "scripts/agent_client")
import computer_use_policy as P


# ---- 核心原则: 绝对禁止 ----
@pytest.mark.parametrize(
    "app", ["支付宝", "微信支付", "中国银行", "1Password", "系统设置", "regedit", "cmd.exe", "powershell", "控制面板", "防火墙"]
)
def test_deny_app_never_automated(app):
    r = P.evaluate("type_text", app=app, allow_write=True)
    assert r["decision"] == "deny"


def test_sensitive_title_input_denied():
    """窗口标题含密码/支付/登录 -> 禁止自动化输入/点击"""
    assert P.evaluate("type_text", app="chrome", title="登录 - 支付宝", allow_write=True)["decision"] == "deny"
    assert P.evaluate("set_value", app="chrome", title="请输入支付密码", allow_write=True)["decision"] == "deny"
    assert P.evaluate("click", app="chrome", title="验证码登录", allow_write=True)["decision"] == "deny"


def test_irreversible_op_denied():
    r = P.evaluate("delete", app="explorer.exe", allow_write=True)
    assert r["decision"] == "deny"


def test_no_allow_write_denied_even_for_whitelisted():
    """没显式 allow_write, 白名单应用也 deny（第一道锁兜底）"""
    assert P.evaluate("click", app="wps.exe", allow_write=False)["decision"] == "deny"


# ---- 分级 ----
def test_low_risk_write_allowed():
    assert P.evaluate("activate_window", app="wps.exe", allow_write=True)["decision"] == "allow"
    assert P.evaluate("perform_secondary_action", app="chrome", allow_write=True)["decision"] == "allow"


def test_launch_app_needs_presence():
    r = P.evaluate("launch_app", app="wps.exe", allow_write=True)
    assert r["decision"] == "approve_presence"


def test_click_on_whitelisted_app_needs_approval():
    """白名单应用内的点击 = 逐次审批"""
    r = P.evaluate("click", app="wps.exe", allow_write=True)
    assert r["decision"] == "approve"


def test_click_on_unknown_app_upgrades_to_presence():
    """不在白名单也不在黑名单 -> 升级逐次+在场（保守）"""
    r = P.evaluate("click", app="某未知.exe", allow_write=True)
    assert r["decision"] == "approve_presence"


def test_missing_app_context_conservative():
    """缺应用上下文 -> 保守升级逐次+在场"""
    r = P.evaluate("click", app="", allow_write=True)
    assert r["decision"] == "approve_presence"


def test_unregistered_op_default_deny():
    assert P.evaluate("something_new", app="wps.exe", allow_write=True)["decision"] == "deny"


# ---- 与 computer_use 的联动: deny 必须硬拦 ----
def test_computer_use_denies_payment_app():
    import computer_use as CU

    r = CU.computer_use({"op": "type_text", "allow_write": True, "app": "支付宝"})
    assert "error" in r and "治理策略拒绝" in r["error"]


def test_computer_use_write_not_enabled_until_opened():
    """非 deny 的写动作: 当前状态是 write_not_enabled(未放开), 绝不静默执行"""
    import computer_use as CU

    r = CU.computer_use({"op": "activate_window", "allow_write": True, "app": "wps.exe"})
    assert r.get("status") == "write_not_enabled"
    assert r["policy"]["decision"] == "allow"  # 决策已算出并透出
    assert "result" not in r  # 未执行, 故无 result


# ---- 老板审阅补充(2026-09-10) ----
def test_self_modification_denied():
    """第7条: 主权 agent 不能自己改自己的规则"""
    for title in (
        "computer_use_policy.py - 记事本",
        "endpoint_guard.py - VSCode",
        "写动作治理白皮书 - Obsidian",
        "config.toml - 记事本",
    ):
        r = P.evaluate("type_text", app="notepad", title=title, allow_write=True)
        assert r["decision"] == "deny", (title, r)
    # 但普通文档不受影响
    assert P.evaluate("type_text", app="wps.exe", title="方案.pptx - WPS", allow_write=True)["decision"] != "deny"


def test_security_app_denied():
    """第8条: 永不削弱防护"""
    for app in ("defender", "360安全卫士", "火绒", "杀毒"):
        assert P.evaluate("click", app=app, allow_write=True)["decision"] == "deny"


def test_scroll_upgraded_to_per_action():
    """scroll 会触发页面行为, 从 L1 升到 L2"""
    r = P.evaluate("scroll", app="chrome", allow_write=True)
    assert r["decision"] == "approve", "scroll 应升 L2(approve), 不是 allow"


def test_browser_forbidden_site_denied():
    """浏览器限定站点: 网银/支付/内部系统/后台 → deny"""
    for title in ("中国银行 网上银行", "支付宝 - 收银台", "公司内部系统 - 管理后台"):
        r = P.evaluate("click", app="chrome", title=title, allow_write=True)
        assert r["decision"] == "deny", (title, r)


def test_browser_normal_site_needs_approval():
    """浏览器普通站点(公开信息/自己账号) = 逐次审批, 不因熟悉而放宽"""
    r = P.evaluate("click", app="chrome", title="DS chat - DeepSeek", allow_write=True)
    assert r["decision"] == "approve"
