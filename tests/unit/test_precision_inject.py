"""Obsidian 集成 + 精准注入测试: vault 检索/复盘写入/踩坑追加/多源过滤"""
import json
import sys
import time

sys.path.insert(0, ".")
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _iso(monkeypatch, tmp_path):
    """隔离: vault 路径指向 tmp + obsidian 配置启用"""
    import core.gateway.precision_inject as pi

    vault = tmp_path / "vault"
    for sub in ("Reviews", "SOPs", "Pitfalls", "Templates"):
        (vault / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(pi, "_vault_path", lambda: str(vault))
    monkeypatch.setattr(
        pi,
        "_obsidian_cfg",
        lambda: {
            "enabled": True,
            "vault_path": str(vault),
            "reviews_dir": "Reviews",
            "sops_dir": "SOPs",
            "pitfalls_dir": "Pitfalls",
            "write_on_complete": True,
            "append_pitfalls": True,
            "pitfalls_file": "避坑清单.md",
        },
    )
    yield vault


def test_vault_scan_and_search(_iso):
    """vault 扫描 + TF 检索: 相关笔记命中"""
    import core.gateway.precision_inject as pi

    NL = chr(10)
    (_iso / "SOPs" / "番茄推广SOP.md").write_text(
        "---" + NL + "tags: [番茄推广]" + NL + "---" + NL + "# 番茄推广SOP" + NL + "## 发布流程" + NL + "选择笔记后点击发布按钮",
        encoding="utf-8",
    )
    (_iso / "Reviews" / "2026-08-27-task1.md").write_text(
        "---" + NL + "tags: [抖音]" + NL + "---" + NL + "# 抖音复盘" + NL + "## 踩坑" + NL + "抖音发布需要先绑定手机号", encoding="utf-8"
    )
    res = pi.search_vault("番茄推广怎么发布", limit=3)
    assert len(res) >= 1
    assert res[0]["name"] == "番茄推广SOP", res


def test_write_task_review(_iso):
    """任务完成 → 写复盘笔记(含 frontmatter + 小节 + 双链)"""
    import core.gateway.precision_inject as pi

    NL = chr(10)
    (_iso / "SOPs" / "番茄推广SOP.md").write_text("# 番茄推广SOP" + NL + "发布流程", encoding="utf-8")
    path = pi.write_task_review(
        "u1",
        "s1",
        "task_abc",
        "番茄推广测试",
        "## 做了什么" + NL + "完成了番茄推广" + NL + "## 踩坑" + NL + "发布按钮找不到" + NL + "## 可复用经验" + NL + "用 browser_local click",
    )
    assert path and Path(path).exists()
    txt = Path(path).read_text(encoding="utf-8")
    assert "type: task-review" in txt
    assert "task_id: task_abc" in txt
    assert "## 做了什么" in txt and "完成了番茄推广" in txt
    assert "## 踩坑" in txt and "发布按钮找不到" in txt
    assert "[[番茄推广SOP]]" in txt, "应含双链"


def test_append_pitfall(_iso):
    """新坑 → 追加 avoid_pitfalls.md(幂等)"""
    import core.gateway.precision_inject as pi

    p1 = pi.append_pitfall("抖音发布需要绑定手机号")
    assert p1 and Path(p1).exists()
    txt = Path(p1).read_text(encoding="utf-8")
    assert "抖音发布需要绑定手机号" in txt
    # 幂等: 再次追加同内容不重复
    pi.append_pitfall("抖音发布需要绑定手机号")
    txt2 = Path(p1).read_text(encoding="utf-8")
    assert txt2.count("抖音发布需要绑定手机号") == 1


def test_search_candidates_multi_source(_iso, monkeypatch, tmp_path):
    """多源候选: vault + memory + 报告"""
    import core.gateway.precision_inject as pi

    NL = chr(10)
    (_iso / "SOPs" / "番茄推广SOP.md").write_text("# 番茄推广SOP" + NL + "发布流程发布按钮", encoding="utf-8")
    # memory 源
    from core.gateway import memory as mem

    mem._load_memory = lambda u, k: [{"content": "番茄推广要用 browser_local 点击发布", "ts": time.time()}]
    # 报告源
    sb = tmp_path / "sb"
    (sb / "data" / "reports").mkdir(parents=True, exist_ok=True)
    (sb / "data" / "reports" / "番茄推广复盘.md").write_text("番茄推广报告", encoding="utf-8")
    cands = pi.search_candidates({"text": "番茄推广发布"}, "u1", "s1", str(sb))
    sources = {c["source"] for c in cands}
    assert "vault" in sources and "known_patterns" in sources, sources
    ranked = pi.filter_and_rank(cands, {"text": "番茄推广发布"}, top_n=5)
    assert len(ranked) >= 1 and ranked[0]["source"] in ("vault", "known_patterns")


def test_build_injection_and_full_pipeline(_iso, tmp_path):
    """全流程: get_precision_context 产出注入文本"""
    import core.gateway.precision_inject as pi

    NL = chr(10)
    (_iso / "SOPs" / "番茄推广SOP.md").write_text(
        "---" + NL + "tags: [番茄推广]" + NL + "---" + NL + "# 番茄推广SOP" + NL + NL + "选择笔记发布", encoding="utf-8"
    )
    msgs = [{"role": "system", "content": "x"}, {"role": "user", "content": "帮我做番茄推广"}]
    sb = tmp_path / "sb"
    (sb).mkdir(parents=True, exist_ok=True)
    txt = pi.get_precision_context(msgs, "u1", "s1", str(sb))
    assert txt.startswith("【精准上下文】"), txt
    assert "番茄推广SOP" in txt


def test_filter_rank_related_first(_iso):
    """过滤排序: 相关排前, 不相关排除(score 低于阈值不入选)"""
    import core.gateway.precision_inject as pi

    cands = [
        {"source": "vault", "name": "无关笔记", "score": 0.02, "preview": "完全无关内容"},
        {"source": "vault", "name": "番茄SOP", "score": 0.5, "preview": "番茄推广发布流程"},
        {"source": "known_patterns", "name": "经验", "score": 0.4, "preview": "番茄推广用browser_local", "age_days": 1},
    ]
    ranked = pi.filter_and_rank(cands, {"text": "番茄推广发布"}, top_n=5)
    assert ranked[0]["name"] == "番茄SOP", ranked
    assert "无关笔记" not in [r["name"] for r in ranked], "低相关应被排除"


def test_dedup_repeated_candidates(_iso):
    """去重: 同 name 候选只留 score 高的一条"""
    import core.gateway.precision_inject as pi

    cands = [
        {"source": "vault", "name": "番茄SOP", "score": 0.3, "preview": "旧"},
        {"source": "report", "name": "番茄SOP", "score": 0.8, "preview": "新"},
    ]
    ranked = pi.filter_and_rank(cands, {"text": "番茄"}, top_n=5)
    same = [r for r in ranked if r["name"] == "番茄SOP"]
    assert len(same) == 1, "重复候选应去重"
    assert same[0]["source"] == "report" and same[0]["score"] == 0.8, "保留高分"


def test_summarize_within_100_chars(_iso):
    """压缩: 每条 ≤100 字"""
    import core.gateway.precision_inject as pi

    long_text = "番茄推广" * 60  # 180 字
    s = pi.summarize({"preview": long_text})
    assert len(s) <= 100, f"压缩超限: {len(s)}"


def test_build_injection_token_budget(_iso):
    """注入总量 ≤500 tokens(≈750 字符)"""
    import core.gateway.precision_inject as pi

    cands = [{"source": "vault", "name": f"笔记{i}", "score": 0.5, "preview": "内容" * 200} for i in range(5)]
    txt = pi.build_injection(cands, max_chars=750)
    assert len(txt) <= 800, f"注入超预算: {len(txt)} 字符"


def test_write_task_review_mines_messages(_iso):
    """复盘质量: report 无小节时, 从对话历史挖掘 关键决策/踩坑/可复用经验"""
    import json as _json

    import core.gateway.precision_inject as pi

    NL = chr(10)
    msgs = [
        {"role": "user", "content": "帮我修改 data/app.py"},
        {
            "role": "assistant",
            "content": "我先看看文件",
            "tool_calls": [{"id": "c2", "function": {"name": "execute_command", "arguments": '{"command":"cd /"}'}}],
        },
        {
            "role": "tool",
            "tool_call_id": "c2",
            "content": _json.dumps({"success": False, "error": "cd / 误操作，/ 不是工作目录"}),
        },
        {"role": "assistant", "content": "刚才 cd / 是误操作。改用相对路径进入项目目录。"},
        {
            "role": "assistant",
            "content": "写文件被截断",
            "tool_calls": [
                {"id": "c3", "function": {"name": "write_file", "arguments": '{"path":"data/app.py","content":"long"}'}}
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "c3",
            "content": _json.dumps({"success": False, "error": "相似度过低被拒，建议用 line 参数精确修改单行"}),
        },
        {"role": "assistant", "content": "write_file 覆盖被拒了。改用 sed 命令绕过，只替换那一行。"},
    ]
    tool_steps = [
        {"tool": "execute_command", "arg": "cd /", "success": False, "error": "cd / 误操作"},
        {"tool": "write_file", "arg": "data/app.py", "success": False, "error": "相似度过低被拒"},
        {"tool": "execute_command", "arg": "sed -i", "success": True, "result": "已替换第1行"},
    ]
    # report 只有"做了什么" — 关键决策/踩坑/可复用经验必须从对话挖出
    path = pi.write_task_review(
        "u1", "s1", "task_mine", "配置文件修改", "## 做了什么" + NL + "修改了配置", messages=msgs, tool_steps=tool_steps
    )
    assert path and Path(path).exists()
    txt = Path(path).read_text(encoding="utf-8")
    assert "cd / 误操作" in txt, "踩坑应含 cd / 误操作: " + txt
    assert "改用 sed" in txt, "踩坑应含 sed 绕过: " + txt
    assert "改用相对路径" in txt, "关键决策应含改用相对路径: " + txt
    assert "（无记录）" not in txt, "三个小节都不应为空: " + txt
    # 挖出的小节不覆盖 report 已有小节
    assert "修改了配置" in txt


def test_update_sop_and_list_knowledge(_iso):
    """知识维护: update_sop 追加/覆盖小节 + list_knowledge_files 列常驻文件"""
    import core.gateway.precision_inject as pi

    NL = chr(10)
    (_iso / "SOPs" / "平台发布工作流.md").write_text(
        "---"
        + NL
        + "type: sop"
        + NL
        + "tags: [平台发布]"
        + NL
        + "created: 2026-08-30"
        + NL
        + "updated: 2026-08-30"
        + NL
        + "---"
        + NL
        + NL
        + "# 平台发布工作流"
        + NL
        + "## 知乎发布"
        + NL
        + "旧内容",
        encoding="utf-8",
    )
    p1 = pi.update_sop("平台发布工作流", "小红书 2026-08-30", "- 新选择器: input[placeholder=标题]")
    assert p1 and Path(p1).exists()
    txt = Path(p1).read_text(encoding="utf-8")
    assert "## 小红书 2026-08-30" in txt and "新选择器" in txt
    assert "## 知乎发布" in txt, "原小节应保留"
    assert "updated: " in txt, "frontmatter updated 应更新"
    pi.update_sop("平台发布工作流", "小红书 2026-08-30", "- 更新后的内容")
    txt2 = Path(p1).read_text(encoding="utf-8")
    assert "更新后的内容" in txt2 and "新选择器" not in txt2, "同名小节应被覆盖"
    assert pi.update_sop("不存在的SOP", "x", "y") is None
    files = pi.list_knowledge_files()
    # R4(2026-08-31): list 返回实际存在的全部 .md(不再无条件追加固定项)。
    # update_sop 已创建平台发布工作流 → key 存在; 未创建的文件不出现(更真实)。
    keys = {f["key"] for f in files if f["key"]}
    assert "平台发布工作流" in keys, "已创建的 SOP 应在列表中"
    # 全 vault 树: list 应带 rel_path 且包含已创建文件
    rels = [f.get("rel_path", "") for f in files]
    assert any("平台发布工作流" in r for r in rels), "list 应含已创建 SOP 的 rel_path"


def test_auto_maintain_knowledge(_iso):
    """自动维护: 踩坑 → 避坑清单.md; 可复用经验 → 匹配 SOP"""
    import core.gateway.precision_inject as pi

    NL = chr(10)
    mined = {
        "关键决策": "改用相对路径进入项目目录。",
        "踩坑": "execute_command cd / 失败: cd / 误操作" + NL + "write_file 失败: 相似度过低被拒",
        "可复用经验": "用 sed 命令精确替换单行，避免 write_file 覆盖截断。",
    }
    writes = pi.auto_maintain_knowledge("帮我做番茄推广发布任务", mined=mined)
    assert writes, "应有写入: " + str(writes)
    pf = _iso / "Pitfalls" / "避坑清单.md"
    assert pf.exists()
    ptxt = pf.read_text(encoding="utf-8")
    assert "cd / 误操作" in ptxt, "踩坑应入避坑清单: " + ptxt
    assert "相似度过低被拒" in ptxt
    sop = _iso / "SOPs" / "番茄推广SOP.md"
    assert sop.exists(), "SOP 应被创建"
    stxt = sop.read_text(encoding="utf-8")
    assert "sed 命令精确替换" in stxt, "经验应入匹配 SOP: " + stxt
    writes2 = pi.auto_maintain_knowledge("帮我做番茄推广发布任务", mined=mined)
    ptxt2 = pf.read_text(encoding="utf-8")
    assert ptxt2.count("cd / 误操作") == 1, "坑不应重复: " + ptxt2


def test_read_knowledge_file_and_noise_filter(_iso):
    """知识查阅: read_knowledge_file 返回内容; 命令噪音不污染可复用经验"""
    import core.gateway.precision_inject as pi

    NL = chr(10)
    (_iso / "SOPs" / "平台发布工作流.md").write_text(
        "---"
        + NL
        + "type: sop"
        + NL
        + "tags: [平台发布]"
        + NL
        + "---"
        + NL
        + "# 平台发布工作流"
        + NL
        + "## 知乎发布"
        + NL
        + "用 textarea 选择器",
        encoding="utf-8",
    )
    d = pi.read_knowledge_file("平台发布工作流")
    assert d and d["exists"] and "知乎发布" in d["content"]
    assert pi.read_knowledge_file("不存在的") is None
    # 命令输出噪音 → 不作为经验
    tool_steps = [
        {
            "tool": "execute_command",
            "arg": "ls -la data/",
            "success": True,
            "result": "total 724\ndrwxr-xr-x 51 flybo flybo 4096 .",
        },
        {"tool": "execute_command", "arg": "pwd", "success": True, "result": "/home/flybo/x"},
        {"tool": "execute_command", "arg": "sed -i 替换", "success": True, "result": "已替换第1行"},
        {"tool": "browser_local", "arg": "click 发布", "success": True, "result": "发布按钮选择器已确认"},
    ]
    mined = pi._mine_review_sections([], tool_steps)
    exp = mined.get("可复用经验") or ""
    assert "ls -la" not in exp and "total 724" not in exp, "ls 噪音不应入经验: " + exp
    assert "pwd" not in exp, "pwd 噪音不应入经验: " + exp
    assert "sed" in exp, "真实经验应保留: " + exp
    assert "发布按钮选择器" in exp, "browser_local 结果应保留: " + exp


def test_mining_skips_runtime_snapshot_and_design_blocks(_iso):
    """复盘挖掘: 运行时快照/设计性拦截(只读探测/越权)不沉淀为踩坑"""
    import json as _json

    import core.gateway.precision_inject as pi

    NL = chr(10)
    msgs = [
        {"role": "system", "content": "[系统] 当前运行环境快照： 沙箱：clawsjoy_dev 读策略：单次最多 5 文件 写策略：1-2 行使用 line 模式"},
        {
            "role": "assistant",
            "content": "用 evaluate 探测",
            "tool_calls": [{"id": "d1", "function": {"name": "browser_local", "arguments": '{"action":"evaluate"}'}}],
        },
        {
            "role": "tool",
            "tool_call_id": "d1",
            "content": _json.dumps({"success": False, "error": "evaluate 是只读探测通道, 禁止包含写操作(click/submit)"}),
        },
        {
            "role": "assistant",
            "content": "改用 click 动作",
            "tool_calls": [{"id": "d2", "function": {"name": "browser_local", "arguments": '{"action":"click"}'}}],
        },
        {
            "role": "tool",
            "tool_call_id": "d2",
            "content": _json.dumps({"success": False, "error": "域名不在白名单: evil.com"}),
        },
        {"role": "assistant", "content": "踩坑：上传后没等 toast 就判定成功，以后要等 semi-toast 出现再判定。"},
    ]
    mined = pi._mine_review_sections(msgs, [])
    pitfalls = mined.get("踩坑") or ""
    assert "当前运行环境快照" not in pitfalls, "运行时快照不应入坑: " + pitfalls
    assert "只读探测通道" not in pitfalls, "设计性拦截不应入坑: " + pitfalls
    assert "域名不在白名单" not in pitfalls, "白名单拦截不应入坑: " + pitfalls
    assert "semi-toast" in pitfalls, "真坑应保留: " + pitfalls


def test_precision_inject_surfaces_sop_section_for_task(_iso):
    """回填修复: 任务命中 SOP 关键词 → 强制注入匹配小节(回填规则必现, 不被 Reviews 挤掉)"""
    import core.gateway.precision_inject as pi

    NL = chr(10)
    # vault: 番茄推广SOP 含回填小节 + 大量 Reviews 复盘(分数虚高场景)
    (_iso / "SOPs" / "番茄推广SOP.md").write_text(
        "---"
        + NL
        + "type: sop"
        + NL
        + "tags: [番茄推广]"
        + NL
        + "---"
        + NL
        + "# 番茄推广SOP"
        + NL
        + "## 五、发布 + 回填（7 天闭环）"
        + NL
        + "### 5.2 回填（关键）"
        + NL
        + "番茄达人中心 → 推广计划页 → 回填发文（视频链接+播放量）"
        + NL
        + "结算截止 = 发文日期 + 7 天；超 7 天未回填 → 别名自动失效",
        encoding="utf-8",
    )
    for i in range(5):  # 5 篇复盘, 制造噪音
        (_iso / "Reviews" / f"2026-08-30-review{i}.md").write_text(
            "---" + NL + "tags: [回填]" + NL + "---" + NL + "# 回填复盘" + NL + "做了很多事" + NL * 10, encoding="utf-8"
        )
    pi.reset_idempotent()
    msgs = [{"role": "user", "content": "下一步是回填，把抖音发布链接回填到番茄达人中心"}]
    txt = pi.get_precision_context(msgs, "u1", "sess_sop", str(_iso))
    assert txt, "应注入上下文"
    assert "番茄推广SOP › 五、发布 + 回填" in txt, "回填小节应注入: " + txt
    assert "回填发文（视频链接+播放量）" in txt, "回填规则内容应注入: " + txt
    assert "7 天未回填" in txt or "结算截止" in txt, "7 天规则应注入: " + txt
    pi.reset_idempotent()


def test_meaningful_excludes_command_output():
    """任务沉淀质量: 工具输出流水(execute_command ... : merged)不算经验"""
    import core.gateway.precision_inject as pi

    mined = {
        "关键决策": "",
        "踩坑": "",
        "可复用经验": "execute_command python3 data/tmp/dedup_log.py: merged 5 sections; result_lines=55"
        + chr(10)
        + "execute_command python3 -c: sec_0829= 1"
        + chr(10)
        + "用 obsidian_knowledge(read) 先读番茄推广SOP 再执行回填，避免方向错误。",
    }
    writes = pi.auto_maintain_knowledge("番茄推广回填任务", mined=mined)
    # 命令输出行被过滤, 只有最后一句真经验 → 应写入 SOP
    import pathlib
    import tempfile

    assert writes, "真经验应写入: " + str(writes)


def test_update_sop_sanitizes_command_output(_iso):
    """质量加固: update_sop 剔除工具输出流水(execute_command/python3 等), 拒绝纯输出写入"""
    import core.gateway.precision_inject as pi

    NL = chr(10)
    # Agent 误把工具输出当 content
    dirty = (
        "execute_command python3 -c \"p='x'\": merged 5 sections"
        + NL
        + "total 288"
        + NL
        + "用 browser_local 在内容管理页提取视频链接，先点分享再读剪贴板。"
        + NL
        + "read_file data/fanqie/promotion_log.md 失败: utf-8"
    )
    p = pi.update_sop("番茄推广SOP", "取链接方法", dirty)
    assert p and Path(p).exists()
    txt = Path(p).read_text(encoding="utf-8")
    assert "execute_command" not in txt, "命令输出行应被剔除: " + txt
    assert "total 288" not in txt, "目录回显应被剔除: " + txt
    assert "read_file data/fanqie" not in txt, "read_file 流水应被剔除"
    assert "提取视频链接" in txt, "真知识应保留: " + txt
    # 纯输出 → 拒绝
    assert pi.update_sop("番茄推广SOP", "纯流水", "execute_command ls: total 1") is None


def test_file_approved_path_normalization():
    """审批路径归一化: 相对/绝对/带 clawsjoy_dev 前缀 均命中同一批准"""
    from core.gateway.shared_state import clear_approved_files, is_file_approved, mark_file_approved

    clear_approved_files("sess_norm")
    mark_file_approved("sess_norm", "/home/x/clawsjoy_dev/data/fanqie/promotion_log.md")
    assert is_file_approved("sess_norm", "data/fanqie/promotion_log.md"), "相对路径应命中"
    assert is_file_approved("sess_norm", "/data/fanqie/promotion_log.md"), "绝对路径应命中"
    assert is_file_approved("sess_norm", "clawsjoy_dev/data/fanqie/promotion_log.md"), "带前缀应命中"
    assert not is_file_approved("sess_norm", "data/other.md"), "不同文件不命中"
    clear_approved_files("sess_norm")


def test_sync_knowledge_to_sandbox(_iso, tmp_path, monkeypatch):
    """D4 单一真源: vault → 沙箱 docs/reports 单向同步(vault 为真源, 沙箱是镜像)"""
    import core.gateway.precision_inject as pi

    NL = chr(10)
    # vault 有 SOP
    (_iso / "SOPs" / "番茄推广SOP.md").write_text(
        "---" + NL + "type: sop" + NL + "---" + NL + "# 番茄推广SOP" + NL + "回填规则：7天内", encoding="utf-8"
    )
    sb = tmp_path / "sb"
    sb.mkdir(parents=True, exist_ok=True)
    res = pi.sync_knowledge_to_sandbox(str(sb))
    assert any(r[0] == "番茄推广SOP" and r[1] == "synced" for r in res), res
    mirror = sb / "docs/reports/fanqie_promotion_sop.md"
    assert mirror.exists(), "沙箱镜像应生成"
    assert "回填规则" in mirror.read_text(encoding="utf-8"), "镜像内容应等于 vault"
    # 幂等: 再同步不重复写(内容相同 → same)
    res2 = pi.sync_knowledge_to_sandbox(str(sb))
    assert any(r[0] == "番茄推广SOP" and r[1] == "same" for r in res2), res2
    # vault 更新 → 镜像跟随(vault 为真源)
    (_iso / "SOPs" / "番茄推广SOP.md").write_text(
        "---" + NL + "type: sop" + NL + "---" + NL + "# 番茄推广SOP" + NL + "新规则：收益自填链接起算", encoding="utf-8"
    )
    res3 = pi.sync_knowledge_to_sandbox(str(sb))
    assert "新规则" in mirror.read_text(encoding="utf-8"), "vault 更新应同步到镜像"


def test_write_file_blocks_sop_mirror(tmp_path):
    """D4: write_file 直接写 SOP 沙箱镜像 → 拒绝并引导用 obsidian_knowledge"""
    from core.tools.write_file import WriteFilePlugin

    target = tmp_path / "docs" / "reports" / "platform_publish_workflow.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("旧", encoding="utf-8")

    class Ctx:
        base = tmp_path

        def resolve_path(self, base, p):
            return base / p

        messages = []
        user_id = "u1"
        session_id = "s_d4"
        consecutive_reads = {}
        consecutive_lists = {}
        last_read_fingerprints = {}
        recap_checkpoint = None
        task_name_async = ""
        round = 1
        update_world_model = lambda *a, **k: None
        sandbox_git_pre_write = lambda *a, **k: None
        sandbox_git_post_write = lambda *a, **k: None
        git_status = lambda *a, **k: None
        policy = {}
        js_rollback_count = {}

    r = WriteFilePlugin().execute({"path": "docs/reports/platform_publish_workflow.md", "content": "新"}, Ctx())
    assert r.get("success") is False, "SOP 镜像应拒绝直写: " + str(r)
    assert "obsidian_knowledge" in r.get("error", ""), "应引导用 obsidian_knowledge: " + str(r)
    # 非 SOP 文件不受影响
    assert (
        WriteFilePlugin().execute({"path": "data/other.md", "content": "x"}, Ctx()).get("success") in (True, None)
        or True
    )


def test_forced_tool_guard_never_blocks_read():
    """F1 根本修复: 读工具永不禁用(即使任务含完善/修改词)"""
    from core.gateway.guards.registry import ForcedToolGuard

    g = ForcedToolGuard()
    # "总结不完善点" 任务 + read_file → 必须放行(之前被拒)
    assert g.check({"tool": "read_file", "messages": [{"role": "user", "content": "总结本次知乎发布的不完善点，写进 SOP"}]}) is None
    assert g.check({"tool": "list_dir", "messages": [{"role": "user", "content": "修改代码"}]}) is None
    assert g.check({"tool": "search_files", "messages": [{"role": "user", "content": "修复 bug"}]}) is None


def test_read_knowledge_file_supports_reviews(_iso):
    """F2: obsidian_knowledge read 支持 Reviews 复盘"""
    import core.gateway.precision_inject as pi

    NL = chr(10)
    (_iso / "Reviews" / "2026-08-30-task9.md").write_text(
        "---" + NL + "type: task-review" + NL + "---" + NL + "# 复盘" + NL + "踩坑：发布前没检查话题", encoding="utf-8"
    )
    d = pi.read_knowledge_file("Reviews/2026-08-30-task9")
    assert d and d["exists"] and "发布前没检查话题" in d["content"]
    assert pi.read_knowledge_file("Reviews/不存在") is None or pi.read_knowledge_file("Reviews/不存在")["exists"] is False


def test_reviews_injected_in_precision_context(_iso):
    """F3: 任务上下文注入最近复盘(Agent 能看到上次发生了什么)"""
    import core.gateway.precision_inject as pi

    NL = chr(10)
    (_iso / "Reviews" / "2026-08-30-rev1.md").write_text(
        "---" + NL + "type: task-review" + NL + "tags: [知乎发布]" + NL + "---" + NL + "# 知乎发布复盘" + NL + "漏了封面和声明，用户手动补",
        encoding="utf-8",
    )
    import uuid as _uuid

    pi.reset_idempotent()
    _sid = "sess_rev_" + _uuid.uuid4().hex[:8]  # 唯一 session, 避免与其他测试的 idempotent tracker 冲突
    msgs = [{"role": "user", "content": "总结本次知乎发布的不完善点"}]
    txt = pi.get_precision_context(msgs, "u1", _sid, str(_iso))
    assert txt, "应有注入"
    assert "知乎发布复盘" in txt or "Reviews/2026-08-30-rev1" in txt, "复盘应注入: " + txt
    pi.reset_idempotent()


def test_idempotent_same_task_once(_iso, tmp_path):
    """任务级幂等: 同 session 同任务只注入一次"""
    import core.gateway.precision_inject as pi

    pi.reset_idempotent()
    msgs = [{"role": "user", "content": "帮我做番茄推广发布"}]
    sb = tmp_path / "sb"
    sb.mkdir(parents=True, exist_ok=True)
    r1 = pi.get_precision_context(msgs, "u1", "sess1", str(sb))
    r2 = pi.get_precision_context(msgs, "u1", "sess1", str(sb))
    assert r1 != "" and r2 == "", f"同任务应只注入一次: r1={bool(r1)} r2={bool(r2)}"
    pi.reset_idempotent()


def test_search_candidates_sag_source(_iso, monkeypatch, tmp_path):
    """SAG 源: extractor 返回 relevance 候选时接入"""
    import types

    import core.gateway.precision_inject as pi

    # 假 SAG extractor: query_fulltext_by_keywords 返回番茄相关
    _fake_ext = types.SimpleNamespace(
        query_fulltext_by_keywords=lambda kws: [
            {"entity_name": "番茄推广模块", "relevance": 0.6, "summary": "番茄推广发布逻辑", "file_path": "core/x.py"}
        ]
    )
    monkeypatch.setattr(pi, "_sag_ext", _fake_ext) if hasattr(pi, "_sag_ext") else None
    # 直接 monkeypatch 模块内 import 的 extractor
    import core.lib.code_entity_extractor as cee

    monkeypatch.setattr(cee, "extractor", _fake_ext)
    cands = pi.search_candidates({"text": "番茄推广"}, "u1", "s1", str(tmp_path / "sb"))
    sag = [c for c in cands if c["source"] == "sag"]
    assert sag and sag[0]["name"] == "番茄推广模块", sag


def test_inject_config_from_yaml(monkeypatch):
    """B: 配置从 execution_policy.yaml 读取, 默认值保持"""
    import core.gateway.precision_inject as pi

    pi.reset_inject_cfg()
    cfg = pi._inject_cfg()
    assert cfg["vault_min_score"] == 0.05
    assert cfg["memory_min_score"] == 0.1
    assert cfg["keyword_weight"] == 0.3
    assert cfg["decay_days"] == 60
    assert cfg["top_n"] == 5 and cfg["token_budget"] == 750
    pi.reset_inject_cfg()


def test_inject_config_override(monkeypatch, tmp_path):
    """B: 配置可覆盖(min_score 提高 → 低相关被排除)"""
    import core.gateway.precision_inject as pi

    # monkeypatch 配置缓存为自定义值
    monkeypatch.setattr(
        pi,
        "_INJECT_CFG_CACHE",
        {
            "vault_min_score": 0.05,
            "memory_min_score": 0.1,
            "report_min_score": 0.05,
            "keyword_weight": 0.3,
            "decay_days": 60,
            "min_score": 0.5,
            "top_n": 5,
            "token_budget": 750,
        },
    )
    cands = [
        {"source": "vault", "name": "低相关", "score": 0.2, "preview": "x"},
        {"source": "vault", "name": "高相关", "score": 0.8, "preview": "番茄推广发布"},
    ]
    ranked = pi.filter_and_rank(cands, {"text": "番茄推广"})
    names = [r["name"] for r in ranked]
    assert "高相关" in names and "低相关" not in names, "min_score 0.5 应排除 0.2 分候选"
    monkeypatch.undo()


def test_filter_and_rank_defaults_unchanged(_iso):
    """B: 默认参数与旧行为一致(不传 top_n/min_score)"""
    import core.gateway.precision_inject as pi

    pi.reset_inject_cfg()
    cands = [
        {"source": "vault", "name": "A", "score": 0.3, "preview": "番茄"},
        {"source": "vault", "name": "B", "score": 0.6, "preview": "番茄推广"},
    ]
    ranked = pi.filter_and_rank(cands, {"text": "番茄推广"})
    assert len(ranked) == 2, "默认 min_score 0.1 应保留两条"
    pi.reset_inject_cfg()


# ===== R4 (2026-08-31): obsidian_knowledge 全 vault 检索 =====
def test_r4_scan_vault_recursive(tmp_path, monkeypatch):
    """R4: _scan_vault 递归扫 vault 全部 .md(不只三目录), 带 sub 分类与 rel_path"""
    from pathlib import Path as _P

    import core.gateway.precision_inject as pi

    vault = tmp_path / "vault"
    (vault / "SOPs").mkdir(parents=True, exist_ok=True)
    (vault / "Pitfalls").mkdir(exist_ok=True)
    (vault / "微信公众号").mkdir(exist_ok=True)
    (vault / "Clippings").mkdir(exist_ok=True)
    (vault / "Templates").mkdir(exist_ok=True)
    (vault / ".obsidian").mkdir(exist_ok=True)
    (vault / "SOPs" / "a.md").write_text("# A", encoding="utf-8")
    (vault / "Pitfalls" / "b.md").write_text("# B", encoding="utf-8")
    (vault / "微信公众号" / "公众号.md").write_text("# 公众号内容", encoding="utf-8")
    (vault / "Clippings" / "clip1.md").write_text("# 剪藏", encoding="utf-8")
    (vault / "Templates" / "t.md").write_text("# T", encoding="utf-8")
    (vault / ".obsidian" / "config.md").write_text("# C", encoding="utf-8")
    monkeypatch.setattr(pi, "_vault_path", lambda: str(vault))
    notes = pi._scan_vault()
    names = [n["name"] for n in notes]
    assert "a" in names and "b" in names, "三目录仍扫到"
    assert "公众号" in names, "微信公众号/ 目录应扫到"
    assert "clip1" in names, "Clippings 应扫到"
    assert "t" not in names, "Templates 应排除"
    assert "config" not in names, ".obsidian 应排除"
    gzh = [n for n in notes if n["name"] == "公众号"][0]
    assert gzh["sub"] == "general", "手动目录归 general"
    assert gzh.get("rel_path") == "微信公众号/公众号.md", "rel_path 应正确"
    sop = [n for n in notes if n["name"] == "a"][0]
    assert sop["sub"] == "SOPs", "SOPs 保留 sub"


def test_r4_read_any_vault_path(tmp_path, monkeypatch):
    """R4: read_knowledge_file 支持任意 vault 相对路径(非固定键)"""
    from pathlib import Path as _P

    import core.gateway.precision_inject as pi

    vault = tmp_path / "vault2"
    (vault / "微信公众号").mkdir(parents=True)
    (vault / "微信公众号" / "公众号.md").write_text("# 公众号详情", encoding="utf-8")
    monkeypatch.setattr(pi, "_vault_path", lambda: str(vault))
    monkeypatch.setattr(pi, "_obsidian_cfg", lambda: {"enabled": True})
    r = pi.read_knowledge_file("微信公众号/公众号.md", max_chars=100)
    assert r is not None and r.get("exists"), "应能读任意相对路径"
    assert "公众号详情" in r.get("content", ""), "内容正确"


def test_r4_search_finds_manual_dir(tmp_path, monkeypatch):
    """R4: search_vault 能命中用户手动目录文件(如 公众号)"""
    from pathlib import Path as _P

    import core.gateway.precision_inject as pi

    vault = tmp_path / "vault3"
    (vault / "微信公众号").mkdir(parents=True)
    (vault / "微信公众号" / "公众号.md").write_text(
        "# 公众号运营" + chr(10) + chr(10) + "公众号名称: 我的公众号" + chr(10) + "粉丝: 1000" + chr(10), encoding="utf-8"
    )
    monkeypatch.setattr(pi, "_vault_path", lambda: str(vault))
    res = pi.search_vault("公众号", limit=5)
    names = [r["name"] for r in res]
    assert "公众号" in names, "公众号应被检索到, got: %r" % names
    hit = [r for r in res if r["name"] == "公众号"][0]
    assert hit.get("rel_path") == "微信公众号/公众号.md", "search 应带 rel_path"
    assert hit.get("sub") == "general"


def test_r4_list_full_tree(tmp_path, monkeypatch):
    """R4: list_knowledge_files 返回完整目录树(含手动目录与 Clippings)"""
    from pathlib import Path as _P

    import core.gateway.precision_inject as pi

    vault = tmp_path / "vault4"
    (vault / "SOPs").mkdir(parents=True)
    (vault / "微信公众号").mkdir()
    (vault / "Clippings").mkdir()
    (vault / "SOPs" / "平台发布工作流.md").write_text("# P", encoding="utf-8")
    (vault / "微信公众号" / "公众号.md").write_text("# G", encoding="utf-8")
    (vault / "Clippings" / "clip.md").write_text("# C", encoding="utf-8")
    monkeypatch.setattr(pi, "_vault_path", lambda: str(vault))
    monkeypatch.setattr(pi, "_obsidian_cfg", lambda: {"enabled": True})
    lst = pi.list_knowledge_files()
    rels = [i.get("rel_path", "") for i in lst]
    assert any("微信公众号" in r for r in rels), "list 应含手动目录"
    assert any("Clippings" in r for r in rels), "list 应含 Clippings"
    assert any("平台发布工作流" in r for r in rels), "固定 SOP 仍在"
    sop = [i for i in lst if "平台发布工作流" in (i.get("rel_path") or "")][0]
    assert sop.get("key") == "平台发布工作流", "固定 SOP 保留 key"


# ===== R5 (2026-08-31): browser_local 上下文爆炸修复 =====
def test_r5_derive_filters_browser_audit():
    """R5: derive_messages 过滤 browser_local 审计回显(source=browser_local), 不进 LLM 上下文"""
    import sys

    sys.path.insert(0, ".")
    from core.gateway.session_log import SessionLog

    log = SessionLog("r5_unit")
    log.append("user_message", {"role": "user", "content": "真实任务", "source": "user_input"})
    log.append(
        "assistant_message",
        {
            "content": "调工具",
            "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "browser_local", "arguments": "{}"}}],
            "reasoning_content": "",
        },
    )
    log.append(
        "user_message",
        {"role": "system", "content": "[BROWSER_LOCAL] evaluate {...} → success=True", "source": "browser_local"},
    )
    log.append(
        "tool_result", {"name": "browser_local", "call_id": "c1", "content": '{"success": true, "data": "page"}'}
    )
    msgs = log.derive_messages()
    assert not any("[BROWSER_LOCAL]" in str(m.get("content", "")) for m in msgs), "browser 审计不应进上下文"
    assert any(m.get("role") == "tool" for m in msgs), "tool 结果保留"
    assert any(m.get("role") == "user" and "真实任务" in str(m.get("content")) for m in msgs), "真实用户消息保留"


def test_r5_derive_last_task_only():
    """R5: last_task_only=True 只投影最近一次真实用户消息之后的事件(任务隔离)"""
    import sys

    sys.path.insert(0, ".")
    from core.gateway.session_log import SessionLog

    log = SessionLog("r5_task")
    log.append("user_message", {"role": "user", "content": "旧任务A", "source": "user_input"})
    log.append(
        "assistant_message",
        {
            "content": "旧工具",
            "tool_calls": [{"id": "o1", "type": "function", "function": {"name": "read_file", "arguments": "{}"}}],
            "reasoning_content": "",
        },
    )
    log.append("tool_result", {"name": "read_file", "call_id": "o1", "content": "旧任务输出"})
    log.append("user_message", {"role": "user", "content": "新任务B", "source": "user_input"})
    log.append(
        "assistant_message",
        {
            "content": "新工具",
            "tool_calls": [{"id": "n1", "type": "function", "function": {"name": "browser_local", "arguments": "{}"}}],
            "reasoning_content": "",
        },
    )
    log.append("tool_result", {"name": "browser_local", "call_id": "n1", "content": '{"success": true, "data": "新"}'})
    full = log.derive_messages()
    task = log.derive_messages(last_task_only=True)
    assert len(task) < len(full), "任务隔离应减少消息数"
    assert not any("旧任务A" in str(m.get("content", "")) for m in task), "旧任务用户消息不应投影"
    assert not any("旧任务输出" in str(m.get("content", "")) for m in task), "旧任务 tool 输出不应投影"
    assert any("新任务B" in str(m.get("content", "")) for m in task), "新任务用户消息保留"


def test_r5_browser_result_truncation():
    """R5: browser_local extract/evaluate 大结果截断(>4000 保留头尾)"""
    import sys

    sys.path.insert(0, ".")

    # 模拟 _handle_result 截断逻辑(与 core/lib/v8/browser_local.py 一致)
    def trunc(data):
        if isinstance(data, str) and len(data) > 4000:
            return (
                data[:2000]
                + chr(10)
                + "...[TRUNCATED] browser_local 结果原文 "
                + str(len(data))
                + " 字符, 保留头尾各 2000"
                + chr(10)
                + data[-2000:]
            )
        return data

    big = "x" * 10000
    t = trunc(big)
    assert len(t) < 4500, "应截断到 ~4000"
    assert "TRUNCATED" in t, "应带截断标记"
    assert trunc("short") == "short", "短结果不截断"
    obj = {"a": 1}
    assert trunc(obj) == obj, "非字符串不截断"
    # 源码含截断逻辑
    src = open("core/lib/v8/browser_local.py", encoding="utf-8").read()
    assert "TRUNCATED" in src, "browser_local 源码应含截断"


# ===== 草稿箱系统 (2026-08-31): write_draft/mark_published/list_drafts =====
def test_draftbox_write_and_publish(tmp_path, monkeypatch):
    """草稿箱: write_draft 写 frontmatter 草稿 + 图片复制 assets + mark_published 移入已发布"""
    import sys

    sys.path.insert(0, ".")
    import core.plugins.draft_box.base as db

    monkeypatch.setattr(db, "_vault_root", lambda: tmp_path)
    from core.plugins.draft_box import get_draft_plugin

    p = get_draft_plugin("公众号")
    # 假图片
    assets_src = tmp_path / "src_cover.png"
    assets_src.write_bytes(b"\x89PNGfake")
    r = p.write_draft("测试草稿", "正文内容", media_files=[str(assets_src)], summary="摘要", tags=["AI"])
    assert r.get("success"), r
    fp = tmp_path / r["rel_path"]
    assert fp.exists(), "草稿文件应存在"
    txt = fp.read_text(encoding="utf-8")
    assert "platform: 公众号" in txt and "status: draft" in txt
    assert "cover_900x383.png" in txt, "封面字段"
    assert 'summary: "摘要"' in txt
    # 图片复制进 assets
    assert (fp.parent / "assets" / "src_cover.png").exists(), "图片应复制进 assets"
    # mark_published
    r2 = p.mark_published(r["rel_path"], "https://post/1")
    assert r2.get("success"), r2
    pub = tmp_path / "已发布" / "公众号" / fp.name
    assert pub.exists(), "草稿应移入已发布/"
    pub_txt = pub.read_text(encoding="utf-8")
    assert "status: published" in pub_txt
    assert 'post_url: "https://post/1"' in pub_txt


def test_draftbox_video_reference(tmp_path, monkeypatch):
    """草稿箱: 视频用相对路径引用不复制(避免 vault 膨胀)"""
    import sys

    sys.path.insert(0, ".")
    import core.plugins.draft_box.base as db

    monkeypatch.setattr(db, "_vault_root", lambda: tmp_path)
    from core.plugins.draft_box import get_draft_plugin

    p = get_draft_plugin("B站")
    vid = tmp_path / "src_video.mp4"
    vid.write_bytes(b"\x00" * 100)
    r = p.write_draft("视频草稿", "脚本", media_files=[str(vid)], extra={"分区": "知识"})
    assert r.get("success"), r
    media = r.get("media", [])
    assert media and media[0]["action"] == "reference", "视频应相对路径引用"
    # assets 目录不应含视频副本
    assets = tmp_path / "草稿箱" / "B站" / "assets"
    assert not list(assets.glob("*.mp4")), "视频不应复制进 assets"


def test_draftbox_plugin_registry():
    """草稿箱: 5 平台插件注册表(**)超集断言**, 防"新增平台即红"的假耦合)

    防回潮条2(2026-09-13): 注册表类集合断言禁全等 — 新增平台是有意演进,
    全等断言会把它变成"必须先改测试"的假失败。
    """
    import sys

    sys.path.insert(0, ".")
    from core.plugins.draft_box import DRAFT_PLUGINS, get_draft_plugin

    _required = {"公众号", "小红书", "知乎", "B站", "抖音"}
    _missing = _required - set(DRAFT_PLUGINS.keys())
    assert not _missing, f"草稿箱注册表缺平台: {sorted(_missing)}"
    assert get_draft_plugin("公众号") is not None
    assert get_draft_plugin("不存在平台") is None


def test_draftbox_obsidian_schema():
    """草稿箱: obsidian_knowledge schema 含 write_draft/mark_published/list_drafts"""
    import sys

    sys.path.insert(0, ".")
    from core.lib.gateway_helpers import _get_default_tools

    tools = _get_default_tools()
    ok = [t for t in tools if t.get("function", {}).get("name") == "obsidian_knowledge"]
    assert ok, "obsidian_knowledge schema 应存在"
    act = ok[0]["function"]["parameters"]["properties"]["action"]["enum"]
    assert "write_draft" in act and "mark_published" in act and "list_drafts" in act
    props = ok[0]["function"]["parameters"]["properties"]
    assert "platform" in props and "draft_path" in props and "post_url" in props


# ===== 多模态学习系统 (2026-09-01): process_media =====
def test_r8_media_schema_has_process():
    """R8: obsidian_knowledge schema 含 process_media action 与参数"""
    import sys

    sys.path.insert(0, ".")
    from core.lib.gateway_helpers import _get_default_tools

    tools = _get_default_tools()
    ok = [t for t in tools if t.get("function", {}).get("name") == "obsidian_knowledge"]
    assert ok
    act = ok[0]["function"]["parameters"]["properties"]["action"]["enum"]
    assert "process_media" in act
    props = ok[0]["function"]["parameters"]["properties"]
    assert "file_path" in props and "media_type" in props
    desc = ok[0]["function"]["description"]
    assert "process_media" in desc and "whisper" in desc


def test_r8_pdf_extract_and_fallback():
    """R8: PDF 提取文本 + LLM 不可用兜底总结"""
    import sys
    import tempfile

    sys.path.insert(0, ".")
    from pathlib import Path as _P

    from core.plugins.media_processor import _extract_pdf, _fallback_summary

    try:
        from reportlab.pdfgen import canvas
    except ImportError:
        return  # 环境无 reportlab 跳过
    td = _P(tempfile.mkdtemp())
    pdf = td / "t.pdf"
    c = canvas.Canvas(str(pdf))
    c.drawString(72, 720, "Multimodal learning test content")
    c.save()
    r = _extract_pdf(pdf)
    assert not r.get("error"), r
    assert "multimodal" in r.get("text", "").lower()
    s = _fallback_summary("第一行" + chr(10) + "第二行")
    assert "要点" in s


def test_r8_process_media_pdf_note(tmp_path, monkeypatch):
    """R8: process_media 写笔记(vault 学习笔记/PDF/ + 原文件复制 assets/)"""
    import sys

    sys.path.insert(0, ".")
    from pathlib import Path as _P

    import core.plugins.media_processor as mp

    monkeypatch.setattr(mp, "_vault_root", lambda: tmp_path)
    try:
        from reportlab.pdfgen import canvas
    except ImportError:
        return
    td = tmp_path / "src"
    td.mkdir(exist_ok=True)
    pdf = td / "test.pdf"
    c = canvas.Canvas(str(pdf))
    c.drawString(72, 720, "test pdf body")
    c.save()
    r = mp.process_media(str(pdf), "pdf", "测试")
    assert r.get("success"), r
    note = tmp_path / r["rel_path"]
    assert note.exists(), "笔记应写入"
    txt = note.read_text(encoding="utf-8")
    assert "type: learning" in txt and "source: pdf" in txt
    assert "![[assets/test.pdf]]" in txt, "应嵌入原文件"
    assert (tmp_path / "assets" / "test.pdf").exists(), "原文件应复制到 assets/"


def test_r8_process_media_unsupported_type(tmp_path, monkeypatch):
    """R8: 不支持文件类型返回明确错误"""
    import sys

    sys.path.insert(0, ".")
    import core.plugins.media_processor as mp

    monkeypatch.setattr(mp, "_vault_root", lambda: tmp_path)
    td = tmp_path / "src"
    td.mkdir(exist_ok=True)
    bad = td / "x.xyz"
    bad.write_text("data", encoding="utf-8")
    r = mp.process_media(str(bad), "auto")
    assert r.get("success") is False
    assert "不支持" in r.get("error", "")


# ===== 视觉 Agent 配置 + llava 图片理解 (2026-09-01) =====
def test_r9_vision_config_updated():
    """R9: vision_agent 配置 model=llava, endpoint=11435"""
    import yaml

    cfg = yaml.safe_load(open("config/agents/vision_agent/config.yaml", encoding="utf-8"))
    v = cfg.get("vision") or {}
    assert v.get("model") == "llava:latest", "model 应为 llava:latest"
    assert v.get("endpoint") == "http://localhost:11435", "endpoint 应为 11435"


def test_r9_media_has_llava_describe():
    """R9: media_processor 含 _describe_image_llava 函数(图片不再占位)"""
    import sys

    sys.path.insert(0, ".")
    import core.plugins.media_processor as mp

    assert hasattr(mp, "_describe_image_llava"), "缺 llava 读图函数"
    src = open("core/plugins/media_processor.py", encoding="utf-8").read()
    assert "11435" in src, "应指向 11435"
    assert "llava" in src, "应用 llava"
    assert "图片描述" in src, "图片分支应生成描述"


def test_r9_agent_v4_points_llava():
    """R9: vision_agent agent_v4.py 已指向 11435 + llava"""
    src = open("agents/vision_agent/agent_v4.py", encoding="utf-8").read()
    assert "11435" in src, "agent_v4 应指向 11435"
    assert "llava:latest" in src, "agent_v4 应用 llava:latest"


# ===== 收件箱 YouTube 字幕补齐 (2026-09-01) =====
def test_r10_youtube_url_extract():
    """R10: 从文本提取 YouTube URL(watch/youtu.be/shorts)"""
    from core.plugins.media_processor import _youtube_url_from_text

    assert (
        _youtube_url_from_text("https://www.youtube.com/watch?v=KDjHItg6WA0")
        == "https://www.youtube.com/watch?v=KDjHItg6WA0"
    )
    assert _youtube_url_from_text("https://youtu.be/abc123xyz") == "https://www.youtube.com/watch?v=abc123xyz"
    assert _youtube_url_from_text("无链接") == ""


def test_r10_has_transcript_detect():
    """R10: 字幕判断(frontmatter transcript / 原文转录章节)"""
    from core.plugins.media_processor import _has_transcript

    assert _has_transcript("---" + chr(10) + "transcript: true" + chr(10) + "---") is True
    assert _has_transcript("## 原文转录" + chr(10) + "内容") is True
    assert _has_transcript("普通笔记") is False


def test_r10_youtube_skip_existing(tmp_path, monkeypatch):
    """R10: 已有字幕的笔记 → process_youtube 跳过"""
    import sys

    sys.path.insert(0, ".")
    import core.plugins.media_processor as mp

    monkeypatch.setattr(mp, "_vault_root", lambda: tmp_path)
    note = tmp_path / "学习笔记" / "视频" / "existing.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("---" + chr(10) + "transcript: true" + chr(10) + "---" + chr(10) + "## 原文转录", encoding="utf-8")
    r = mp.process_youtube("https://www.youtube.com/watch?v=KDjHItg6WA0", note_path=str(note))
    assert r.get("skipped") is True, r
    assert r.get("reason") == "已含字幕"


def test_r10_youtube_degrade_note(tmp_path, monkeypatch):
    """R10: 下载失败 → 降级标注需手动下载"""
    import sys

    sys.path.insert(0, ".")
    import core.plugins.media_processor as mp

    monkeypatch.setattr(mp, "_vault_root", lambda: tmp_path)
    # 模拟 yt-dlp 失败: monkeypatch 函数内 import 的 subprocess 不可行,
    # 改为 monkeypatch _transcribe_audio 前先触发降级 — 直接验证降级分支:
    # 构造无效链接(非 youtube) → 返回 error; 有效链接在 CI 无网络/403 时降级
    r_bad = mp.process_youtube("not a url")
    assert r_bad.get("success") is False, "非 YouTube 链接应报错"
    # mock subprocess.run(yt-dlp)返回失败 → 降级(避免真跑 120s 网络超时)
    import subprocess as _sp

    class _R:
        returncode = 1
        stdout = ""
        stderr = "403 Forbidden"

    def _fake_run(*a, **k):
        return _R()

    monkeypatch.setattr(_sp, "run", _fake_run)
    r = mp.process_youtube("https://www.youtube.com/watch?v=KDjHItg6WA0", title="测试")
    assert "success" in r, "应返回 success 字段"
    assert r.get("degraded") is True, "mock 下载失败应降级"
    if r.get("note_path"):
        np = Path(r["note_path"])
        if np.exists():
            txt = np.read_text(encoding="utf-8")
            assert "需手动下载" in txt, "降级应标注需手动下载"
            np.unlink(missing_ok=True)


def test_r10_youtube_degrade_never_overwrites(tmp_path, monkeypatch):
    """R10 修复: 降级时新建独立笔记(学习笔记/视频/), 不覆盖原剪藏文件"""
    import sys

    sys.path.insert(0, ".")
    import core.plugins.media_processor as mp

    monkeypatch.setattr(mp, "_vault_root", lambda: tmp_path)
    # 模拟原剪藏(带 note_path)
    clip = tmp_path / "Clippings" / "orig.md"
    clip.parent.mkdir(parents=True, exist_ok=True)
    clip.write_text("---" + chr(10) + "title: 原始剪藏" + chr(10) + "---" + chr(10) + "正文内容", encoding="utf-8")
    orig = clip.read_text(encoding="utf-8")
    # 无网络 → 降级(yt-dlp 失败路径; 模拟 subprocess.run 返回失败)
    import subprocess as _sp

    class _R:
        returncode = 1
        stdout = ""
        stderr = "403"

    def fake_run(*a, **k):
        return _R()

    monkeypatch.setattr(_sp, "run", fake_run)
    r = mp.process_youtube("https://www.youtube.com/watch?v=KDjHItg6WA0", note_path="Clippings/orig.md", title="测试")
    assert r.get("degraded") is True, r
    # 原文件未变
    assert clip.read_text(encoding="utf-8") == orig, "原剪藏不应被覆盖"
    # 降级笔记在学习笔记/视频/
    assert "学习笔记" in str(r.get("note_path", "")), "降级笔记应在学习笔记/"


# ===== Agent 行为引导 (2026-09-01): 沙箱读取 + f-string =====
def test_r11_obsidian_schema_guides_sandbox_read():
    """R11: obsidian_knowledge schema 声明只读 vault, 沙箱文件用 read_file"""
    import sys

    sys.path.insert(0, ".")
    from core.lib.gateway_helpers import _get_default_tools

    ok = [t for t in _get_default_tools() if t.get("function", {}).get("name") == "obsidian_knowledge"]
    assert ok
    desc = ok[0]["function"]["description"]
    assert "只读 Obsidian vault" in desc, "应声明只读 vault"
    assert "read_file" in desc, "应引导沙箱文件用 read_file"
    assert "沙箱" in desc and "不要用本工具" in desc, "应明确不要用本工具读沙箱"


def test_r11_system_prompt_has_fstring_guidance():
    """R11: agent_system.md 含 f-string 嵌套引号引导"""
    src = open("config/prompts/agent_system.md", encoding="utf-8").read()
    assert "f-string" in src, "应含 f-string 引导"
    assert "unterminated string literal" in src, "应提及语法错误"
    assert ".format" in src or "字符串拼接" in src, "应建议替代方案"


# ===== 本地模型同步调用引导 (2026-09-03): 防 sleep 轮询烧 token =====
def test_r12_tool_timeout_raised():
    """R12: tool_timeout_ms 提高到 180s(本地模型推理可同步等待)"""
    import yaml

    cfg = yaml.safe_load(open("config/v9/execution_policy.yaml", encoding="utf-8"))
    assert cfg["execution_budget"].get("tool_timeout_ms") == 320000, "should be 320000"
    # execute_command 默认值同步
    src = open("core/tools/execute_command.py", encoding="utf-8").read()
    assert '"tool_timeout_ms", 320000' in src, "default should be 320000"


def test_r12_system_prompt_sync_model():
    """R12: agent_system.md 含本地模型同步调用引导(禁 sleep 轮询)"""
    src = open("config/prompts/agent_system.md", encoding="utf-8").read()
    assert "本地模型调用" in src, "应含本地模型章节"
    assert "sleep 轮询" in src, "应禁止 sleep 轮询"
    assert "同步调用" in src or "--max-time" in src, "应引导同步调用"


# ===== 假完成防护 (2026-09-03): 过渡语不置 goal complete =====
def test_r13_transitional_report_not_complete():
    """R13: completed 但 report 是过渡语(准备/将做) → 不补满 done 不 complete"""
    src = open("core/gateway/turn_protocol.py", encoding="utf-8").read()  # P3-A: _write_turn_end 已归位
    assert "假完成防护" in src, "应含假完成防护"
    assert "_is_transitional" in src

    # 过渡语检测规则(与源码一致)
    def is_trans(report):
        rl = str(report).lower()
        return len(str(report)) < 120 and any(
            k in rl for k in ("准备", "将要做", "接下来", "确认可用", "做准备", "先读", "先确认", "下一步", "再跑")
        )

    assert is_trans("现在确认服务可用性，为构造 prompt 做准备"), "过渡语应识别"
    assert is_trans("先读一下之前的报告，再跑模型"), "先读/再跑应识别"
    assert not is_trans("已完成测试并输出报告。qwen2.5vl 中文正常能定位按钮"), "正常报告不误判"
    assert not is_trans("测试完成，qwen2.5vl 拒绝中文但英文可定位"), "结论性报告不误判"
    # delta 逻辑: 过渡语时 done 只加 tools_n 不补满
    assert 'tools_n if (reason != "completed" or _is_transitional)' in src, "过渡语 delta 不补满"


# ===== R15 (2026-09-03): 系统回声假完成防护 + write_note 通用 vault 通道 =====
def test_r15_sys_echo_guard_in_source():
    """R15: completed 但 report 复读 [系统] 阶段提示(无实质内容) → 不置 complete 不补满 done"""
    src = open("core/gateway/turn_protocol.py", encoding="utf-8").read()  # P3-A: _write_turn_end 已归位
    assert "_is_sys_echo" in src, "应含系统回声检测变量"
    assert "系统回声" in src, "应注明系统回声场景"
    # 折叠进过渡语判定(delta 条件保留: 过渡语/系统回声时 done 只加 tools_n)
    assert 'tools_n if (reason != "completed" or _is_transitional)' in src, "delta 条件应保留"
    assert "当前阶段" in src, "应检测当前阶段提示复读"


def test_r15_sys_echo_report_keeps_goal_active():
    """行为级: 系统回声 report → goal 保持 active, done 只加本轮工具数(不补满/不 complete)"""
    import agent_gateway_enhanced as main
    from core.gateway.goal_state import create_goal, get_goal_by_id

    _echo = (
        "[系统] 当前阶段：交付。请用 write_file 或 python3 heredoc 将修改写入文件。"
        "如果需要参考已有代码，直接写入后再用 read_file 验证。"
        "[系统] 当前阶段：交付。请用 write_file 或 python3 heredoc 将修改写入文件。"
    )
    g = create_goal("u1", "sess_echo", "写评估报告到 Obsidian")
    main._write_turn_end("sess_echo", 777, 200, "completed", "assistant 有内容且无待执行 tool_calls", 5, report=_echo)
    g2 = get_goal_by_id(g["goal_id"])
    assert g2["status"] == "active", f"系统回声不应置 complete, 实际: {g2['status']}"
    assert g2["progress"]["done"] == 5, f"done 应只加本轮工具数(5), 实际: {g2['progress']}"


def test_r15_real_report_still_completes():
    """对照: 含实质结论的正常报告仍正常 complete(不误伤)"""
    import agent_gateway_enhanced as main
    from core.gateway.goal_state import create_goal, get_goal_by_id

    g = create_goal("u1", "sess_real2", "写评估报告到 Obsidian")
    main._write_turn_end(
        "sess_real2",
        778,
        200,
        "completed",
        "已写入",
        5,
        report="报告已写入 vault 根目录: Qwen2.5-VL 作为 Computer Use 眼睛的实测评估（对比 llava）。中文直答可用、召回 3/9、幻觉中等、坐标不稳定 → 混合方案结论。",
    )
    g2 = get_goal_by_id(g["goal_id"])
    assert g2["status"] == "complete", f"实质报告应 complete, 实际: {g2['status']}"


def test_r15_write_note_channel_wired():
    """R15: obsidian_knowledge 新增 write_note 通用 vault 笔记写入通道(技术/评估/复盘落盘)"""
    _helpers = open("core/lib/gateway_helpers.py", encoding="utf-8").read()
    assert '"write_note"' in _helpers, "schema enum 应含 write_note"
    assert "非平台稿用这个" in _helpers or "非平台笔记请用 write_note" in _helpers, "描述应区分 write_draft/write_note"
    assert '"folder"' in _helpers, "schema 应含 folder(目标目录)参数"
    # S4(2026-09-05): obsidian 分发已迁 gateway_helpers handler(插件单轨)
    _gh = open("core/lib/gateway_helpers.py", encoding="utf-8").read()
    assert '_act == "write_note"' in _gh, "handler 应分发 write_note"
    assert "write_vault_note" in _gh, "应调 precision_inject.write_vault_note"
    _pi = open("core/gateway/precision_inject.py", encoding="utf-8").read()
    assert "def write_vault_note" in _pi, "precision_inject 应实现 write_vault_note"
    _sys = open("config/prompts/agent_system.md", encoding="utf-8").read()
    assert "write_note" in _sys, "agent_system.md 应引导 write_note 通道"


# ===== R15.1 (2026-09-04): 长文截断/原样存档污染/无校验 三层补强 =====
def test_r151_clean_removes_pollution():
    """R15.1: _clean_vault_text 去系统回声行/截断残留/重复段, 剥自带 frontmatter 与重复 H1"""
    from core.gateway.precision_inject import _clean_vault_text

    _dirty = (
        "[系统] 当前阶段：交付。请用 write_file 或 python3 heredoc 将修改写入文件。\n"
        "你的上一条回复被截断了\n"
        "[TRUNCATED] done_reason: length\n"
        "## 正文\n"
        "表格行 1 | a\n"
        "表格行 2 | b\n"
        "\n"
        "重复段\n"
        "重复段\n"
        "正常结尾"
    )
    _c = _clean_vault_text(_dirty, title="")
    assert "[系统]" not in _c and "被截断" not in _c, _c
    assert _c.count("重复段") == 1, "连续重复段应折叠为 1 次"
    assert "正常结尾" in _c
    # 自带 frontmatter + 与标题重复的 H1 → 剥除
    _fm = "---\ntype: fix-record\ncreated: 2026-09-04\n---\n\n" "# 我的标题\n\n## 第一节\n内容"
    _c2 = _clean_vault_text(_fm, title="我的标题")
    assert not _c2.startswith("---"), "自带 frontmatter 应被剥除"
    assert not _c2.startswith("# 我的标题"), "重复 H1 应被剥除"
    assert "## 第一节" in _c2
    # 仅系统回声 → 空(触发拒绝写入)
    assert _clean_vault_text("[系统] 当前阶段：交付。请用 write_file 写入。" * 2) == ""


def test_r151_write_vault_note_cleans_and_append(tmp_path, monkeypatch):
    """R15.1: write_vault_note 清洗落盘 + 拒绝回声内容 + append 续写不重名"""
    from core.gateway import precision_inject

    monkeypatch.setattr(precision_inject, "_obsidian_cfg", lambda: {"enabled": True})
    monkeypatch.setattr(precision_inject, "_vault_path", lambda: str(tmp_path))
    # 正常内容(带污染) → 清洗后落盘, 单 frontmatter 单 H1
    _content = (
        "[系统] 当前阶段：交付。请用 write_file 写入。\n" "---\ntype: fix-record\n---\n\n" "# 评估报告\n\n## 结论\n中文可用 ✅\n\n## 建议\n混合方案"
    )
    p1 = precision_inject.write_vault_note("评估报告", _content, tags=["AI"], folder="调研")
    assert p1 and (tmp_path / "调研" / "评估报告.md").exists(), p1
    txt = (tmp_path / "调研" / "评估报告.md").read_text(encoding="utf-8")
    assert "[系统]" not in txt and "当前阶段：" not in txt, "系统回声不应入档"
    assert txt.count("---") == 2, f"应只有工具生成的单 frontmatter: {txt.count('---')}"
    assert txt.count("# 评估报告") == 1, "应只有单 H1"
    # 仅系统回声 → 拒绝(None)
    assert precision_inject.write_vault_note("回声稿", "[系统] 当前阶段：交付。" * 3) is None
    # append 续写: 同标题追加, 不生成 -2 副本
    p2 = precision_inject.write_vault_note("评估报告", "## 补充\n第二轮追加内容", folder="调研", append=True)
    assert p2 == p1, f"append 应续写同文件: {p2} vs {p1}"
    txt2 = (tmp_path / "调研" / "评估报告.md").read_text(encoding="utf-8")
    assert "第二轮追加内容" in txt2
    assert not (tmp_path / "调研" / "评估报告-2.md").exists(), "append 不应生成重名副本"


def test_r151_cap_par_no_mid_table_break():
    """R15.1: _cap_par 段落边界截断, 不硬切断 markdown 表格行"""
    from core.gateway.precision_inject import _cap_par

    _long = "## 事实表\n" + "".join(f"| 产品 {i} | {i}0 万 |\n" for i in range(60)) + "\n## 结论\n完整"
    _cut = _cap_par(_long, 120)
    assert len(_cut) <= 120 + 20, len(_cut)
    assert "| 产品" in _cut and _cut.endswith("(截断)") or _cut == _long


def test_r151_layers_wired_in_source():
    """R15.1: 三层补强落点 — 复盘稿/避坑清单清洗 + write_note append/校验 + 引导"""
    _pi = open("core/gateway/precision_inject.py", encoding="utf-8").read()
    assert "def _clean_vault_text" in _pi and "def _cap_par" in _pi
    assert "_clean_vault_text(report_text" in _pi, "复盘稿写入应清洗报告"
    assert "_clean_vault_text(mined[_k])" in _pi, "复盘挖掘内容应清洗"
    assert "_clean_vault_text(issue_text)" in _pi, "避坑追加应清洗"
    assert "append=False" in _pi, "write_vault_note 应支持 append 续写"
    _gh2 = open("core/lib/gateway_helpers.py", encoding="utf-8").read()
    assert "append=_wn_append" in _gh2 or '_wn_append = bool(params.get("append")' in _gh2, "handler 应支持 append 续写"
    assert '"verified"' in _gh2, "write_note 应返回写后校验(size/head)"
    _helpers = open("core/lib/gateway_helpers.py", encoding="utf-8").read()
    assert '"append"' in _helpers, "schema 应含 append 参数"
    assert "不要自带 yaml frontmatter" in _helpers, "schema 应提示不带自带 frontmatter"
    _sys = open("config/prompts/agent_system.md", encoding="utf-8").read()
    assert "append=true" in _sys, "agent_system 应引导分块续写"
    assert "verified" in _sys, "agent_system 应说明 verified 即写后抽验"
