"""上下文精准注入: 任务语义 → 多源检索(vault/SAG/Vector/memory/报告) → 过滤 → 注入。

Obsidian 第二大脑集成: vault 扫描检索 + 任务完成写复盘 + 踩坑追加。
"""
import functools
import json
import os
import re
import time
from pathlib import Path
from core.lib.paths import vault_root, write_text_lf


def _tokenize(text):
    """中文分词: 中文按字切(提高匹配召回), 英文按词切。

    例: "番茄推广怎么发布" → [番,茄,推,广,怎,么,发,布] (单字, 与笔记"番茄推广SOP"
    共享 番/茄/推/广 → 余弦 > 0)。整串作为一个词元时不同文本几乎无重叠 → 检索全 0。
    """
    t = str(text).lower()
    words = re.findall(r"[a-z][a-z0-9]*", t)
    chars = re.findall(r"[\u4e00-\u9fa5]", t)
    return words + chars


def _tf_vector(text):
    words = _tokenize(text)
    total = len(words) or 1
    vec = {}
    for w in words:
        vec[w] = vec.get(w, 0) + 1
    return {w: c / total for w, c in vec.items()}


def _cosine(v1, v2):
    words = set(v1.keys()) | set(v2.keys())
    dot = sum(v1.get(w, 0) * v2.get(w, 0) for w in words)
    n1 = (sum(x * x for x in v1.values()) ** 0.5) or 1
    n2 = (sum(x * x for x in v2.values()) ** 0.5) or 1
    return dot / (n1 * n2)


def _vault_path():
    """vault 根: **唯一真源** = ``core.lib.paths.vault_root()``（CEO 2026-09-28 ⑤⒜ 启用）。

    2026-09-28(成对改): 此前先读 execution_policy.yaml 的 obsidian.vault_path
    （写死 WSL 挂载形态），读不到才回落 vault_root() ⇒ 同一台机上并存「配置」与「实探测」
    两份口径 —— 脑根一改或两边形态不同，判据就读错对象。
    现统一由 vault_root() 解析（``PA_VAULT_DIR`` → 配置 → 内置 kb → 末选实探测）；
    ``obsidian.vault_path`` 降为**说明**（⛔ 改它不改变行为）。
    ⚠ 2026-10-06（承 pm_1387 §二.2）：未接 ⇒ 返 ``""``（⛔ ``str(None)`` 之 ``"None"`` 假径）。
    """
    root = vault_root()
    return str(root) if root is not None else ""


# ===== 检索面排除名单（CEO 2026-09-28 ⑧ 终裁 ＋ ⑤⒝）=====
# `_冷区` = 冷库、`_垃圾箱` = 垃圾桶 ⇒ 参与检索 = 自相矛盾（且违老板「删权归我」的结构）；
# `.obsidian` = 配置目录、`Templates` = 模板 —— 都非知识。
# 配置项 obsidian.exclude_dirs 为唯一来源；缺省回落本常量。
_DEFAULT_EXCLUDE_DIRS = ("_冷区", "_垃圾箱", ".obsidian", "Templates")


def _exclude_dirs():
    """检索排除名单（配置优先 · 缺省回落 _DEFAULT_EXCLUDE_DIRS）。"""
    _got = _obsidian_cfg().get("exclude_dirs")
    if isinstance(_got, (list, tuple)):
        _out = tuple(str(x).strip() for x in _got if str(x).strip())
        if _out:
            return _out
    return _DEFAULT_EXCLUDE_DIRS


def _walk_warn(err):
    """遍历出错要有痕（⛔ 不静默吞）—— 静默丢件是「读数假绿」的老病根。"""
    print(f"[OBSIDIAN] vault 遍历告警(该子树可能不全): {err}")


def _walk_vault_md(root, skip):
    """遍历 vault 下全部 .md，**在进入排除目录前剪枝**（⛔ 不先递归再过滤）。

    剪枝而非事后过滤，两个理由：
      ① 排除面件量巨大 —— 事后过滤 = 白读几千件（本机实测全量 8,615 件 / 活区 3,166 件）；
      ② WSL drvfs 下 readdir 出错会**整棵丢**（DSH 2026-09-27 实测 scan_total 1,034 → 2,257）
         ⇒ 遍历范围越小，越少踩这一类。
    输出按路径排序（保持既有 sorted(rglob) 的确定性顺序）。
    """
    for dirpath, dirnames, filenames in os.walk(str(root), onerror=_walk_warn):
        dirnames[:] = sorted(d for d in dirnames if d not in skip)
        for _name in sorted(filenames):
            if _name.endswith(".md"):
                yield Path(dirpath) / _name


def _rel_excluded(rel, skip):
    """相对路径**任一段**落在排除名单 ⇒ 排除（防嵌套的同名目录）。"""
    return any(_seg in skip for _seg in str(rel).split("/"))


def _scan_vault():
    """扫描 vault 根下全部 .md(递归), 带 sub 来源类型与相对路径。

    R4(2026-08-31): 原只扫 Reviews/SOPs/Pitfalls 三目录 → 用户手动目录(微信公众号/、
    我的知乎主页/ 等)与 Clippings 自动剪藏检索不到 → Agent 误报「公众号未登记」。
    现递归扫 vault 根下所有 *.md: 权威类别(SOPs/Pitfalls/Reviews)走配置解析, 其余归 general。
    2026-09-28(CEO ⑧ 终裁 ＋ ⑤⒝): 排除名单 = `_冷区` / `_垃圾箱` / `.obsidian` / `Templates`
    （可在 obsidian.exclude_dirs 配），且**在进入排除目录前剪枝**（见 _walk_vault_md）。
    """
    root = Path(_vault_path())
    skip = set(_exclude_dirs())
    out = []
    for f in _walk_vault_md(root, skip):
        rel = f.relative_to(root).as_posix()
        # 剪枝只管顶层名 ⇒ 嵌套同名目录在这里补一刀
        if _rel_excluded(rel, skip):
            continue
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        tags = []
        m = re.search(r"^---\n(.*?)\n---", txt, re.S)
        fm = m.group(1) if m else ""
        tm = re.search(r"tags:\s*\[?([^\n\]]*)\]?", fm)
        if tm:
            tags = [t.strip().strip(chr(39)).strip(chr(34)) for t in tm.group(1).split(chr(44)) if t.strip()]
        # sub 分类: 权威类别走配置根(见 _reviews_sub_label); 其余归 general(检索可用, 权重默认)
        sub = _reviews_sub_label(rel)  # 批198: 复盘迁到「聊天区/复盘」后仍按 Reviews 加权
        title = f.name.replace(".md", "")
        out.append(
            {
                "name": title,
                "tags": tags,
                "text": txt[:2000],
                "path": str(f),
                "rel_path": rel,
                "mtime": f.stat().st_mtime,
                "sub": sub,
            }
        )
    return out


# 2026-08-30 回填修复: 权威度加权(同一相似度下 SOP/Pitfalls 优先于 Reviews 复盘)
# 批198 · 复盘目录「单一来源」：此前**写**用 cfg.reviews_dir、**读**硬编码 'Reviews' ⇒ 只改配置就分裂
def _reviews_write_dir():
    # 写复盘的目标目录（配置为唯一来源）
    return Path(_vault_path()) / (str(_obsidian_cfg().get("reviews_dir") or "Reviews"))


def _reviews_read_dirs():
    # 读复盘：配置目录 + 历史目录 'Reviews'（迁移期间不丢历史；相同则只一个）
    root = Path(_vault_path())
    cfg_dir = str(_obsidian_cfg().get("reviews_dir") or "Reviews")
    out = [root / cfg_dir]
    legacy = root / "Reviews"
    if cfg_dir != "Reviews" and legacy.exists():
        out.append(legacy)
    return [d for d in out if d.exists()]


