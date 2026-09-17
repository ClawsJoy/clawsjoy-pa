# -*- coding: utf-8 -*-
"""PA 画像种子 v0(2026-09-10): 首次初始化时灌入已沉淀条目(源自收件箱/PA方向与画像内核.md §6-§8)。"""
SEED = [
    # lesson: 试错教训
    ("lesson", "PPT 形状模板自动映射(v1)被否; 正确=模板优先/人确认 或 freeform HTML 设计", "2026-09-10 老板反馈", "high", "confirmed"),
    ("lesson", "视觉品质靠模板库/色板系统(布局/字体/配色/背景), 不靠 agent 手拼", "2026-09-10 老板反馈", "high", "confirmed"),
    # aesthetic
    (
        "aesthetic",
        "候选主题: A Electric Studio(蓝橙) / B Swiss Modern(黑白瑞士红) / C Blue Professional / D Dark Botanical; 待老板圈定",
        "2026-09-10 初筛",
        "medium",
        "proposed",
    ),
    ("aesthetic", "禁忌待老板给(示例: 禁紫色渐变/禁 emoji 满屏/要留白)", "2026-09-10", "low", "proposed"),
    # style: 合作风格
    ("style", "问题分析: 根因优先, 拒绝打补丁", "多轮协作明示", "high", "confirmed"),
    ("style", "方案偏好: 确定性优先(状态机/纯函数/守卫), 模糊留给必要处", "F0 内核/熔断等", "high", "confirmed"),
    ("style", "诚实底线: 编造数字/假成功不可接受; 未查到/待线下核实 是合法输出", "PPT 数字审核", "high", "confirmed"),
    ("style", "沟通: 结论先行 + 可选项 + 默认项; 少开放式问卷", "本会话模式", "medium", "proposed"),
    # product/decision
    ("decision", "principal = ClawsJoy 运营者本人(先用产品喂自己); 光电老板类客户为后续形态", "2026-09-10 就职约定", "high", "confirmed"),
    ("decision", "V9=PA(7x24 陪伴/商量/积累/分派/代理审核); 执行 agent 非常态", "2026-09-10 方向", "high", "confirmed"),
    ("product", "架构方向: V9 内分层长出 PA 首层(core/pa), 执行内核完善为被调度服务; 不 fork V10", "2026-09-10 架构讨论", "medium", "proposed"),
    # channel
    ("channel", "7x24 入口候选: WPS 协作@ 派工(与 WPS-AI 桥同链路); GUI 当前可用", "WPS-AI 调研", "low", "proposed"),
]
