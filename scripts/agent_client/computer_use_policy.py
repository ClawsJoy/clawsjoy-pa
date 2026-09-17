# -*- coding: utf-8 -*-
"""computer_use 写动作治理策略（2026-09-10，白皮书 v1 的机器执行层）

【原则】宁可不做，不能做错。默认拒绝（fail-closed）。不确定就是拒绝。
与收件箱《写动作治理白皮书 v1》同源；本文件是给机器执行的，单测覆盖。

三级决策:
  allow             → 放行（但治理门的"随时停止"仍生效）
  approve           → 必须逐次审批（老板在场确认这一次）
  approve_presence  → 逐次审批 + 明确在场（更高风险）
  deny              → 绝对禁止，永不自动化

【为什么在这做】
  治理门(停止/会话授权/审批)在网关侧是"动作级"的，不知道"这个动作打的是哪个应用"。
  本策略补上"应用语义"这一维: 同样的 type_text，打进 WPS 和打进支付页是两个风险等级。
"""
import re

# ---- 动作分级 ----
LOW_RISK_OPS = {"activate_window", "perform_secondary_action"}  # L1 一次授权可免逐次
# (2026-09-10 老板审阅) scroll 会触发页面行为 → 升 L2 逐次审批
PER_ACTION_OPS = {"click", "type_text", "set_value", "drag", "move", "drag_handle", "press_key", "scroll"}  # L2 逐次审批
LAUNCH_OPS = {"launch_app"}  # L3 逐次+在场

# 防御性: 这些 op 不在 computer_use.ALL_OPS 里, 但若未来加回来, 一律 deny
DENY_OP_KEYWORDS = ("delete", "remove", "format", "uninstall", "clear", "rm", "卸载", "删除", "清空", "格式化")

# ---- 应用黑名单（命中即 deny, 任何写动作都不行）----
DENY_APP_KEYWORDS = (
    "支付",
    "银行",
    "银行卡",
    "支付宝",
    "微信支付",
    "password",
    "keepass",
    "1password",
    "bitwarden",
    "keychain",
    "系统设置",
    "控制面板",
    "注册表",
    "regedit",
    "防火墙",
    "安全中心",
    "任务管理器",
    "cmd.exe",
    "powershell",
    "terminal",
    "console",
    "终端",
    # 第8条: 安全软件, 永不削弱防护
    "defender",
    "杀毒",
    "antivirus",
    "火绒",
    "安全卫士",
    "卡巴",
    "norton",
    "360安全",
)

# 第7条: AI 自我修改 —— 写动作目标若是 PA 自己的治理产物, 一律 deny。
# 主权 agent 不能自己改自己的规则。检测依据: 目标窗口标题含这些治理文件名。
SELF_MODIFY_TITLE_KEYWORDS = (
    "computer_use_policy",
    "endpoint_guard",
    "gateway_routes",
    "browser_local",
    "execution_policy",
    "roster",
    "config.toml",
    "profile.json",
    "ledger.json",
    "治理白皮书",
    "写动作治理",
)

# 浏览器「限定站点」的禁止清单(网银/支付/密码管理/内部系统/后台)
BROWSER_DENY_SITE_KEYWORDS = (
    "网银",
    "网上银行",
    "收银台",
    "支付",
    "password",
    "1password",
    "bitwarden",
    "内部系统",
    "管理后台",
    "后台",
    "admin",
    "控制台",
)

# ---- 应用白名单（PA 可驱动的办公工具）----
ALLOW_APP_KEYWORDS = (
    "wps.exe",
    "wpp.exe",
    "et.exe",
    "word",
    "excel",
    "powerpoint",
    "chrome",
    "edge",
    "firefox",
    "obsidian",
    "blender",
    "explorer.exe",
    "文件资源管理器",
)

# 敏感上下文关键词（出现在窗口标题里, 视为高风险, 升级到 approve_presence 或 deny）
SENSITIVE_TITLE_KEYWORDS = ("登录", "支付", "密码", "验证码", "付款", "转账", "password", "login", "card", "卡号")