@functools.lru_cache(maxsize=1)
def _cfg_roots():
    """权威度类别根(vault 相对) = 配置 ``obsidian.sops_dir`` / ``pitfalls_dir``。

    2026-09-28(P0-② 成对改): 真源目录由 vault 根 `SOPs/` / `Pitfalls/` 迁到
    **配置根**(`工作区/SOPs/SOPs` / `开发区/ComputerUse/Pitfalls`) ⇒ 类别判据
    `_reviews_sub_label()` 必须跟着走, ⛔ 不写死旧前缀(否则权重 1.25/1.2 永不生效)。
    lru_cache: 逐件扫描免重复读 yaml; `cache_clear()` 供改配置/测试重算
    (见 tests/unit/test_authority_label.py::test_C_config_driven)。
    """
    _cfg = _obsidian_cfg()
    _s = str(_cfg.get("sops_dir") or "SOPs").strip("/")
    _p = str(_cfg.get("pitfalls_dir") or "Pitfalls").strip("/")
    return _s, _p


def _reviews_sub_label(rel):
    # 权威度类别标签: 复盘迁到「聊天区/复盘」后仍按 'Reviews' 加权
    r = str(rel or "")
    if r.startswith("Reviews/") or "复盘" in r:
        return "Reviews"
    top = r.split("/")[0]
    if top in ("SOPs", "Pitfalls"):
        return top  # 历史形态: vault 根直接挂牌
    # P0-②(2026-09-28 成对改): 真源在配置根下(首段 = 工作区/开发区) ⇒ 按配置根判
    _sops_root, _pit_root = _cfg_roots()
    if _sops_root and (r == _sops_root or r.startswith(_sops_root + "/")):
        return "SOPs"
    if _pit_root and (r == _pit_root or r.startswith(_pit_root + "/")):
        return "Pitfalls"
    return "general"


_VALTYPE_WEIGHT = {"SOPs": 1.25, "Pitfalls": 1.2, "Reviews": 0.75}


def _sop_sections(sop_key):
    """把指定常驻 SOP 文件切成 ## 小节, 返回 [(小节标题, 小节正文), ...]。

    用于小节级检索: 任务命中 _KNOWLEDGE_FILES 关键词时, 强制注入对应小节
    (如"回填"任务 → 番茄推广SOP 的"五、发布 + 回填(7天闭环)"小节), 不再被 TF 稀释漏掉。
    """
    fpath = _resolve_knowledge_path(sop_key)
    if fpath is None or not fpath.exists():
        return []
    try:
        txt = fpath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    txt = re.sub(r"^---\n.*?\n---\n", "", txt, count=1, flags=re.S)
    parts = re.split(r"(?m)^## ", txt)
    out = []
    for p in parts[1:]:
        lines = p.splitlines()
        title = lines[0].strip() if lines else ""
        body = chr(10).join(lines[1:]).strip()[:1200]
        if title and body:
            out.append((title, body))
    return out


def _sop_knowledge_hits(text):
    """任务文本命中常驻 SOP 关键词 → 返回 [(sop_key, [(小节标题, 正文)...]), ...](按命中数排序)"""
    if not text:
        return []
    hits = []
    for key, info in _KNOWLEDGE_FILES.items():
        n = sum(1 for k in info["keywords"] if k in text)
        if n > 0:
            hits.append((n, key, _sop_sections(key)))
    hits.sort(key=lambda x: -x[0])
    return hits


def search_vault(query, limit=3):
    qv = _tf_vector(query)
    scored = []
    for note in _scan_vault():
        hay = note["name"] + " " + " ".join(note["tags"]) + " " + note["text"][:800]
        s = _cosine(qv, _tf_vector(hay))
        # 2026-08-30 回填修复: 权威度加权(SOP/Pitfalls 优先于 Reviews 复盘)
        s *= _VALTYPE_WEIGHT.get(note.get("sub", ""), 1.0)
        if s > 0.05:
            scored.append(
                {
                    "name": note["name"],
                    "score": round(s, 3),
                    "tags": note["tags"],
                    "path": note["path"],
                    "rel_path": note.get("rel_path", ""),  # R4: 相对路径(Agent read 用)
                    "preview": note["text"][:100],
                    "content": note["text"][:2000],  # B2: 全文片段(2026-08-30)
                    "sub": note.get("sub", ""),
                }
            )
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


def extract_task_semantics(messages):
    text = ""
    for m in reversed(messages or []):
        if m.get("role") == "user":
            text = str(m.get("content", ""))[:500]
            break
    return {"text": text}


# 过滤网参数配置(B): 从 execution_policy.yaml precision_inject 段读取, 默认值保持
_INJECT_CFG_CACHE = None


def _inject_cfg():
    """读 precision_inject 配置(带缓存, 测试可 monkeypatch)。默认值与硬编码一致。"""
    global _INJECT_CFG_CACHE
    if _INJECT_CFG_CACHE is not None:
        return _INJECT_CFG_CACHE
    _cfg = {
        "vault_min_score": 0.05,
        "memory_min_score": 0.1,
        "report_min_score": 0.05,
        "keyword_weight": 0.3,
        "decay_days": 60,
        "min_score": 0.1,
        "top_n": 5,
        "token_budget": 750,
    }
    try:
        import yaml as _yaml

        with open("config/v9/execution_policy.yaml", encoding="utf-8") as _f:
            _pol = (_yaml.safe_load(_f) or {}).get("precision_inject") or {}
        for _k in _cfg:
            if _k in _pol and _pol[_k] is not None:
                _cfg[_k] = _pol[_k]
    except Exception:
        pass
    _INJECT_CFG_CACHE = _cfg
    return _cfg


def reset_inject_cfg():
    """测试/热更新用: 清配置缓存"""
    global _INJECT_CFG_CACHE
    _INJECT_CFG_CACHE = None


