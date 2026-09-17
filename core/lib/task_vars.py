"""#41 阶段3：任务变量抽取与资产过滤 — 变量驱动投喂

从任务描述提取变量集（文件路径/函数名/模块名/核心关键词），
供 precision_feed 按相关性裁剪 world_model / dependency_graph 注入，
替代"全量注入再截断"的浪费式投喂。
"""
import re
from pathlib import Path


# 常见动作词/噪声词：不构成任务变量
_NOISE = {
    "修改", "添加", "新增", "创建", "删除", "完善", "优化", "重构", "实现", "编写",
    "修复", "解决", "更新", "补充", "调整", "改造", "升级", "生成", "写入", "输出",
    "文件", "代码", "函数", "功能", "模块", "逻辑", "问题", "任务", "完成", "测试",
    "请", "帮我", "需要", "应该", "可以", "以及", "并且", "然后", "先", "再", "用",
    "the", "and", "or", "for", "with", "this", "that", "fix", "add", "update",
    "修改一下", "添加一个", "实现一个", "完成以下",
}


def extract_task_vars(task_name):
    """从任务描述提取变量集。

    返回 {"paths": [str], "tokens": [str], "keywords": [str]}
    - paths:    显式文件路径（clawsjoy_dev/... 或 xxx.py/xxx.js 等）
    - tokens:   代码标识符（下划线/驼峰/点号连接）
    - keywords: 过滤噪声后的中文/英文关键词（长度 >= 2）
    """
    if not task_name:
        return {"paths": [], "tokens": [], "keywords": []}
    text = str(task_name)

    # 1. 文件路径
    paths = re.findall(r"(?:clawsjoy_dev/)?[\w./-]+\.(?:py|js|ts|jsx|tsx|html|css|json|yaml|yml|md|txt|sh|sql)", text)
    paths = [p for p in paths if len(p) > 2]
    # 去重保序
    seen = set()
    paths_dedup = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            paths_dedup.append(p)

    # 2. 代码标识符（函数名/模块名：下划线/驼峰/点号）
    tokens = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]{1,}(?:\.[a-zA-Z_][a-zA-Z0-9_]*){0,2}\b", text)
    tokens = [t for t in tokens if not t.lower() in _NOISE and len(t) >= 2]
    # 只保留像代码标识符的（含下划线/驼峰/点号），纯单词如"add"排除
    code_like = [t for t in tokens if "_" in t or "." in t or re.search(r"[a-z][A-Z]", t) or re.match(r"^[A-Z]", t)]

    # 3. 关键词：中文连续片段 + 英文单词（过滤噪声）
    kw = re.findall(r"[一-鿿]{2,}|[a-zA-Z]{3,}", text)
    kw = [k for k in kw if k not in _NOISE and k.lower() not in _NOISE]
    kw = [k for k in kw if len(k) >= 2]

    return {"paths": paths_dedup, "tokens": code_like, "keywords": kw}


def filter_world_model_modules(wm_modules, task_vars, top_limit=30):
    """按任务变量过滤 world_model.modules，只保留相关模块。

    匹配规则（任一命中即保留）：
    - 模块路径包含任务文件路径（完整或 basename）
    - 模块路径含任务 token（函数/模块名片段）
    - 模块内容（skeleton/imports/functions）含任务关键词
    无变量时返回全量（前 top_limit）。
    """
    if not isinstance(wm_modules, dict) or not wm_modules:
        return {}
    paths = task_vars.get("paths", [])
    tokens = task_vars.get("tokens", [])
    keywords = task_vars.get("keywords", [])
    if not paths and not tokens and not keywords:
        items = list(wm_modules.items())[:top_limit]
        return dict(items)

    # 三级匹配：路径精确 > 标识符 > 关键词宽泛（避免宽泛匹配挤掉精确命中）
    exact = {}
    token_hit = {}
    kw_hit = {}
    for fp, info in wm_modules.items():
        fp_lower = str(fp).lower()
        hit = False
        # 一级：路径匹配（最精确）
        for p in paths:
            p_lower = str(p).lower()
            if p_lower in fp_lower or Path(p).name in fp_lower:
                exact[fp] = info
                hit = True
                break
        if hit:
            continue
        # 二级：标识符匹配（模块路径片段）
        for t in tokens:
            t_lower = t.lower()
            if t_lower in fp_lower:
                token_hit[fp] = info
                hit = True
                break
        if hit:
            continue
        # 三级：关键词匹配（骨架/函数/导入内容，最宽泛）
        if keywords:
            info_str = str(info.get("skeleton") or "") + " " + " ".join(str(info.get(k, "")) for k in ("functions", "classes", "imports"))
            info_lower = info_str.lower()
            if any(k.lower() in info_lower for k in keywords):
                kw_hit[fp] = info
    # 合并：精确优先，再 token，再关键词；限制数量
    merged = {}
    for src in (exact, token_hit, kw_hit):
        for k, v in src.items():
            if len(merged) >= top_limit:
                break
            merged[k] = v
    return merged


def filter_dependency_graph(dg_text, task_vars, max_chars=2000):
    """按任务变量过滤依赖图文本（行级匹配）。无变量时全量截断。"""
    if not dg_text or not isinstance(dg_text, str):
        return ""
    paths = task_vars.get("paths", [])
    tokens = task_vars.get("tokens", [])
    keywords = task_vars.get("keywords", [])
    if not paths and not tokens and not keywords:
        return dg_text[:max_chars]
    lines = dg_text.splitlines()
    keep = []
    for ln in lines:
        ln_lower = ln.lower()
        if any(str(p).lower() in ln_lower for p in paths):
            keep.append(ln)
            continue
        if any(t.lower() in ln_lower for t in tokens):
            keep.append(ln)
            continue
        if any(k.lower() in ln_lower for k in keywords):
            keep.append(ln)
    result = "\n".join(keep)
    return result[:max_chars]