def _hit(text, keywords):
    """子串匹配（用于 app 名/窗口标题这类自由文本）。"""
    t = (text or "").lower()
    for k in keywords:
        if k.lower() in t:
            return k
    return None


def _op_hit(op, keywords):
    """动作名按【整词】匹配（op 是 snake_case token），避免子串误伤。

    例: 关键词 rm 不能误伤 perform_secondary_action（子串 'rm' 恰好藏在 'perform' 里）。
    """
    toks = set((op or "").lower().split("_"))
    for k in keywords:
        kk = k.lower()
        if kk == op.lower() or kk in toks:
            return k
    return None


def evaluate(op, app="", title="", allow_write=False):
    """写动作治理决策。

    参数:
      op          computer_use 的动作名(必须在 WRITE_OPS 里; 调用方保证)
      app         目标应用的标识(list_windows/list_apps 里的 app 字段, 或窗口对象)
      title       目标窗口标题(用于敏感上下文检测)
      allow_write 是否已显式声明(computer_use 已校验过, 这里兜底)
    返回:
      {"decision": allow|approve|approve_presence|deny, "reason": str}
    """
    # 0) 硬门槛: 没显式 allow_write 一律 deny(这是 computer_use 里的第一道锁, 这里兜底)
    if not allow_write:
        return {"decision": "deny", "reason": "写动作必须显式 allow_write=true"}

    # 1) 不可逆动作关键词 → deny（动作名整词匹配）
    k = _op_hit(op, DENY_OP_KEYWORDS)
    if k:
        return {"decision": "deny", "reason": "不可逆动作关键词命中: %s" % k}

    # 2) 应用黑名单 → deny
    k = _hit(app, DENY_APP_KEYWORDS)
    if k:
        return {"decision": "deny", "reason": "禁区应用命中: %s" % k}

    # 3) 敏感上下文(窗口标题含支付/密码/登录等) → deny（永不自动化输凭证）
    k = _hit(title, SENSITIVE_TITLE_KEYWORDS)
    if k and op in ("type_text", "set_value", "click"):
        return {"decision": "deny", "reason": "敏感上下文命中: 标题含「%s」，禁止自动化输入/点击" % k}

    # 3.5) 第7条: AI 自我修改 → deny（主权 agent 不能自己改自己的规则）
    k = _hit(title, SELF_MODIFY_TITLE_KEYWORDS)
    if k and op in ("type_text", "set_value", "click"):
        return {"decision": "deny", "reason": "AI 自我修改命中: 目标含「%s」，禁止改 PA 自己的治理产物" % k}

    # 3.6) 浏览器限定站点: 浏览器内打到禁止站点 → deny
    if _hit(app, ("chrome", "edge", "firefox")):
        k = _hit(title, BROWSER_DENY_SITE_KEYWORDS)
        if k:
            return {"decision": "deny", "reason": "浏览器禁止站点命中: 「%s」" % k}

    # 4) 低风险写 → allow（但仍受网关"随时停止"约束）
    if op in LOW_RISK_OPS:
        return {"decision": "allow", "reason": "低风险写动作(切窗口/滚动/二级动作)"}

    # 5) 启动应用 → 逐次+在场
    if op in LAUNCH_OPS:
        return {"decision": "approve_presence", "reason": "启动应用属逐次+在场"}

    # 6) 逐次审批类(click/type/set_value/drag/...)
    if op in PER_ACTION_OPS:
        if _hit(app, ALLOW_APP_KEYWORDS):
            return {"decision": "approve", "reason": "白名单应用内的输入/点击, 逐次审批"}
        if app:
            return {"decision": "approve_presence", "reason": "应用不在白名单, 升级为逐次+在场"}
        return {"decision": "approve_presence", "reason": "缺少应用上下文, 保守升级为逐次+在场"}

    # 7) 兜底: 未登记动作一律 deny
    return {"decision": "deny", "reason": "未登记写动作, 默认拒绝"}