def search_candidates(sem, user_id, session_id, sandbox_base, now=None):
    now = now or time.time()
    _cfg = _inject_cfg()
    cands = []
    # 2026-08-30 回填修复: 任务命中常驻 SOP 关键词 → 强制注入对应小节(回填规则必现)
    # 小节按与任务文本的 TF 相关度排序(不是文件顺序), 取最相关 top2
    _task_text = sem.get("text", "")
    _qv = _tf_vector(_task_text)
    for _n, _key, _sections in _sop_knowledge_hits(_task_text):
        _ranked_sec = sorted(
            _sections, key=lambda st: _cosine(_qv, _tf_vector(st[0] + " " + st[1][:400])), reverse=True
        )
        for _st, _sb in _ranked_sec[:2]:  # 每 SOP 最多 2 小节, 避免刷屏
            cands.append(
                {
                    "source": "sop_section",
                    "name": f"{_key} › {_st}",
                    "score": 0.6 + 0.05 * _n,  # 关键词命中越多分越高
                    "preview": _sb[:200],
                    "path": _resolve_knowledge_path(_key),
                }
            )
    for n in search_vault(sem.get("text", ""), limit=_cfg["top_n"]):
        cands.append(
            {"source": "vault", "name": n["name"], "score": n["score"], "preview": n["preview"], "path": n["path"]}
        )
    try:
        from core.gateway.memory import _load_memory

        for kind in ("known_issues", "known_patterns"):
            for e in _load_memory(user_id, kind):
                content = str(e.get("content", ""))
                s = _cosine(_tf_vector(sem.get("text", "")), _tf_vector(content))
                if s > _cfg["memory_min_score"]:
                    age_days = (now - float(e.get("ts", now))) / 86400
                    cands.append(
                        {
                            "source": kind,
                            "name": kind,
                            "score": round(s, 3),
                            "preview": content[:120],
                            "age_days": round(age_days, 1),
                        }
                    )
    except Exception:
        pass
    try:
        base = Path(str(sandbox_base))
        reports = base / "data" / "reports"
        if reports.exists():
            for f in sorted(reports.glob("*.md")):
                s = _cosine(_tf_vector(sem.get("text", "")), _tf_vector(f.stem))
                if s > _cfg["report_min_score"]:
                    cands.append(
                        {"source": "report", "name": f.stem, "score": round(s, 3), "preview": str(f), "path": str(f)}
                    )
    except Exception:
        pass
    # R3 修复(2026-08-30): 最近复盘注入 — vault Reviews 最近 3 条(任务相关度排序由 filter_and_rank 完成),
    # Agent 任务前能看到"上次发生了什么", 不再翻 goal JSON 找复盘
    try:
        if _obsidian_cfg().get("enabled"):
            _rv_files = []
            for _rr in _reviews_read_dirs():
                _rv_files.extend(_rr.glob("*.md"))
            for f in sorted(_rv_files, key=lambda p: p.stat().st_mtime, reverse=True)[:3]:
                try:
                    _rvt = f.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                cands.append(
                    {
                        "source": "review",
                        "name": f"Reviews/{f.stem}",
                        "score": 0.45,  # 略低于 SOP 命中, 高于普通噪音
                        "preview": _rvt[:200],
                        "path": str(f),
                    }
                )
    except Exception:
        pass
    # 4) SAG 源(代码图谱全文检索, 如可用): query_fulltext_by_keywords → relevance 候选
    try:
        from core.lib.code_entity_extractor import extractor as _sag_ext

        _kws = _tokenize(sem.get("text", ""))[:8]
        if _kws:
            _sag_rows = _sag_ext.query_fulltext_by_keywords(_kws) or []
            for _row in _sag_rows[: _cfg["top_n"]]:
                _rel = float(_row.get("relevance", 0) or 0)
                _nm = str(_row.get("entity_name") or _row.get("task_name") or "SAG")
                _snip = str(_row.get("summary") or _row.get("signature") or "")[:120]
                if _rel > 0:
                    # 2026-08-30: SAG 降权 ×0.3 — 代码实体对文档/复盘任务价值低, 却常以 1.0 相关度
                    # 挤掉 Reviews/SOP 候选(日志: top_n 被 SAG 占满, 复盘注入失败)
                    cands.append(
                        {
                            "source": "sag",
                            "name": _nm,
                            "score": round(_rel * 0.3, 3),
                            "preview": _snip,
                            "path": str(_row.get("file_path") or ""),
                        }
                    )
    except Exception:
        pass
    return cands


def filter_and_rank(candidates, sem, now=None, top_n=None, min_score=None):
    now = now or time.time()
    _cfg = _inject_cfg()
    # 参数为 None 时用配置(默认值与硬编码一致), 显式传参覆盖配置
    if top_n is None:
        top_n = _cfg["top_n"]
    if min_score is None:
        min_score = _cfg["min_score"]
    _kw = _cfg["keyword_weight"]
    _decay = _cfg["decay_days"]
    kws = set(_tokenize(sem.get("text", "")))
    seen = {}
    for c in candidates:
        k = c.get("name", "")
        if k in seen:
            if c["score"] > seen[k]["score"]:
                seen[k] = c
        else:
            seen[k] = c
    scored = []
    for c in seen.values():
        score = c["score"]
        preview_kws = set(_tokenize(c.get("preview", "")))
        hit = len(preview_kws & kws) / max(len(kws), 1)
        score += hit * _kw
        age = c.get("age_days")
        if age is not None and _decay > 0:
            score *= max(0.5, 1.0 - age / _decay)
        scored.append({**c, "rank_score": round(score, 3)})
    scored.sort(key=lambda x: x["rank_score"], reverse=True)
    # 低相关排除: rank_score 低于阈值不注入(防噪音)
    filtered = [c for c in scored if c["rank_score"] >= min_score]
    return filtered[:top_n]


def summarize(item, max_chars=100):
    t = item.get("preview", "") or item.get("name", "")
    return t[:max_chars]


def build_injection(candidates, max_chars=750):
    """拼【精准上下文】文本, 总量截断到 max_chars(≈500 tokens, 中文 1 token≈1.5 字)。

    优先级: 注入层最后一道 — 即使候选超预算, 也只截断摘要不丢条目前缀。
    """
    if not candidates:
        return ""
    parts = []
    for c in candidates:
        src = c["source"]
        label = {
            "vault": "笔记",
            "known_issues": "踩坑",
            "known_patterns": "经验",
            "report": "报告",
            "sag": "代码",
            "sop_section": "SOP",
            "review": "复盘",
        }.get(src, src)
        parts.append(f"- [{label}] {c.get('name', '')}（相关度 {c.get('rank_score', c.get('score', 0))}）: {summarize(c)}")
    head = "【精准上下文】根据当前任务检索到的相关知识："
    body = chr(10).join(parts)
    if len(head) + len(body) > max_chars:
        # 预算内逐条保留(保前缀), 超出截断尾部
        kept = [head]
        budget = max_chars - len(head) - 20
        for p in parts:
            if budget <= 0:
                break
            add = p[:budget]
            kept.append(add)
            budget -= len(add) + 2
        body = chr(10).join(kept[1:])
        return head + body + "…"
    return head + body


# 任务级幂等: {session_id: last_task_fingerprint} — 同任务(最近 user 消息)只注入一次,
# 防每轮 bridge_loop 重建 messages 后重复注入同一批相关知识(浪费预算 + 噪音)
_IDEMPOTENT_TRACKER = {}


def _task_fingerprint(text):
    """任务指纹: 关键词集合排序 hash(轻微措辞变化不触发重复注入)"""
    kws = sorted(set(_tokenize(text)))
    return hash(tuple(kws)) if kws else None


def get_precision_context(messages, user_id, session_id, sandbox_base, now=None):
    sem = extract_task_semantics(messages)
    text = sem.get("text", "")
    if not text:
        return ""
    # 任务指纹幂等: 同 session 同任务不重复注入
    fp = _task_fingerprint(text)
    if fp is not None and _IDEMPOTENT_TRACKER.get(session_id) == fp:
        return ""
    cands = search_candidates(sem, user_id, session_id, sandbox_base, now=now)
    _cfg = _inject_cfg()
    ranked = filter_and_rank(cands, sem, now=now, top_n=_cfg["top_n"], min_score=_cfg["min_score"])
    if not ranked:
        return ""
    _IDEMPOTENT_TRACKER[session_id] = fp
    return build_injection(ranked, max_chars=_cfg["token_budget"])


def reset_idempotent(session_id=None):
    """测试/新会话用: 清任务指纹(全部或指定 session)"""
    if session_id is None:
        _IDEMPOTENT_TRACKER.clear()
    else:
        _IDEMPOTENT_TRACKER.pop(session_id, None)


def _obsidian_cfg():
    try:
        import yaml as _yaml

        with open("config/v9/execution_policy.yaml", encoding="utf-8") as _f:
            return (_yaml.safe_load(_f) or {}).get("obsidian") or {}
    except Exception:
        return {}


