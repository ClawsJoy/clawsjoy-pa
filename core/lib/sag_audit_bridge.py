"""R1 落盘检索编目 — 统一 SAG 注册桥（图书馆编目入口）

所有非代码落盘数据（审计/越权/快照/goal/说明书）通过本模块注册进 SAG
（code_entities 表），使 query_index 可检索。DB 不可用时自动降级（仅落盘，
不影响现有行为）。
"""
import os
import time

# 懒加载：extractor 在 DATABASE_URL 缺失时会抛 ValueError，延迟到首次调用
_extractor = None
_extractor_loaded = False

# 降级态自印（老板 2026-10-03 裁：两态各留一行带刻 + 报压制了多少条）
_DEG = {"down": False, "suppressed": 0}


def _ts():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _note_degraded(exc):
    """状态变化时才打一行（不是每次调用都打 —— 否则 2,991 行刷屏）。"""
    _DEG["suppressed"] += 1
    if not _DEG["down"]:
        _DEG["down"] = True
        print("[SAG_BRIDGE][DEGRADE %s] 编目不可用，转「仅落盘」：%s" % (_ts(), exc))
    elif _DEG["suppressed"] % 500 == 0:
        print("[SAG_BRIDGE][DEGRADE %s] 降级中，累计压制 %d 条" % (_ts(), _DEG["suppressed"]))


def _note_recovered():
    if _DEG["down"]:
        print("[SAG_BRIDGE][RECOVER %s] 编目恢复；降级期间压制 %d 条" % (_ts(), _DEG["suppressed"]))
    _DEG["down"] = False
    _DEG["suppressed"] = 0


def _get_extractor():
    """懒加载 SAG extractor；失败返回 None（降级）"""
    global _extractor, _extractor_loaded
    if _extractor_loaded:
        return _extractor
    _extractor_loaded = True
    try:
        from core.lib.code_entity_extractor import extractor
        _extractor = extractor
    except Exception as e:
        print(f"[SAG_BRIDGE] extractor 加载失败(降级为仅落盘): {e}")
        _extractor = None
    return _extractor


def register_entity(entity_type, entity_name, signature="", file_path="", related_entities=None):
    """把一条落盘记录注册进 SAG（编目）。DB 不可用时静默降级。

    参数对齐 code_entities schema：
    - entity_type: 编目分类（audit_event/escalation/snapshot/goal/manual）
    - entity_name: 实体名（如工具名/目标摘要）— 与 file_path 组合为 ON CONFLICT 键
    - signature:   内容签名/摘要
    - file_path:   关联路径（如 session_id/快照文件路径）
    - related_entities: 关联实体列表（如 [user_id, session_id]）
    """
    try:
        ext = _get_extractor()
        if ext is None:
            return False
        _ok = ext.upsert_entity({
            "entity_type": entity_type,
            "entity_name": str(entity_name)[:200],
            "signature": str(signature)[:2000],
            "file_path": str(file_path)[:500],
            "related_entities": related_entities or [],
        })
        if _ok:
            _note_recovered()
        return _ok
    except Exception as e:
        _note_degraded(e)
        return False


def query_entities(entity_type=None, query=None, limit=50, project_id="default"):
    """统一检索 SAG 实体（按 entity_type 过滤 + 关键词匹配）。

    返回 list[dict]：{"entity_type", "entity_name", "signature", "file_path", "related_entities"}
    DB 不可用返回 []。
    """
    try:
        import psycopg2
        ext = _get_extractor()
        if ext is None:
            return []
        db_url = ext.db_url
        if not db_url:
            print("[SAG_BRIDGE] DB URL 不可用，query_entities 返回空")
            return []
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        sql = "SELECT entity_type, entity_name, signature, file_path, related_entities FROM code_entities WHERE project_id = %s"
        params = [project_id]
        if entity_type:
            sql += " AND entity_type = %s"
            params.append(entity_type)
        if query:
            sql += " AND (entity_name ILIKE %s OR signature ILIKE %s)"
            like = f"%{query}%"
            params.extend([like, like])
        sql += " ORDER BY id DESC LIMIT %s"
        params.append(int(limit))
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {"entity_type": r[0], "entity_name": r[1], "signature": r[2],
             "file_path": r[3], "related_entities": r[4]}
            for r in rows
        ]
    except Exception as e:
        print(f"[SAG_BRIDGE] query_entities 失败: {e}")
        return []


def register_manual(doc_path=None):
    """注册说明书文档（entity_type=manual）进 SAG。启动时调用。

    doc_path: 说明书路径，默认 config/prompts/agent_manual.md。
    """
    try:
        path = doc_path or "config/prompts/agent_manual.md"
        from pathlib import Path
        p = Path(path)
        if not p.exists():
            print(f"[SAG_BRIDGE] manual 文档不存在: {path}")
            return False
        text = p.read_text(encoding="utf-8")
        # 提取各章节标题作为实体名（每章一条，便于按需检索）
        import re
        sections = re.findall(r"^##\s+(.+)$", text, re.MULTILINE)
        names = sections if sections else [p.stem]
        _any_ok = False
        for name in names[:12]:
            if register_entity("manual", name.strip()[:200], text[:1500], str(path), ["agent_manual"]):
                _any_ok = True
        return _any_ok
    except Exception as e:
        print(f"[SAG_BRIDGE] register_manual 失败: {e}")
        return False