def _mine_review_sections(messages=None, tool_steps=None):
    """从对话历史挖掘复盘小节(关键决策/踩坑/可复用经验)。

    背景: 最终 report(LLM 总结)通常只有"做了什么", 关键决策/踩坑/可复用经验全空。
    实际这些内容散落在对话历史里 — 工具失败结果、assistant 的自我纠错叙述、
    [系统] 守卫提示(如 "evaluate 是只读探测通道" / "write_file line 参数精确修改单行")。
    返回 {"关键决策": str, "踩坑": str, "可复用经验": str}(空串表示未挖到)。
    """
    pitfalls, decisions, experiences = [], [], []
    seen = set()

    def _add(lst, txt):
        txt = str(txt or "").strip()
        if txt and txt not in seen and len(lst) < 8:
            seen.add(txt)
            lst.append(txt[:200])

    # ---- tool_steps 结构化信号(最可靠: success/error 已解析) ----
    _NOISE_RESULT = ("total ", "drwx", "-rw-", "Permission denied", "No such file", "command not found", "usage:")
    _EXPLORE_TOOLS2 = ("list_dir", "read_file", "search_files", "query_index")
    _NOISE_CMDS = (
        "ls",
        "pwd",
        "cat",
        "head",
        "tail",
        "echo",
        "find",
        "which",
        "whoami",
        "date",
        "df",
        "free",
        "env",
        "history",
        "tree",
        "ls -la",
    )
    for ts in tool_steps or []:
        if not isinstance(ts, dict):
            continue
        tool = str(ts.get("tool") or "")
        arg = str(ts.get("arg") or "")[:80]
        if ts.get("success"):
            r = str(ts.get("result") or "").strip()
            # 经验过滤(2026-08-30): 排除命令输出噪音(ls/find/cat/pwd 等目录/回显), 只留真知识
            _is_noise = tool in _EXPLORE_TOOLS2
            if tool == "execute_command":
                _cmd = arg.split()[0] if arg.split() else arg
                if _cmd in _NOISE_CMDS or any(x in arg for x in ("ls -la", "| head", "| grep", "| tail")):
                    _is_noise = True
                if len(r) > 200 or any(r.startswith(x) for x in _NOISE_RESULT):
                    _is_noise = True
            if r and not _is_noise:
                _add(experiences, f"{tool} {arg}: {r[:120]}")
        else:
            err = str(ts.get("error") or "").strip()
            if err and err not in ("等待老板确认写入", "检测到多文件/多意图任务，等待老板确认计划"):
                _add(pitfalls, f"{tool} {arg} 失败: {err}")
    # ---- messages: 先建 tool_call_id → 工具名 映射(assistant tool_calls) ----
    call2tool = {}
    for m in messages or []:
        if not isinstance(m, dict) or m.get("role") != "assistant":
            continue
        for tc in m.get("tool_calls") or []:
            if isinstance(tc, dict) and tc.get("id"):
                fn = (tc.get("function") or {}).get("name") or ""
                if fn:
                    call2tool[str(tc["id"])] = fn
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        content = str(m.get("content") or "")
        if role == "tool":
            tname = call2tool.get(str(m.get("tool_call_id") or ""), "")
            try:
                data = json.loads(content)
            except Exception:
                data = None
            if isinstance(data, dict) and not data.get("success"):
                err = str(data.get("error") or data.get("reason") or "")[:180]
                # 设计性拦截(只读探测通道/审批/越权是系统保护, 非新坑) — 不沉淀为踩坑
                _design_block = any(k in err for k in ("只读探测通道", "等待老板确认", "域名不在白名单", "越权", "高危命令", "路径越权"))
                if err and not _design_block:
                    _add(pitfalls, (f"{tname}: " if tname else "") + err)
            continue
        if role == "system":
            # 模板注入(沙箱边界/精准上下文)/运行时快照非任务经验, 跳过; 守卫/止损提示才是有价值信号
            if content.startswith("【") or content.startswith("[系统] 当前运行环境快照"):
                continue
            if any(k in content for k in ("已连续", "无实质产出", "失败", "只读", "相似度", "越权", "拦截", "等待", "暂停", "不要", "禁止")):
                _add(pitfalls, content.strip()[:200])
            if any(k in content for k in ("参数精确修改", "相对路径", "data/tmp", "只读探测", "请停止")):
                _add(experiences, content.strip()[:200])
            continue
        if role == "assistant":
            sentences = re.split(r"(?<=[。！？!?\n])", content)
            for s in sentences:
                s = s.strip()
                if not s or len(s) < 6:
                    continue
                if any(k in s for k in ("改用", "决定", "选择", "采用", "方案", "换一种", "先尝试", "为了避免", "于是用", "改成")):
                    _add(decisions, s)
                if any(k in s for k in ("失败", "错误", "误操作", "踩坑", "报错", "❌", "cd /", "绕过", "被拒", "反复", "截断")):
                    _add(pitfalls, s)
                if any(k in s for k in ("经验", "以后", "下次", "记住", "总结", "正确做法", "应该用")):
                    _add(experiences, s)
    return {
        "关键决策": chr(10).join(decisions),
        "踩坑": chr(10).join(pitfalls),
        "可复用经验": chr(10).join(experiences),
    }


def write_task_review(
    user_id, session_id, task_id, task_title, report_text, extra=None, messages=None, tool_steps=None
):
    """任务完成后写复盘笔记到 vault Reviews/。返回笔记路径或 None。"""
    cfg = _obsidian_cfg()
    if not cfg.get("enabled"):
        return None
    root = Path(_vault_path())
    reviews = _reviews_write_dir()  # 批198: 写=配置（唯一来源）
    try:
        reviews.mkdir(parents=True, exist_ok=True)
        date = time.strftime("%Y-%m-%d")
        fname = f"{date}-{task_id}.md"
        fpath = reviews / fname
        # R15.1(2026-09-04): 落盘前清洗(去系统提示行/截断残留/重复段) + 段落边界截断,
        # 防"残缺复盘稿"(原硬切 [:3000]/[:500] 会断在 markdown 表格行中)与噪音入档
        report = _clean_vault_text(report_text, keep_cap=3000)

        def _sec(title):
            m = re.search(title + r"[：:]?\n(.*?)(?=\n## |\Z)", report, re.S)
            return _cap_par(m.group(1).strip(), 500) if m else ""

        sections = {
            "做了什么": _sec("## 做了什么"),
            "关键决策": _sec("## 关键决策"),
            "踩坑": _sec("## 踩坑"),
            "可复用经验": _sec("## 可复用经验"),
        }
        if not any(sections.values()):
            sections["做了什么"] = _cap_par(report, 500)
        # 复盘质量修复(2026-08-30): report 常只有"做了什么", 关键决策/踩坑/可复用经验
        # 从对话历史挖掘兜底 — tool 失败结果/assistant 纠错叙述/[系统] 守卫提示都在这
        try:
            mined = _mine_review_sections(messages, tool_steps)
            for _k in ("关键决策", "踩坑", "可复用经验"):
                if not sections[_k] and mined.get(_k):
                    # R15.1: 挖掘内容也可能混入工具输出碎片/截断残留 → 清洗 + 段落截断
                    sections[_k] = _cap_par(_clean_vault_text(mined[_k]), 500)
        except Exception:
            pass
        links = re.findall(r"\[\[([^\]]+)\]\]", report)[:5]
        if not links:
            sops = root / (cfg.get("sops_dir") or "SOPs")
            if sops.exists():
                links = [f.stem for f in sorted(sops.glob("*.md"))][:3]
        content = [
            "---",
            "type: task-review",
            f"tags: [{task_title[:30]}]",
            f"created: {date}",
            f"task_id: {task_id}",
            "---",
            f"# 任务复盘：{task_title}",
            "",
        ]
        for sec, body in sections.items():
            content.append(f"## {sec}")
            content.append(body if body else "（无记录）")
            content.append("")
        content.append("## 相关")
        if links:
            for l in links:
                content.append(f"- [[{l}]]")
        else:
            content.append("- （暂无相关笔记）")
        write_text_lf(fpath, chr(10).join(content))
        return str(fpath)
    except Exception as e:
        print(f"[OBSIDIAN] 复盘写入失败: {e}")
        return None


def _looks_like_frontmatter(lines):
    """判断 --- 与 --- 之间的内容是否**真的像** YAML frontmatter（而不是正文/分隔线）。

    契约：返回 bool。任一行既不是 `key:` / `key: value` 也不是 `- item` / 空行 / 注释 → False。
    这条判据是 2026-09-13 事故的修复核心：旧实现只看「以 --- 开头 + 后面还有 ---」就整段切掉，
    而 markdown 正文以 --- (分隔线) 开头、后面又有 --- 极其常见 → 中间内容被静默删除。
    """
    import re as _re_fm

    if not lines:
        return False
    _seen_key = False
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if _re_fm.match(r"^[-*]\s+.+$", s):  # 列表项（tags 下的子项）
            continue
        if _re_fm.match(r"^[^\s:][^:]*:.*$", s):  # key: / key: value（半角冒号）
            _seen_key = True
            continue
        return False
    return _seen_key


def _clean_vault_text(text, title="", keep_cap=None):
    """R15.1(2026-09-04): vault 落盘前清洗 — 防"原样存档污染"。

    去除三类污染源, 再按段落边界截断:
    1. 系统/阶段提示行: 以 "[系统]" 开头或含 "当前阶段：" 的行(回声/指令残留);
    2. 截断残留标记行: "你的上一条回复被截断了" / "[TRUNCATED]" / 尾部裸的
       "done_reason: length"(整行即标记) — 长文被系统截断后原样入档的证据;
    3. 连续重复段落: 同段重复 >=2 次保留 1 次(系统回声常整段复读)。
    另: 剥除自带 yaml frontmatter 块(工具会自动生成)与重复的一级标题(== title)。
    返回清洗后文本(可能为 "")。
    """
    import re as _re_clean

    if text is None:
        return ""
    text = str(text)
    out_lines = []
    prev = None
    _markers = ("你的上一条回复被截断了", "[TRUNCATED]")
    for ln in text.split(chr(10)):
        s = ln.strip()
        # 系统回声/阶段指令行
        if s.startswith("[系统]") or "当前阶段" in s[:24] or "请用 write_file 或 python3 heredoc" in s:
            continue
        if any(m in s for m in _markers) and len(s) < 80:
            continue
        if s == "done_reason: length" or s.startswith("done_reason: length"):
            continue
        # 连续重复行/段折叠
        if s and s == prev:
            continue
        prev = s if s else prev
        out_lines.append(ln)
    cleaned = chr(10).join(out_lines).strip()
    # 剥除自带 frontmatter(--- ... --- 开头块)
    # 修(2026-09-13): 旧实现是「以 --- 开头 + 后面能搜到 \n---」就整段切掉 ——
    # 正文以 --- (markdown 分隔线)开头、后面又有一个 --- 时, 中间内容被**静默删除**。
    # 真实事故: write_note(append=True) 一段以 --- 开头的正文, 掉了整节 P11–P13,
    # 工具仍返回 success + verified(bytes/lines) → 调用方无法发现掉段。
    # 现在只在该块**真的像 YAML frontmatter** 时才剥除(且限前 30 行内闭合)。
    if cleaned.startswith("---"):
        _fm_lines = cleaned.split(chr(10))
        if _fm_lines and _fm_lines[0].strip() == "---":
            _fm_end = -1
            for _i in range(1, min(len(_fm_lines), 31)):
                if _fm_lines[_i].strip() == "---":
                    _fm_end = _i
                    break
            if _fm_end != -1 and _looks_like_frontmatter(_fm_lines[1:_fm_end]):
                cleaned = chr(10).join(_fm_lines[_fm_end + 1 :]).lstrip(chr(10))
    # 去掉与标题重复的一级标题行
    if title:
        _t = str(title).strip()
        for h in ("# " + _t, "#" + _t):
            if cleaned.startswith(h + chr(10)) or cleaned == h:
                cleaned = cleaned[len(h) :].lstrip(chr(10))
    cleaned = cleaned.strip()
    # 按段落边界截断, 避免硬切断 markdown 表格行
    if keep_cap and len(cleaned) > keep_cap:
        cut = cleaned[:keep_cap]
        _br = max(cut.rfind(chr(10) + chr(10)), cut.rfind(chr(10)))
        cut = cut[:_br] if _br > 0 else cut
        cleaned = cut.rstrip() + chr(10) + "...(截断, 完整版见权威源)"
    return cleaned.strip()


def _cap_par(text, n):
    """按段落边界截断到 <=n 字符(避免硬切断 markdown 表格行/代码块)。"""
    t = str(text or "").strip()
    if len(t) <= n:
        return t
    cut = t[:n]
    br = max(cut.rfind(chr(10) + chr(10)), cut.rfind(chr(10)))
    cut = cut[:br] if br > 0 else cut
    return cut.rstrip() + chr(10) + "…(截断)"


def write_vault_note(title, content, tags=None, folder="", append=False):
    """R15(2026-09-03)+R15.1(2026-09-04): 写任意技术/评估/复盘笔记到 vault(非平台草稿的通用落盘)。

    背景: obsidian_knowledge 原只有 write_draft(草稿箱/平台稿, 需 platform)与
    process_media/process_youtube(学习笔记专用) — 技术评估/总结类笔记无落盘通道,
    Agent 调 write_draft 传 platform=None → 报"未知平台"后放弃写报告。
    本函数: 写 {vault}/{folder}/{sanitized_title}.md, folder 默认空=vault 根目录,
    可传 收件箱/学习笔记/ 等 vault 相对目录(禁止绝对路径与 .. 穿越)。
    R15.1 补强:
    - content 落盘前经 _clean_vault_text 清洗(去系统提示行/截断残留/重复段,
      剥除自带 frontmatter 与重复 # 标题 → 不再双 frontmatter/双标题);
    - 清洗后为空/仅系统回声 → 拒绝写入返回 None(防原样存档污染);
    - append=True 追加到同名已存在笔记(长文分块续写, 防单次输出过长被截断)。
    返回笔记路径或 None。
    """
    cfg = _obsidian_cfg()
    if not cfg.get("enabled"):
        return None
    root = Path(_vault_path())
    title = str(title or "").strip()
    if not title:
        return None
    folder = str(folder or "").strip().strip("/")
    # 路径穿越防护: 只允许 vault 内相对目录(逐段校验, 拒绝 . / .. / 绝对路径 / 盘符)
    _parts = folder.split("/") if folder else []
    if any(p in ("", ".", "..") or ":" in p or "/" in p for p in _parts):
        return None
    target_dir = root.joinpath(*_parts) if _parts else root
    # 文件名净化: 去掉 Windows/文件系统非法字符, 空格保留
    import re as _re_note

    fname = _re_note.sub(r'[\\/:*?"<>|\n\r\t]+', "_", title).strip(" .")
    if not fname:
        fname = "note"
    cleaned = _clean_vault_text(content, title=title)
    # 拒绝阈值只需拦住"清洗后为空"(系统回声/截断残留会清成空), 不误伤短小实义笔记
    if len(cleaned) < 10:
        print(f"[OBSIDIAN] write_note 拒绝写入: 内容清洗后为空/仅系统回声或截断残留(title={title[:30]})")
        return None
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        # 并发安全(2026-09-05): 进程级锁(同进程多线程) + os.open(O_CREAT|O_EXCL) 原子独占创建(跨进程)。
        # 修复竞态: 旧 exists()+open('w') 非原子 → 同标题多线程双写同一 -N 文件互相覆盖。
        # 注意: append 跨进程追加仍可能交错(建议 append 由单一写入方串行执行)。
        import os as _os_note
        import threading as _th_note

        global _NOTE_WRITE_LOCK
        if _NOTE_WRITE_LOCK is None:
            _NOTE_WRITE_LOCK = _th_note.Lock()
        with _NOTE_WRITE_LOCK:
            if append:
                fpath = target_dir / (fname + ".md")
                if fpath.exists():
                    with open(fpath, "a", encoding="utf-8") as _af:
                        _af.write(chr(10) + chr(10) + cleaned + chr(10))
                    print(f"[OBSIDIAN] write_note 追加续写: {fpath}")
                    return str(fpath)
            # 独占创建: 先试原名(冲突则 -2/-3/-4...), O_EXCL 保证同刻仅一个写入者
            n = 0
            while True:
                cand = target_dir / (fname + ".md") if n == 0 else target_dir / (f"{fname}-{n + 1}.md")
                try:
                    fd = _os_note.open(str(cand), _os_note.O_CREAT | _os_note.O_EXCL | _os_note.O_WRONLY, 0o644)
                    fpath = cand
                    break
                except FileExistsError:
                    n += 1
                    if n > 999:
                        raise
            with _os_note.fdopen(fd, "w", encoding="utf-8") as _nf:
                tag_list = tags or []
                if isinstance(tag_list, str):
                    tag_list = [tag_list]
                date = time.strftime("%Y-%m-%d")
                _lines = ["---", "type: note", "created: " + date]
                if tag_list:
                    _lines.append("tags:")
                    for t in tag_list:
                        _lines.append(f"  - {t}")
                _lines += ["---", "", f"# {title}", ""]
                if cleaned:
                    _lines.append(cleaned)
                _nf.write(chr(10).join(_lines) + chr(10))
        print(f"[OBSIDIAN] write_note 落盘: {fpath}")
        return str(fpath)
    except Exception as e:
        print(f"[OBSIDIAN] write_note 写入失败: {e}")
        return None


_NOTE_WRITE_LOCK = None  # write_vault_note 进程级锁(并发安全)


def append_pitfall(issue_text, tags=None):
    """新坑追加到 vault Pitfalls/避坑清单.md(迁移后的常驻文件, cfg pitfalls_file 可配)。

    2026-08-30: 知识迁移后 pitfalls 常驻文件为 避坑清单.md; 旧 avoid_pitfalls.md 内容已并入。
    """
    cfg = _obsidian_cfg()
    if not cfg.get("enabled") or not cfg.get("append_pitfalls"):
        return None
    root = Path(_vault_path())
    pfile = root / _pitfalls_rel()
    try:
        # 目标目录缺失 ⇒ 先建（⛔ 不再静默返回 None —— 静默失败正是「追加已断」没被发现的原因）
        pfile.parent.mkdir(parents=True, exist_ok=True)
        # R15.1: 追加前清洗(去系统提示行/截断残留/重复段), 防"避坑清单尾部被日志污染"
        issue = _cap_par(_clean_vault_text(issue_text), 300)
        if len(issue) < 6:
            print("[OBSIDIAN] append_pitfall 拒绝: 内容为空/仅系统回声或截断残留")
            return None
        txt = pfile.read_text(encoding="utf-8", errors="ignore") if pfile.exists() else ""
        if issue in txt:
            return str(pfile)
        marker = "> [!warning] 按标签聚合的坑"
        entry = f"- [{time.strftime('%Y-%m-%d')}] {issue}"
        if marker in txt:
            txt = txt.replace(marker, marker + chr(10) + entry, 1)
        else:
            txt += chr(10) + chr(10) + marker + chr(10) + entry + chr(10)
        write_text_lf(pfile, txt)
        return str(pfile)
    except Exception as e:
        print(f"[OBSIDIAN] 踩坑追加失败: {e}")
        return None


# ===== 知识键的路径解析: 目录一律走配置（⛔ 不写死 `SOPs/`）=====
# 2026-09-28: 写死 `SOPs/` 时 vault 根无该目录 ⇒ 3 个固定键 + 避坑清单 4/4 断链
# （CEO ② 已一手证：真件在 `工作区/SOPs/SOPs/`）。⇒ 目录走 cfg，换布局不改代码。
def _sops_dir():
    """SOP 目录（vault 相对）—— cfg ``obsidian.sops_dir`` 为唯一来源。"""
    return _cfg_roots()[0]  # 单一来源: 见 _cfg_roots


def _sops_rel(filename):
    """SOP 的 vault 相对路径 = <sops_dir>/<filename>。"""
    return "%s/%s" % (_sops_dir(), filename)


def _pitfalls_rel():
    """避坑清单的 vault 相对路径（cfg ``pitfalls_dir`` ＋ ``pitfalls_file``）。"""
    _cfg = _obsidian_cfg()
    _d = _cfg_roots()[1]  # 单一来源: 见 _cfg_roots
    _f = str(_cfg.get("pitfalls_file") or "避坑清单.md")
    return "%s/%s" % (_d, _f)


def _knowledge_rel_map():
    """{vault 相对路径: (知识键, 描述)} —— 供清单标注（逐件读配置太贵 ⇒ 一次算好）。"""
    out = {}
    for _k, _info in _KNOWLEDGE_FILES.items():
        out[_sops_rel(_info["file"])] = (_k, _info.get("desc", ""))
    out[_pitfalls_rel()] = ("避坑清单", "避坑清单(跨任务坑汇总)")
    return out


# ===== 2026-08-30 知识迁移: 常驻四个知识文件的自动维护 =====
# 固定映射: 知识键 → (vault 相对路径, 描述, 任务关键词)
_KNOWLEDGE_FILES = {
    "平台发布工作流": {
        "file": "平台发布工作流.md",
        "desc": "平台发布工作流(知乎/小红书/B站/抖音 SOP)",
        "keywords": ("发布", "知乎", "小红书", "B站", "抖音", "平台", "上传", "草稿", "图文"),
        "sandbox_rel": "docs/reports/platform_publish_workflow.md",
    },
    "番茄推广SOP": {
        "file": "番茄推广SOP.md",
        "desc": "番茄推广完整落地 SOP(选书/别名/回填)",
        "keywords": ("番茄", "别名", "达人", "推广", "回填", "选书"),
        "sandbox_rel": "docs/reports/fanqie_promotion_sop.md",
    },
    "视频制作SOP": {
        "file": "视频制作SOP.md",
        "desc": "视频制作 SOP(脚本/分镜/配音/B站)",
        "keywords": ("视频", "脚本", "分镜", "配音", "B站", "bilibili", "剪辑"),
        "sandbox_rel": "docs/reports/bilibili_video_script.md",
    },
}


def sync_knowledge_to_sandbox(sandbox_base=None):
    """D4 单一真源(2026-08-30): vault → 沙箱 docs/reports 单向同步。

    vault 是 SOP 唯一真源; 沙箱 docs/reports 的对应文件是**只读镜像**。
    调用时机: 网关启动 / obsidian_knowledge 写操作后 / 任务开始时。
    sandbox_base: 沙箱根(默认从 _get_sandbox_base 推断失败则跳过)。
    返回 [(sop_key, synced|skipped), ...]。
    """
    cfg = _obsidian_cfg()
    if not cfg.get("enabled"):
        return []
    root = Path(_vault_path())
    out = []
    for key, info in _KNOWLEDGE_FILES.items():
        src = root / _sops_rel(info["file"])
        if not src.exists():
            out.append((key, "skipped_no_vault"))
            continue
        if not sandbox_base:
            try:
                from core.lib.gateway_helpers import _get_sandbox_base

                sandbox_base = _get_sandbox_base("default", "default")
            except Exception:
                out.append((key, "skipped_no_sandbox"))
                continue
        dst = Path(sandbox_base) / info["sandbox_rel"]
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            _vtxt = src.read_text(encoding="utf-8", errors="ignore")
            _same = dst.exists() and dst.read_text(encoding="utf-8", errors="ignore") == _vtxt
            if not _same:
                dst.write_text(_vtxt, encoding="utf-8")
                out.append((key, "synced"))
            else:
                out.append((key, "same"))
        except Exception as _se:
            out.append((key, f"error:{_se}"))
    return out


def _resolve_knowledge_path(sop_key):
    """按知识键解析 vault 绝对路径。返回 Path 或 None。

    R4(2026-08-31): 支持任意 vault 相对路径 — 除固定 SOP/避坑清单外,
    sop_key 可为 相对路径(如 '微信公众号/公众号.md'、'Clippings/xxx')或 Reviews/xxx,
    使 Agent 能读任何已登记/剪藏文件, 不再只认 4 个固定键。
    """
    cfg = _obsidian_cfg()
    if not cfg.get("enabled"):
        return None
    root = Path(_vault_path())
    key = str(sop_key or "").strip()
    if key in _KNOWLEDGE_FILES:
        return root / _sops_rel(_KNOWLEDGE_FILES[key]["file"])
    if key == "避坑清单":
        return root / _pitfalls_rel()
    # R4: 任意相对路径(含子目录) — 规范化后拼接, 防路径逃逸(../)
    if key and not key.startswith("/"):
        _clean = key.replace("\\", "/")
        # 防 ../ 逃逸: 拒绝任何路径穿越片段
        if ".." in [seg for seg in _clean.split("/")]:
            return None
        _cand = root / _clean
        if _cand.exists() and _cand.is_file():
            return _cand
        # 兼容 Reviews/xxx 无 .md 后缀
        if _cand.exists() and _cand.is_dir():
            return None
    return None


def read_knowledge_file(sop_key, max_chars=4000):
    """读取常驻知识文件内容(供 Agent 任务前查阅 SOP/避坑清单/复盘)。

    sop_key: 平台发布工作流 | 番茄推广SOP | 视频制作SOP | 避坑清单
          或 Reviews/<复盘文件名>(如 "Reviews/2026-08-30-8060425102_5", 去 .md)
    R2 修复(2026-08-30): 支持 Reviews 复盘 — Agent 任务前可读上次复盘,
    不再翻 goal JSON 找"上次发生了什么"。
    返回 {"content": str, "path": str, "exists": bool} 或 None(vault 未启用/未知键)。
    """
    fpath = _resolve_knowledge_path(sop_key)
    if fpath is None:
        # R2: Reviews/xxx 前缀 → 解析为 vault Reviews 目录下的文件
        _key = str(sop_key or "").strip()
        if _key.startswith("Reviews/"):
            cfg = _obsidian_cfg()
            if cfg.get("enabled"):
                _rp = (
                    Path(_vault_path())
                    / "Reviews"
                    / (_key[len("Reviews/") :] + (".md" if not _key.endswith(".md") else ""))
                )
                if _rp.exists():
                    fpath = _rp
        if fpath is None:
            return None
    if not fpath.exists():
        return {"content": "", "path": str(fpath), "exists": False}
    try:
        txt = fpath.read_text(encoding="utf-8", errors="ignore")
        return {"content": txt[:max_chars], "path": str(fpath), "exists": True, "truncated": len(txt) > max_chars}
    except Exception as e:
        print(f"[OBSIDIAN] 读取知识失败: {e}")
        return {"content": "", "path": str(fpath), "exists": True}


def list_knowledge_files():
    """列出 vault 完整目录树(递归所有 .md, 含 sub 分类), 供 Agent/前端了解知识库结构。

    R4(2026-08-31): 原只列 4 个固定 SOP + 避坑清单 → 用户手动目录(微信公众号/ 等)
    与 Clippings 剪藏不可见 → Agent 误报「未登记」。现返回全部 .md(带相对路径/分类)。
    """
    cfg = _obsidian_cfg()
    if not cfg.get("enabled"):
        return []
    root = Path(_vault_path())
    skip = set(_exclude_dirs())
    _rel_map = _knowledge_rel_map()  # 逐件读配置太贵 ⇒ 一次算好
    out = []
    for f in _walk_vault_md(root, skip):
        rel = f.relative_to(root).as_posix()
        if _rel_excluded(rel, skip):
            continue
        sub = _reviews_sub_label(rel)  # 批198: 复盘迁到「聊天区/复盘」后仍按 Reviews 加权
        # 固定 SOP / 避坑清单 保留 key/desc(兼容旧调用); 其余通用文件仅路径/分类
        _key, _desc = _rel_map.get(rel, (None, None))
        out.append(
            {
                "key": _key,
                "desc": _desc,
                "path": str(f),
                "rel_path": rel,
                "exists": True,
                "type": sub,
                "name": f.name.replace(".md", ""),
            }
        )
    # 兼容: 避坑清单若在 Pitfalls 下也会被 rglob 覆盖(带 type=pitfalls 标记)
    return out


def update_sop(sop_key, section_title, content, append=False):
    """向指定 SOP 文件追加/更新一个小节(带日期), 更新 frontmatter updated。

    sop_key: 平台发布工作流 | 番茄推广SOP | 视频制作SOP
    section_title: 小节标题(如 "抖音图文发布 2026-08-26")
    content: 小节正文(markdown)
    append=True: 始终追加; 默认同名小节覆盖、不同名追加。
    返回笔记路径或 None。同 key+title+content 已存在 → 不重复写。
    """
    cfg = _obsidian_cfg()
    if not cfg.get("enabled"):
        return None
    info = _KNOWLEDGE_FILES.get(str(sop_key or "").strip())
    if not info:
        print(f"[OBSIDIAN] 未知知识键: {sop_key}, 可选: {list(_KNOWLEDGE_FILES)}")
        return None
    root = Path(_vault_path())
    fpath = root / _sops_rel(info["file"])
    try:
        title = str(section_title or "").strip()[:60]
        body = str(content or "").strip()[:3000]
        if not title or not body:
            return None
        # 2026-08-30 质量加固: 剔除工具输出流水行(Agent 误把 execute_command/python3 输出贴进 SOP)
        _clean_lines = []
        for _l in body.split(chr(10)):
            _ls = _l.strip()
            if not _ls:
                _clean_lines.append(_l)
                continue
            if _ls.startswith(
                (
                    "execute_command",
                    "read_file",
                    "list_dir",
                    "search_files",
                    "browser_local",
                    "write_file",
                    "python3 ",
                    "total ",
                    "drwx",
                    "-rw-",
                )
            ):
                continue  # 工具输出/命令回显 → 丢弃
            _clean_lines.append(_l)
        body = chr(10).join(_clean_lines).strip()[:3000]
        if not body:
            print(f"[OBSIDIAN] SOP 内容净化后为空, 拒绝写入: {title}")
            return None
        fpath.parent.mkdir(parents=True, exist_ok=True)
        txt = fpath.read_text(encoding="utf-8", errors="ignore") if fpath.exists() else ""
        date = time.strftime("%Y-%m-%d")
        # frontmatter 兜底(文件缺失/无 frontmatter 时补)
        if not txt.strip().startswith("---"):
            fm = (
                f"---{chr(10)}type: sop{chr(10)}tags: [{sop_key}, SOP]{chr(10)}"
                f"created: {date}{chr(10)}updated: {date}{chr(10)}---{chr(10)}"
            )
            txt = fm + txt
        block = f"## {title}{chr(10)}{chr(10)}{body}"
        if not append and f"## {title}" in txt:
            txt = re.sub(rf"(?m)^## {re.escape(title)}.*?(?=^## |\Z)", block, txt, count=1, flags=re.S)
        elif "## 相关" in txt:
            # 新小节插到"## 相关"之前(相关双链保持文件末尾)
            txt = txt.replace("## 相关", block + chr(10) + chr(10) + "## 相关", 1)
        else:
            txt = txt.rstrip() + chr(10) + chr(10) + block + chr(10)
        txt = re.sub(r"(?m)^updated:.*$", f"updated: {date}", txt, count=1)
        write_text_lf(fpath, txt)
        # D4 单一真源(2026-08-30): vault 写后同步沙箱镜像(docs/reports), 防三份漂移
        try:
            _sb = info.get("sandbox_rel")
            if _sb:
                from core.lib.gateway_helpers import _get_sandbox_base as _gsb_sync

                _sb_base = _gsb_sync("default", "default")
                if _sb_base:
                    _dst = Path(_sb_base) / _sb
                    _dst.parent.mkdir(parents=True, exist_ok=True)
                    _dst.write_text(txt, encoding="utf-8")
                    print(f"[OBSIDIAN] SOP 已同步沙箱镜像: {_sb}")
        except Exception as _sync_err:
            print(f"[OBSIDIAN] SOP 沙箱同步失败(忽略): {_sync_err}")
        return str(fpath)
    except Exception as e:
        print(f"[OBSIDIAN] SOP 更新失败: {e}")
        return None


def auto_maintain_knowledge(task_title, messages=None, tool_steps=None, mined=None):
    """任务完成后自动维护常驻知识: 踩坑 → 避坑清单.md; 可复用经验 → 相关 SOP。

    由 _write_turn_end(completed) 调用, 复用 _mine_review_sections 挖掘结果。
    task_title: 目标文本(用于选 SOP); mined: 可选, 已挖掘的 {关键决策/踩坑/可复用经验}。
    """
    if not _obsidian_cfg().get("enabled"):
        return []
    try:
        if mined is None:
            mined = _mine_review_sections(messages, tool_steps)
        writes = []
        # 1) 踩坑 → 避坑清单.md(逐条, 幂等)
        pitfalls = [p.strip() for p in (mined.get("踩坑") or "").split(chr(10)) if p.strip() and len(p.strip()) >= 6]
        for p in pitfalls[:6]:
            w = append_pitfall(p)
            if w:
                writes.append(("pitfall", w))
        # 2) 可复用经验/关键决策 → 匹配的 SOP
        exp = (mined.get("可复用经验") or "").strip()
        dec = (mined.get("关键决策") or "").strip()
        title = str(task_title or "")
        hit = None
        _best_hits = 0
        for key, info in _KNOWLEDGE_FILES.items():
            _n = sum(1 for k in info["keywords"] if k in title)
            if _n > _best_hits:  # 命中关键词最多者优先(如"番茄推广发布"→番茄推广SOP 2 命中)
                _best_hits = _n
                hit = key

        # 经验质量门槛(2026-08-30): 纯命令噪音(ls 回显等)已被 _mine_review_sections 过滤,
        # 但仍要求有实质内容(含工具名+结果), 避免把流水账写进 SOP
        def _meaningful(txt):
            # 2026-08-30 收紧: 工具输出流水(execute_command/read_file 等 + ":" 冒号)不算经验
            lines = [
                l.strip()
                for l in txt.split(chr(10))
                if l.strip()
                and not l.startswith(
                    ("execute_command", "read_file", "list_dir", "search_files", "browser_local", "write_file")
                )
            ]
            return lines and any(
                ("用" in l or "选择" in l or "→" in l or "成功" in l or "经验" in l or "以后" in l) for l in lines
            )

        if hit and exp and _meaningful(exp):
            # 同名小节(当天)覆盖更新 — 避免同日多次完成叠加重复小节头
            w = update_sop(hit, f"任务沉淀 {time.strftime('%Y-%m-%d')}", exp[:1500], append=False)
            if w:
                writes.append(("sop", w))
        if hit and dec and not exp and _meaningful(dec):
            w = update_sop(hit, f"任务决策 {time.strftime('%Y-%m-%d')}", dec[:1200], append=False)
            if w:
                writes.append(("sop", w))
        return writes
    except Exception as e:
        print(f"[OBSIDIAN] 自动维护失败: {e}")
        return []


def unified_inject(*, messages, data_resp, is_read_only, file_missing):
    """统一注入点（S4，从 _v9_bridge_loop 归位，2026-09-12）：阶段提示 + 已读目标文件提示。

    契约：原地修改 data_resp["choices"][0]["message"]["content"]，返回 None。
    is_read_only / file_missing 由调用方（bridge_loop 的写入意图检测 v3 段）计算后传入——
    二者依赖当前轮被拦截/改写过的 msg.tool_calls，不能在本函数内从 data_resp 重算。
    """
    import re as _re4

    from core.gateway.context_validator import (
        _check_recent_writes,
        _classify_task_type,
        _is_readonly_task,
        _should_inject_hint,
    )

    _user_msgs = [m for m in messages if m["role"] == "user"]
    _last_user_msg = _user_msgs[-1]["content"] if _user_msgs else ""
    _has_write_intent = any(
        kw in _last_user_msg for kw in ["修改", "创建", "添加", "修复", "实现", "完善", "写入", "重构", "写", "改", "解决", "优化", "更新"]
    )
    _recent_msgs = [m for m in messages[-6:] if m["role"] == "assistant"]
    _has_read_target = any(
        "read_file" in str(tc.get("function", {}).get("name", ""))
        for m in _recent_msgs
        for tc in m.get("tool_calls", [])
    )
    _target = _last_user_msg
    _file_match = _re4.search(r"[\w/]+\.\w+", _target)
    _target_file = _file_match.group(0) if _file_match else "目标文件"
    _action_words = ["重写", "修改", "创建", "添加", "修复", "实现", "完善", "增加", "删除", "更新"]
    _has_action = any(w in _last_user_msg for w in _action_words)
    _has_action = _has_action and not any(w in _last_user_msg for w in ["只读", "排查", "分析报告", "设计方案", "输出方案", "盘点", "设计"])
    _has_write = _check_recent_writes(messages)
    _need_inject = (_has_write_intent and is_read_only and file_missing) or (
        _has_action and not _has_write and _has_read_target
    )
    if _need_inject and not _is_readonly_task(_last_user_msg):
        if _classify_task_type(messages) == "analysis":
            hint_msg2 = "[系统] 当前阶段：分析。请输出分析报告。\n"
        elif _has_read_target:
            hint_msg2 = (
                f"[系统] 你已读取 {_target_file}，现在立即写入修改。\n"
                f"不要继续读取其他文件，不要只输出计划。\n"
                f"用 write_file 或 python3 heredoc 写入完整内容。\n"
            )
        else:
            hint_msg2 = "[系统] 当前阶段：交付。请用 write_file 或 python3 heredoc 将修改写入文件。如果需要参考已有代码，直接写入后再用 read_file 验证。\n"
        # 方案三防御：如果 content 已以 [系统] 开头，追加而非覆盖
        if _should_inject_hint(messages, hint_msg2):
            _cur2 = data_resp["choices"][0]["message"].get("content", "") or ""
            if _cur2.startswith("[系统]"):
                data_resp["choices"][0]["message"]["content"] = _cur2 + "\n\n" + hint_msg2
            elif _cur2:
                data_resp["choices"][0]["message"]["content"] = hint_msg2 + "\n\n" + _cur2
            else:
                data_resp["choices"][0]["message"]["content"] = hint_msg2
