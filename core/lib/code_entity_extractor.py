"""代码实体自动抽取器 — 写入时自动入库 + 查询时动态超边"""

import ast
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool

try:
    import redis as redis_lib
except Exception:
    redis_lib = None
import logging

logger = logging.getLogger(__name__)


# ===== 检索域闸（老板 2026-10-03 裁 · 域 ＝ default）=====
# 域 ＝ "default"：本检索器只认 default 域之件；改域 ⇒ 改此处一处（⛔ 散成字面常量多处）。
SEARCH_DOMAIN_PROJECT_ID = "default"


def _format_path_for_agent(path: str) -> str:
    """统一输出 clawsjoy_dev/xxx 格式的路径给 Agent（与网关同逻辑）"""
    if not path:
        return path
    if path.startswith("clawsjoy_dev/") and path.count("clawsjoy_dev/") == 1:
        return path
    if path.count("clawsjoy_dev/") > 1:
        return "clawsjoy_dev/" + path.split("clawsjoy_dev/")[-1]
    if "/clawsjoy_dev/" in path:
        return "clawsjoy_dev/" + path.split("/clawsjoy_dev/", 1)[1]
    if not path.startswith("/") and "clawsjoy_dev/" not in path:
        return "clawsjoy_dev/" + path
    return path


# ===== 检索精度闸（老板 2026-10-03 裁 · 最小词长 + 词边界）=====
# 判例（修前）：`"no"` 命中 `no_proxy`（`"no" ⊂ "nexi**no**stent"`）、
# `"clean"` 命中 `cleanup_task_context`（`"clean" ⊂ "**clean**_neg"`）⇒
# 任取一个乱串都能命中 ⇒ **「反例空」这一判据在修前恒不成立**（常态之值非零 ⇒ 面作废）。
_KW_MIN_ASCII = 3
_KW_MIN_CJK = 2
_KW_SPLIT_RE = re.compile(r"[_\-\./\s]+")


def query_tokens(query: str) -> set:
    """把 query 切成可比 token（小写）：ASCII 按 `_ - . /` 与空白拆分，CJK 段整体保留。"""
    _q = str(query or "").lower()
    _toks = set()
    for _seg in re.findall(r"[\u4e00-\u9fff]+", _q):
        if len(_seg) >= _KW_MIN_CJK:
            _toks.add(_seg)
    for _ident in re.findall(r"[a-z0-9][a-z0-9_]*", _q):
        for _p in _KW_SPLIT_RE.split(_ident):
            if len(_p) >= _KW_MIN_ASCII:
                _toks.add(_p)
    return _toks


def kw_hit(keyword: str, tokens) -> bool:
    """关键词是否命中：**token 全等**（⛔ 不用裸子串），ASCII token 须 >= 3 字符。"""
    _k = str(keyword or "").lower().strip()
    if not _k:
        return False
    if re.search(r"[\u4e00-\u9fff]", _k):
        return any(len(_t) >= _KW_MIN_CJK and (_t in _k or _k in _t) for _t in tokens)
    for _p in _KW_SPLIT_RE.split(_k):
        if len(_p) >= _KW_MIN_ASCII and _p in tokens:
            return True
    return False


def boundary_hit(term: str, text: str) -> bool:
    """`term` 在 `text` 中按**词边界**命中。

    `_` 计作边界 ⇒ `extractor` 命中 `code_entity_extractor`（保留 snake_case 召回），
    而 `no` ⛔ 不命中 `nonexistent`（`n` 是字母 ⇒ 非边界）。
    """
    _t = str(term or "").lower()
    _s = str(text or "").lower()
    if not _t or not _s:
        return False
    if re.search(r"[\u4e00-\u9fff]", _t):
        return _t in _s
    if len(_t) < _KW_MIN_ASCII:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(_t) + r"(?![a-z0-9])", _s) is not None


def _chinese_query_terms(query: str) -> list:
    """中文 query 拆分为整句 + 中文段 + 二元组；补充英文标识符（下划线拆分）与数字，提升 ILIKE 召回率"""
    terms = [query]
    for seg in re.findall(r"[\u4e00-\u9fff]+", query):
        if len(seg) >= 2:
            terms.append(seg)
            terms.extend(seg[i : i + 2] for i in range(len(seg) - 1))
    # 英文标识符：整体 + 下划线拆分 token
    for ident in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", query):
        terms.append(ident)
        terms.extend(part for part in ident.split("_") if part)
    # 数字 token
    terms.extend(re.findall(r"\d+", query))
    # 检索精度闸（老板 2026-10-03 裁 · 最小词长）：ASCII 词元 < 3 字符不参与匹配。
    terms = [t for t in terms if re.search(r"[\u4e00-\u9fff]", t) or len(t.strip()) >= _KW_MIN_ASCII]
    return list(dict.fromkeys(terms))


def _ts():
    return time.strftime("%Y-%m-%d %H:%M:%S")


class DbUnavailable(RuntimeError):
    """DB 不可达（断路器打开时抛出）：不建连、不重试。"""


class _DbBreaker:
    """DB 不可达断路器：一次探测 -> 指数退避(1,2,4,...) -> 封顶 300s。

    为什么需要：``_get_extractor()`` 是惰性构造，库不在时**每次调用**都会新建
    连接池并各开一条 TCP 连接。实测 2026-10-03 19:27 那一跑：2,991 次
    ``port 5432 failed``、启动 6 min 40 s。

    纪律（老板 2026-10-03 裁）：降级 / 恢复两态各留一行**带刻**；
    退避期间须报**压制了多少条**（静默压制又成假绿）。
    """

    def __init__(self, base: float = 1.0, cap: float = 300.0):
        self._base = base
        self._cap = cap
        self._lock = threading.Lock()
        self._fails = 0
        self._open_until = 0.0
        self.skipped_downgraded = 0   # 退避窗内被压制（未建连）的调用数
        self.opened = 0    # 进入降级态次数（状态变化才 +1）

    def allow(self) -> bool:
        with self._lock:
            if time.monotonic() < self._open_until:
                self.skipped_downgraded += 1
                return False
            return True

    def ok(self):
        with self._lock:
            if self._fails:
                print("[DB_BREAKER][RECOVER %s] DB 可达，编目恢复；降级期间共压制 %d 条"
                      % (_ts(), self.skipped_downgraded))
            self._fails = 0
            self._open_until = 0.0

    def fail(self, exc):
        with self._lock:
            self._fails += 1
            delay = min(self._cap, self._base * (2 ** (self._fails - 1)))
            was_open = time.monotonic() < self._open_until
            self._open_until = time.monotonic() + delay
            if not was_open:      # 只在「降级态」这个状态变化时打
                self.opened += 1
                print("[DB_BREAKER][DEGRADE %s] DB 不可达(第 %d 次)：%s"
                      % (_ts(), self._fails, exc))
                print("[DB_BREAKER][DEGRADE %s] 退避 %.0fs（上限 %.0fs）；窗内不再建连，已压制 %d 条"
                      % (_ts(), delay, self._cap, self.skipped_downgraded))
            return delay


_DB_BREAKER = _DbBreaker()


class ConnectionPool:
    """基于 psycopg2 SimpleConnectionPool 的连接池（最小连接数 2，最大连接数 10）"""

    def __init__(self, db_url: str, minconn: int = 2, maxconn: int = 30):
        # connect_timeout：让每次探测有界（不再挂 OS 默认超时）
        if "connect_timeout" not in db_url:
            db_url = db_url + ("&" if "?" in db_url else "?") + "connect_timeout=3"
        self._pool = SimpleConnectionPool(minconn, maxconn, dsn=db_url)

    def getconn(self):
        return self._pool.getconn()

    def putconn(self, conn, close: bool = False):
        self._pool.putconn(conn, close=close)

    def closeall(self):
        self._pool.closeall()


class CodeEntityExtractor:
    """从 Python/Go/TSX 文件中抽取实体并自动入库"""

    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv("DATABASE_URL")  # 移除硬编码默认凭据，必须从环境变量读取
        if not self.db_url:
            raise ValueError("DATABASE_URL 未配置，必须通过环境变量设置数据库连接串")
        self._pool = ConnectionPool(self.db_url)
        self._init_table()

    def _init_table(self):
        try:
            conn = self._pool.getconn()
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS code_entities (
                    id SERIAL PRIMARY KEY,
                    project_id TEXT DEFAULT 'default',
                    entity_type TEXT NOT NULL,
                    entity_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    line_number INT,
                    signature TEXT,
                    related_entities TEXT[],
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(project_id, entity_name, file_path)
                )
            """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_actions (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    task_name TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    result TEXT NOT NULL,
                    file_type TEXT DEFAULT 'unknown',
                    agent_reaction TEXT DEFAULT '',
                    detail TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS task_progress (
                    id SERIAL PRIMARY KEY,
                    task_name TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    step_number INT NOT NULL,
                    step_description TEXT,
                    tool_name TEXT,
                    file_path TEXT,
                    status TEXT DEFAULT 'pending',
                    snapshot_path TEXT,
                    error_message TEXT,
                    started_at TIMESTAMP DEFAULT NOW(),
                    completed_at TIMESTAMP,
                    UNIQUE(task_name, step_number)
                )
            """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS code_edges (
                    id SERIAL PRIMARY KEY,
                    project_id TEXT DEFAULT 'default',
                    source_name TEXT NOT NULL,
                    target_name TEXT NOT NULL,
                    edge_type TEXT DEFAULT 'calls',
                    file_path TEXT,
                    weight REAL DEFAULT 1.0,
                    used_count INT DEFAULT 0,
                    ignored_count INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(project_id, source_name, target_name, edge_type)
                )
            """
            )
            cur.execute("ALTER TABLE code_edges ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()")
            cur.execute("ALTER TABLE code_edges ADD COLUMN IF NOT EXISTS weight REAL DEFAULT 1.0")
            cur.execute("ALTER TABLE code_edges ADD COLUMN IF NOT EXISTS used_count INT DEFAULT 0")
            cur.execute("ALTER TABLE code_edges ADD COLUMN IF NOT EXISTS ignored_count INT DEFAULT 0")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS steps_summary (
                    id SERIAL PRIMARY KEY,
                    task_name TEXT NOT NULL,
                    step_number INT NOT NULL,
                    summary_json JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(task_name, step_number)
                )
            """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS injection_feedback (
                    id SERIAL PRIMARY KEY,
                    task_name TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    edge_id INT,
                    source_name TEXT,
                    target_name TEXT,
                    edge_type TEXT,
                    feedback_type TEXT NOT NULL,
                    feedback_value REAL,
                    context TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """
            )
            cur.execute(
                """
                DO $$
                BEGIN
                    CREATE ROLE clawsjoy_readonly LOGIN PASSWORD 'clawsjoy_readonly_secret';
                EXCEPTION WHEN duplicate_object THEN
                    RAISE NOTICE 'clawsjoy_readonly role already exists';
                END
                $$;
            """
            )
            cur.execute("GRANT CONNECT ON DATABASE clawsjoy_dev TO clawsjoy_readonly")
            cur.execute("GRANT USAGE ON SCHEMA public TO clawsjoy_readonly")
            cur.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO clawsjoy_readonly")
            conn.commit()
            cur.close()
            self._pool.putconn(conn)
        except Exception:
            pass

    def upsert_entity(self, entity: dict, project_id: str = "default"):
        """通用实体入库：直接 INSERT/UPDATE code_entities"""
        try:
            conn = self._pool.getconn()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO code_entities (project_id, entity_type, entity_name, file_path, signature, related_entities)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (project_id, entity_name, file_path)
                DO UPDATE SET signature = EXCLUDED.signature, related_entities = EXCLUDED.related_entities
            """,
                (
                    project_id,
                    entity.get("entity_type", "unknown"),
                    entity.get("entity_name", ""),
                    entity.get("file_path", ""),
                    entity.get("signature", ""),
                    entity.get("related_entities", []),
                ),
            )
            conn.commit()
            cur.close()
            self._pool.putconn(conn)
            return True
        except Exception as e:
            print(f"[upsert_entity] 入库失败: {e}")
            return False

    def list_pending_auto_fixes(self, limit: int = 20):
        """查询待审核的自动修复建议(auto_fix_suggestion 且 status 非 approved/rejected)。"""
        try:
            conn = self._pool.getconn()
            cur = conn.cursor()
            cur.execute(
                "SELECT entity_name, signature, created_at FROM code_entities "
                "WHERE entity_type='auto_fix_suggestion' "
                "AND (status IS NULL OR status NOT IN ('approved', 'rejected')) "
                "ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            fixes = []
            for row in cur.fetchall():
                try:
                    fixes.append({"name": row[0], "detail": json.loads(row[1]), "created_at": str(row[2])})
                except Exception:
                    pass
            cur.close()
            self._pool.putconn(conn)
            return fixes
        except Exception as e:
            print(f"[list_pending_auto_fixes] 查询失败: {e}")
            return []

    def set_auto_fix_status(self, entity_name: str, status: str):
        """审核通过/拒绝：将 auto_fix_suggestion 标记为 approved/rejected。"""
        try:
            conn = self._pool.getconn()
            cur = conn.cursor()
            cur.execute(
                "UPDATE code_entities SET status = %s " "WHERE entity_type='auto_fix_suggestion' AND entity_name = %s",
                (status, entity_name),
            )
            conn.commit()
            cur.close()
            self._pool.putconn(conn)
            return True
        except Exception as e:
            print(f"[set_auto_fix_status] 更新失败: {e}")
            return False

    def create_edge(
        self,
        source: str,
        target: str,
        edge_type: str = "calls",
        project_id: str = "default",
        file_path: str = "",
        weight: float = 1.0,
    ):
        """创建实体之间的边关系"""
        try:
            conn = self._pool.getconn()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO code_edges (project_id, source_name, target_name, edge_type, file_path, weight)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (project_id, source_name, target_name, edge_type)
                DO UPDATE SET weight = code_edges.weight + EXCLUDED.weight, used_count = code_edges.used_count + 1, updated_at = NOW()
            """,
                (project_id, source, target, edge_type, file_path, weight),
            )
            conn.commit()
            cur.close()
            self._pool.putconn(conn)
            return True
        except Exception as e:
            print(f"[create_edge] 失败: {e}")
            return False

    def get_edges(self, entity_name: str = None, edge_type: str = None, project_id: str = "default", limit: int = 50):
        """查询边关系，可按实体名和边类型过滤"""
        try:
            conn = self._pool.getconn()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            conditions = ["project_id = %s"]
            params = [project_id]
            if entity_name:
                conditions.append("(source_name = %s OR target_name = %s)")
                params.extend([entity_name, entity_name])
            if edge_type:
                conditions.append("edge_type = %s")
                params.append(edge_type)
            sql = f"SELECT * FROM code_edges WHERE {' AND '.join(conditions)} ORDER BY created_at DESC LIMIT %s"
            params.append(limit)
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()
            self._pool.putconn(conn)
            return [dict(r) for r in rows]
        except Exception as e:
            print(f"[get_edges] 查询失败: {e}")
            return []

    def record_edge_feedback(self, source_name, target_name, edge_type, used=True):
        """记录边使用反馈，调整权重"""
        try:
            conn = self._pool.getconn()
            cur = conn.cursor()
            if used:
                cur.execute(
                    "UPDATE code_edges SET used_count = used_count + 1, weight = weight * 1.1 WHERE source_name=%s AND target_name=%s AND edge_type=%s",
                    (source_name, target_name, edge_type),
                )
            else:
                cur.execute(
                    "UPDATE code_edges SET ignored_count = ignored_count + 1, weight = weight * 0.9 WHERE source_name=%s AND target_name=%s AND edge_type=%s",
                    (source_name, target_name, edge_type),
                )
            conn.commit()
            cur.close()
            self._pool.putconn(conn)
        except Exception as e:
            print(f"[record_edge_feedback] 失败: {e}")

    def update_edge_learning(
        self, entity_names, used_entity_names=None, project_id: str = "default", decay_days: int = 30
    ):
        """#81 过滤网自学习：根据 Agent 对注入 SAG 节点的使用情况更新 code_edges 评分。

        规则：
        - 被使用的节点 → used_count += 1, weight += 0.1（上限 10.0）
        - 未使用的节点 → ignored_count += 1, weight -= 0.05（下限 0.1）
        - 长期未使用（updated_at 距今超过 decay_days 天）→ weight *= 0.95 衰减（下限 0.1）
        返回更新的边数；异常时返回 0。
        """
        try:
            conn = self._pool.getconn()
            cur = conn.cursor()
            used_set = set(used_entity_names or [])
            updated = 0
            for _name in entity_names or []:
                _name = str(_name).strip()
                if not _name or len(_name) > 200:
                    continue
                if _name in used_set:
                    cur.execute(
                        """
                        UPDATE code_edges
                           SET used_count = used_count + 1,
                               weight = LEAST(weight + 0.1, 10.0),
                               updated_at = NOW()
                         WHERE (source_name = %s OR target_name = %s)
                           AND project_id = %s
                    """,
                        (_name, _name, project_id),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE code_edges
                           SET ignored_count = ignored_count + 1,
                               weight = GREATEST(weight - 0.05, 0.1),
                               updated_at = NOW()
                         WHERE (source_name = %s OR target_name = %s)
                           AND project_id = %s
                    """,
                        (_name, _name, project_id),
                    )
                updated += cur.rowcount
            # 长期未使用 → weight 衰减（int 强转保证安全拼接）
            _decay_interval = f"INTERVAL '{int(decay_days)} days'"
            cur.execute(
                f"""
                UPDATE code_edges
                   SET weight = GREATEST(weight * 0.95, 0.1)
                 WHERE project_id = %s
                   AND updated_at < NOW() - {_decay_interval}
            """,
                (project_id,),
            )
            conn.commit()
            cur.close()
            self._pool.putconn(conn)
            return updated
        except Exception as e:
            print(f"[update_edge_learning] 失败: {e}")
            return 0

    def get_related_entities(
        self, entity_name: str, project_id: str = "default", hops: int = 2, limit: int = 20
    ) -> Dict:
        """加权多跳图遍历：沿 code_edges 双向递归，按路径权重降序返回关联实体"""
        try:
            conn = self._pool.getconn()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
                """
                WITH RECURSIVE traverse AS (
                    SELECT e.entity_name AS start_name, e.id AS entity_id,
                           0 AS depth, 1.0 AS path_weight
                    FROM code_entities e
                    WHERE e.project_id = %s AND e.entity_name = %s
                    UNION ALL
                    SELECT t.start_name, te.id, t.depth + 1,
                           t.path_weight * e.weight
                    FROM traverse t
                    JOIN code_edges e ON e.project_id = %s
                       AND e.source_name = (SELECT entity_name FROM code_entities WHERE id = t.entity_id)
                       AND e.target_name <> t.start_name
                    JOIN code_entities te ON te.project_id = %s AND te.entity_name = e.target_name
                    WHERE t.depth < %s
                    UNION ALL
                    SELECT t.start_name, te.id, t.depth + 1,
                           t.path_weight * e.weight
                    FROM traverse t
                    JOIN code_edges e ON e.project_id = %s
                       AND e.target_name = (SELECT entity_name FROM code_entities WHERE id = t.entity_id)
                       AND e.source_name <> t.start_name
                    JOIN code_entities te ON te.project_id = %s AND te.entity_name = e.source_name
                    WHERE t.depth < %s
                )
                SELECT ce.entity_name, ce.entity_type, ce.file_path, ce.signature,
                       MIN(t.depth) AS min_hop, MAX(t.path_weight) AS max_weight
                FROM traverse t
                JOIN code_entities ce ON ce.id = t.entity_id
                WHERE t.depth BETWEEN 1 AND %s
                GROUP BY ce.id, ce.entity_name, ce.entity_type, ce.file_path, ce.signature
                ORDER BY max_weight DESC
                LIMIT %s
            """,
                (project_id, entity_name, project_id, project_id, hops, project_id, project_id, hops, hops, limit),
            )
            rows = cur.fetchall()
            cur.close()
            self._pool.putconn(conn)
            return {"entity": entity_name, "hops": hops, "results": [dict(r) for r in rows]}
        except Exception as e:
            print(f"[get_related_entities] 查询失败: {e}")
            return {"entity": entity_name, "hops": hops, "results": []}

    def extract_and_upsert(self, filepath: str, content: str, project_id: str = "default"):
        """抽取实体并 upsert 到数据库（实体 + 图边）"""
        entities = self._extract(filepath, content)
        if not entities:
            # 无实体文件也自动创建文件→依赖（imports）图边
            self._sync_code_edges(filepath, content, [], project_id)
            return 0

        conn = self._pool.getconn()
        cur = conn.cursor()
        for e in entities:
            cur.execute(
                """
                INSERT INTO code_entities (project_id, entity_type, entity_name, file_path, line_number, signature, related_entities)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (project_id, entity_name, file_path)
                DO UPDATE SET signature = EXCLUDED.signature, related_entities = EXCLUDED.related_entities, line_number = EXCLUDED.line_number
            """,
                (project_id, e["type"], e["name"], e["file"], e["line"], e["signature"], e["related"]),
            )
        conn.commit()
        # 入库验证
        try:
            cur.execute("SELECT COUNT(*) FROM code_entities WHERE file_path = %s", (filepath,))
            db_count = cur.fetchone()[0]
            if db_count < len(entities):
                for e in entities:
                    cur.execute(
                        "INSERT INTO code_entities (project_id, entity_type, entity_name, file_path, line_number, signature, related_entities) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                        "ON CONFLICT (project_id, entity_name, file_path) "
                        "DO UPDATE SET signature = EXCLUDED.signature, related_entities = EXCLUDED.related_entities, line_number = EXCLUDED.line_number",
                        (project_id, e["type"], e["name"], e["file"], e["line"], e["signature"], e["related"]),
                    )
                conn.commit()
                cur.execute("SELECT COUNT(*) FROM code_entities WHERE file_path = %s", (filepath,))
                db_count2 = cur.fetchone()[0]
                if db_count2 < len(entities):
                    print(f"[SAG_VERIFY] FAIL: expected {len(entities)} entities, got {db_count2}, file {filepath}")
        except Exception as ve:
            print(f"[SAG_VERIFY] error: {ve}")
        cur.close()
        self._pool.putconn(conn)
        # 大文件全文索引兜底：写入 code_fulltext 实体，query_index 找不到函数时 fallback
        if len(content) > 500:
            try:
                cur.execute(
                    """
                    INSERT INTO code_entities (project_id, entity_type, entity_name, file_path, line_number, signature, related_entities)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (project_id, entity_name, file_path)
                    DO UPDATE SET signature = EXCLUDED.signature
                """,
                    (project_id, "code_fulltext", f"fulltext::{filepath}", filepath, 1, content[:5000], []),
                )
                cur.close()
            except Exception:
                pass
        # 图化：write_file 后自动创建 code_edges（文件→函数/类、函数→调用、文件→依赖）
        self._sync_code_edges(filepath, content, entities, project_id)
        # 图化：write_file 后增量更新 dependency_graph.json（仅更新当前文件条目）
        _dep_imports = self._extract_import_paths(content)
        self.update_dependency_graph(filepath, _dep_imports)
        # #87 依赖图边入库 SAG（entity_type=dependency_edge，幂等）
        self.sync_dependency_edges_to_sag(filepath, _dep_imports)
        return len(entities)

    def _sync_code_edges(self, filepath: str, content: str, entities: List[Dict], project_id: str = "default") -> int:
        """write_file 后自动创建 code_edges 图边：

        - 文件 → 函数（contains）
        - 文件 → 类（contains）
        - 函数 → 调用（calls）
        - 文件 → 依赖（imports）
        """
        # 类型保护：entities 必须为 List[Dict]；_extract 偶发返回字符串时直接忽略
        if isinstance(entities, str) or not isinstance(entities, list):
            entities = []
        # 过滤非 dict 元素，避免 e.get 在非 dict 上 AttributeError
        entities = [e for e in entities if isinstance(e, dict)]
        file_node = _format_path_for_agent(filepath)
        edges = []
        # 1) 文件 → 函数/类（包含关系）
        for e in entities or []:
            if e.get("type") in ("function", "type"):
                edges.append((file_node, e.get("name", ""), "contains"))
        # 2) 函数 → 调用（调用关系）
        for e in entities or []:
            if e.get("type") == "function":
                for callee in e.get("related", []) or []:
                    edges.append((e.get("name", ""), callee, "calls"))
        # 3) 文件 → 依赖（导入关系）
        for mod in self._extract_imports(content):
            edges.append((file_node, mod, "imports"))
        edges = [(s, t, et) for s, t, et in edges if s and t]
        if not edges:
            return 0
        try:
            conn = self._pool.getconn()
            cur = conn.cursor()
            for src, tgt, etype in edges:
                cur.execute(
                    """
                    INSERT INTO code_edges (project_id, source_name, target_name, edge_type, file_path, weight)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (project_id, source_name, target_name, edge_type)
                    DO UPDATE SET weight = code_edges.weight + EXCLUDED.weight,
                                  used_count = code_edges.used_count + 1,
                                  updated_at = NOW()
                """,
                    (project_id, src, tgt, etype, filepath, 1.0),
                )
            conn.commit()
            cur.close()
            self._pool.putconn(conn)
            return len(edges)
        except Exception as e:
            print(f"[_sync_code_edges] 建边失败: {e}")
            return 0

    def update_dependency_graph(self, filepath: str, imports: List[str] = None) -> int:
        """write_file 后增量更新 dependency_graph.json（仅更新当前文件条目）。

        - imports 为空时自动从文件内容重新提取 import 语句
        - 增量更新：只更新当前文件对应的 key，不重写其他文件条目
        - 写入时加文件锁（fcntl.flock），防止并发写冲突；写回采用原子替换
        """
        graph_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dependency_graph.json")
        key = _format_path_for_agent(filepath).rsplit("/", 1)[-1]

        if imports is None:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except (OSError, IOError):
                content = ""
            imports = self._extract_import_paths(content)

        imports = list(dict.fromkeys(imports or []))[:30]

        # 文件锁：串行化 读→改→写 临界区，防止并发写冲突
        lock_path = graph_path + ".lock"
        try:
            import fcntl
        except ImportError:
            fcntl = None

        lock_f = open(lock_path, "a+", encoding="utf-8")
        try:
            if fcntl is not None:
                fcntl.flock(lock_f, fcntl.LOCK_EX)
            try:
                try:
                    with open(graph_path, "r", encoding="utf-8") as f:
                        graph = json.load(f)
                except (OSError, ValueError):
                    graph = {}
                if not isinstance(graph, dict):
                    graph = {}
                # 增量更新：只覆盖当前文件条目，不影响其他文件
                graph[key] = imports
                # 原子写回：先写临时文件再 os.replace，避免半截 JSON
                tmp_path = graph_path + ".tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(graph, f, ensure_ascii=False, indent=2)
                    f.write("\n")
                os.replace(tmp_path, graph_path)
            finally:
                if fcntl is not None:
                    fcntl.flock(lock_f, fcntl.LOCK_UN)
        finally:
            lock_f.close()
        return len(imports)

    def sync_dependency_edges_to_sag(self, filepath: str, imports: List[str] = None) -> int:
        """#87 dependency_graph 边入库 SAG（entity_type=dependency_edge，幂等）。

        entity_name: f"edge::{source}::{target}"
        signature: {"source":..., "target":..., "type":"imports"}
        """
        if imports is None:
            try:
                with open(filepath, "r", encoding="utf-8") as _f:
                    _content = _f.read()
            except (OSError, IOError):
                _content = ""
            imports = self._extract_import_paths(_content)
        _source = _format_path_for_agent(filepath).rsplit("/", 1)[-1]
        _count = 0
        for _imp in list(dict.fromkeys(imports or []))[:30]:
            try:
                self.upsert_entity(
                    {
                        "entity_type": "dependency_edge",
                        "entity_name": f"edge::{_source}::{_imp}",
                        "signature": json.dumps(
                            {"source": _source, "target": _imp, "type": "imports"}, ensure_ascii=False
                        ),
                        "file_path": filepath,
                    }
                )
                _count += 1
            except Exception:
                pass
        return _count

    def update_task_progress(
        self,
        task_name: str,
        session_id: str,
        step_number: int,
        step_description: str = "",
        tool_name: str = "",
        file_path: str = "",
        status: str = "in_progress",
        error_message: str = "",
    ):
        """更新任务步骤进度"""
        try:
            # 任务3 v7 防御: step_number 必须是 int(曾有调用方把 file_path 传入导致 SQL integer 类型错误)
            try:
                _step_int = int(step_number)
            except (TypeError, ValueError):
                _step_int = 0
            conn = self._pool.getconn()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO task_progress (task_name, session_id, step_number, step_description, tool_name, file_path, status, error_message, started_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (task_name, step_number)
                DO UPDATE SET status = EXCLUDED.status,
                              error_message = EXCLUDED.error_message,
                              completed_at = CASE WHEN EXCLUDED.status IN ('completed', 'failed', 'rolled_back') THEN NOW() ELSE task_progress.completed_at END
            """,
                (task_name, session_id, _step_int, step_description, tool_name, file_path, status, error_message),
            )
            conn.commit()
            cur.close()
            self._pool.putconn(conn)
        except Exception as e:
            logger.warning(f"[code_entity_extractor] 更新 task_progress 失败: {e}")

    def insert_agent_action(
        self,
        session_id: str,
        task_name: str,
        tool_name: str,
        result: str,
        file_type: str = "unknown",
        agent_reaction: str = "",
        detail: str = "",
        capability_chain: list = None,
    ):
        """插入 Agent 行为记录到 agent_actions 表

        #97 修复：capability_chain 为可选项（原 record_step 传入但签名缺失 → TypeError）。
        表无独立列，序列化追加到 detail 保留信息。
        """
        try:
            if capability_chain:
                _extra = json.dumps({"capability_chain": capability_chain}, ensure_ascii=False)
                detail = (detail + chr(10) + _extra) if detail else _extra
            conn = self._pool.getconn()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO agent_actions (session_id, task_name, tool_name, result, file_type, agent_reaction, detail)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
                (session_id, task_name, tool_name, result, file_type, agent_reaction, detail),
            )
            conn.commit()
            cur.close()
            self._pool.putconn(conn)
        except Exception as e:
            logger.warning(f"[code_entity_extractor] 插入 agent_actions 失败: {e}")

    def store_step_summary(self, task_name: str, step_number: int, summary_json: dict):
        """存储步骤摘要 JSON 到 steps_summary 表"""
        try:
            conn = self._pool.getconn()
            cur = conn.cursor()
            # 任务3 v7: default=str 处理 PosixPath 等非 JSON 类型(步骤摘要含 Path 对象时序列化失败)
            _summary_str = json.dumps(summary_json, ensure_ascii=False, default=str)
            cur.execute(
                """
                INSERT INTO steps_summary (task_name, step_number, summary_json)
                VALUES (%s, %s, %s)
                ON CONFLICT (task_name, step_number)
                DO UPDATE SET summary_json = EXCLUDED.summary_json
            """,
                (task_name, step_number, _summary_str),
            )
            conn.commit()
            cur.close()
            self._pool.putconn(conn)
        except Exception as e:
            print(f"[store_step_summary] 失败: {e}")

    SAG_CACHE_TTL = 300

    def _get_redis_client(self):
        """获取 Redis 客户端；Redis 不可用时返回 None（fallback 直查 PostgreSQL）"""
        if redis_lib is None:
            return None
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            client = redis_lib.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
            client.ping()
            return client
        except Exception:
            return None

    def query_step_summaries(self, task_name: str) -> list:
        """查询指定 task_name 的所有步骤摘要（含 system_hypothesis 场景）

        缓存策略（SAG Redis 缓存）：
        1. 先查 Redis 缓存，key = sag:step_summaries:{task_name}
        2. 命中直接返回，不访问 PostgreSQL
        3. 未命中则查 PostgreSQL 并写入缓存，TTL 300 秒
        4. Redis 不可用时 fallback 直接查 PostgreSQL
        """
        cache_key = f"sag:step_summaries:{task_name}"

        # 1) 先查 Redis 缓存
        r = self._get_redis_client()
        if r is not None:
            try:
                cached = r.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass  # 缓存读取失败，继续查 PostgreSQL

        # 2) 未命中 → 查 PostgreSQL
        try:
            conn = self._pool.getconn()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
                """
                SELECT step_number, summary_json, created_at
                FROM steps_summary
                WHERE task_name = %s
                ORDER BY step_number ASC
            """,
                (task_name,),
            )
            rows = cur.fetchall()
            cur.close()
            self._pool.putconn(conn)
            result = [dict(r) for r in rows]
        except Exception as e:
            print(f"[query_step_summaries] 失败: {e}")
            return []

        # 3) 写入 Redis 缓存（TTL 300 秒）
        if r is not None:
            try:
                r.setex(cache_key, self.SAG_CACHE_TTL, json.dumps(result, ensure_ascii=False, default=str))
            except Exception:
                pass  # 缓存写入失败不影响结果
        return result

    def query_fulltext_by_keywords(self, keywords: List[str], task_name: str = None) -> List[Dict]:
        """全文检索：steps_summary 全文 + code_entities 中 entity_type='context_summary'，返回带 relevance 的全文结果。

        1. steps_summary：对 summary_json 全文字符串做关键词命中统计，
           relevance = 命中关键词数 / 关键词总数
        2. code_entities：entity_type='context_summary' 的实体，按 entity_name/signature/related_entities
           全文命中统计 relevance
        结果按 relevance 降序返回。
        """
        conn = self._pool.getconn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        results = []
        kw_list = [str(k).strip().lower() for k in (keywords or []) if str(k).strip()]

        def _kw_hits(text: str) -> int:
            if not text:
                return 0
            t = text.lower()
            return sum(1 for k in kw_list if k in t)

        try:
            # 1) steps_summary 全文检索
            if task_name:
                cur.execute(
                    "SELECT * FROM steps_summary WHERE task_name = %s ORDER BY step_number",
                    (task_name,),
                )
            else:
                cur.execute("SELECT * FROM steps_summary ORDER BY step_number")
            for row in cur.fetchall():
                summary = row.get("summary_json", {})
                if isinstance(summary, str):
                    try:
                        summary = json.loads(summary)
                    except Exception:
                        summary = {}
                summary_str = json.dumps(summary, ensure_ascii=False)
                hits = _kw_hits(summary_str)
                if hits > 0:
                    results.append(
                        {
                            "source": "steps_summary",
                            "task_name": row.get("task_name"),
                            "step_number": row.get("step_number"),
                            "summary": summary,
                            "relevance": round(hits / len(kw_list), 4) if kw_list else 1.0,
                        }
                    )

            # 2) code_entities 中 context_summary 全文检索
            cur.execute("SELECT * FROM code_entities WHERE entity_type = 'context_summary' ORDER BY id")
            for e in cur.fetchall():
                text = " ".join(
                    str(x)
                    for x in [
                        e.get("entity_name", ""),
                        e.get("signature", ""),
                        json.dumps(e.get("related_entities", []), ensure_ascii=False),
                    ]
                )
                hits = _kw_hits(text)
                if hits > 0:
                    results.append(
                        {
                            "source": "code_entities",
                            "entity_name": e.get("entity_name"),
                            "entity_type": e.get("entity_type"),
                            "file_path": e.get("file_path"),
                            "signature": e.get("signature", ""),
                            "related_entities": e.get("related_entities", []),
                            "relevance": round(hits / len(kw_list), 4) if kw_list else 1.0,
                        }
                    )
        finally:
            cur.close()
            self._pool.putconn(conn)

        results.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        return results

    def _extract(self, filepath: str, content: str) -> List[Dict]:
        """从文件内容中抽取实体"""
        entities = []
        ext = Path(filepath).suffix

        if ext == ".py":
            entities = self._extract_python(filepath, content)
        elif ext == ".go":
            entities = self._extract_go(filepath, content)
        elif ext in (".tsx", ".ts"):
            entities = self._extract_typescript(filepath, content)

        return entities

    def _extract_python(self, filepath: str, content: str) -> List[Dict]:
        """Python AST 抽取（SAG 大文件拆分索引）"""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []

        # SAG 大文件拆分索引：对 >500 行的 Python 文件按 def/class 拆分为独立实体，
        # 每个函数/类生成独立 entity 记录（含精确签名），
        # 方便 query_index 精确定位到函数级别。
        entities = self._split_large_python(filepath, tree)

        # #212 SAG 变量级索引盲区：模块级赋值语句（ast.Assign 且目标是 Name）也生成 entity，
        # entity_type="variable"，entity_name=变量名，line_number=赋值行号，
        # signature=变量值前100字符，使 query_index 能搜到模块级变量（如 _write_kw、MAX_CONTEXT_TOKENS）。
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        try:
                            value_src = ast.unparse(node.value)
                        except Exception:
                            value_src = ""
                        entities.append(
                            {
                                "type": "variable",
                                "name": target.id,
                                "file": filepath,
                                "line": node.lineno,
                                "signature": value_src[:100],
                                "related": [],
                            }
                        )
        return entities

    def _split_large_python(self, filepath: str, tree: ast.AST) -> List[Dict]:
        """SAG 大文件拆分索引：按 def/class 拆分为独立实体。

        遍历 AST 中所有函数/类（含嵌套 def / async def / class），
        每个生成独立 entity 记录，签名通过 ast.unparse 精确还原参数与基类，
        便于 query_index 精确定位到函数级别。
        """
        entities = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                related = self._find_calls(node)
                entities.append(
                    {
                        "type": "function",
                        "name": node.name,
                        "file": filepath,
                        "line": node.lineno,
                        "signature": f"def {self._py_signature(node)}",
                        "related": related,
                    }
                )
            elif isinstance(node, ast.ClassDef):
                entities.append(
                    {
                        "type": "type",
                        "name": node.name,
                        "file": filepath,
                        "line": node.lineno,
                        "signature": f"class {self._py_signature(node)}",
                        "related": [],
                    }
                )
        return entities

    def _py_signature(self, node) -> str:
        """生成精确的函数/类签名（含参数与基类）"""
        try:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return f"{node.name}({ast.unparse(node.args)})"
            if isinstance(node, ast.ClassDef):
                bases = ", ".join(ast.unparse(b) for b in node.bases)
                return f"{node.name}({bases})" if bases else node.name
        except Exception:
            pass
        return node.name

    def _find_calls(self, func_node: ast.FunctionDef) -> List[str]:
        """找出函数内调用的其他函数/类"""
        calls = set()
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        return list(calls)[:10]

    def _extract_imports(self, content: str) -> List[str]:
        """提取文件导入依赖（imports）：import X.Y → X；from X import Y → X"""
        mods = []
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return mods
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mods.append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    mods.append(node.module.split(".")[0])
        # 去重，最多保留 30 个
        return list(dict.fromkeys(mods))[:30]

    def _extract_import_paths(self, content: str) -> List[str]:
        """提取完整导入路径（含包路径）：import a.b.c → a.b.c；from x.y import z → x.y"""
        mods = []
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return mods
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mods.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    mods.append(node.module)
        return list(dict.fromkeys(mods))[:30]

    def _extract_go(self, filepath: str, content: str) -> List[Dict]:
        """Go 正则抽取"""
        entities = []
        for m in re.finditer(r"func\s+(?:\(.*?\)\s+)?(\w+)\((.*?)\)", content):
            entities.append(
                {
                    "type": "function",
                    "name": m.group(1),
                    "file": filepath,
                    "line": content[: m.start()].count("\n") + 1,
                    "signature": m.group(0).strip(),
                    "related": re.findall(r"(\w+)\.", m.group(2)),
                }
            )
        for m in re.finditer(r"type\s+(\w+)\s+struct", content):
            entities.append(
                {
                    "type": "type",
                    "name": m.group(1),
                    "file": filepath,
                    "line": content[: m.start()].count("\n") + 1,
                    "signature": m.group(0).strip(),
                    "related": [],
                }
            )
        return entities

    def _extract_typescript(self, filepath: str, content: str) -> List[Dict]:
        """TypeScript/TSX 正则抽取"""
        entities = []
        for m in re.finditer(r"(?:export\s+)?(?:const|function)\s+(\w+)", content):
            entities.append(
                {
                    "type": "function",
                    "name": m.group(1),
                    "file": filepath,
                    "line": content[: m.start()].count("\n") + 1,
                    "signature": m.group(0).strip(),
                    "related": [],
                }
            )
        for m in re.finditer(r"(?:export\s+)?interface\s+(\w+)", content):
            entities.append(
                {
                    "type": "type",
                    "name": m.group(1),
                    "file": filepath,
                    "line": content[: m.start()].count("\n") + 1,
                    "signature": m.group(0).strip(),
                    "related": [],
                }
            )
        return entities


class CodeEntitySearcher:
    """查询时动态超边检索"""

    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv("DATABASE_URL")  # 移除硬编码默认凭据，必须从环境变量读取
        if not self.db_url:
            raise ValueError("DATABASE_URL 未配置，必须通过环境变量设置数据库连接串")
        self._pool = ConnectionPool(self.db_url)
        self._init_table()

    def _init_table(self):
        try:
            conn = self._pool.getconn()
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS code_entities (
                    id SERIAL PRIMARY KEY,
                    project_id TEXT DEFAULT 'default',
                    entity_type TEXT NOT NULL,
                    entity_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    line_number INT,
                    signature TEXT,
                    related_entities TEXT[],
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(project_id, entity_name, file_path)
                )
            """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_actions (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    task_name TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    result TEXT NOT NULL,
                    file_type TEXT DEFAULT 'unknown',
                    agent_reaction TEXT DEFAULT '',
                    detail TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS task_progress (
                    id SERIAL PRIMARY KEY,
                    task_name TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    step_number INT NOT NULL,
                    step_description TEXT,
                    tool_name TEXT,
                    file_path TEXT,
                    status TEXT DEFAULT 'pending',
                    snapshot_path TEXT,
                    error_message TEXT,
                    started_at TIMESTAMP DEFAULT NOW(),
                    completed_at TIMESTAMP,
                    UNIQUE(task_name, step_number)
                )
            """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS steps_summary (
                    id SERIAL PRIMARY KEY,
                    task_name TEXT NOT NULL,
                    step_number INT NOT NULL,
                    summary_json JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(task_name, step_number)
                )
            """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS injection_feedback (
                    id SERIAL PRIMARY KEY,
                    task_name TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    edge_id INT,
                    source_name TEXT,
                    target_name TEXT,
                    edge_type TEXT,
                    feedback_type TEXT NOT NULL,
                    feedback_value REAL,
                    context TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """
            )
            cur.execute(
                """
                DO $$
                BEGIN
                    CREATE ROLE clawsjoy_readonly LOGIN PASSWORD 'clawsjoy_readonly_secret';
                EXCEPTION WHEN duplicate_object THEN
                    RAISE NOTICE 'clawsjoy_readonly role already exists';
                END
                $$;
            """
            )
            cur.execute("GRANT CONNECT ON DATABASE clawsjoy_dev TO clawsjoy_readonly")
            cur.execute("GRANT USAGE ON SCHEMA public TO clawsjoy_readonly")
            cur.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO clawsjoy_readonly")
            conn.commit()
            cur.close()
            self._pool.putconn(conn)
        except Exception:
            pass

    def search_with_hyperedges(self, query: str, project_id: str = "default", limit: int = 10) -> Dict:
        """查询实体 + 动态超边扩展（支持中文关键词匹配）"""
        conn = self._pool.getconn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 中文增强：生成匹配词组（整句 + 中文段 + 二元组），提升中文召回
        _terms = _chinese_query_terms(query)

        # Step 1: 找主实体（entity_name / signature 模糊匹配，任一中文词组命中即可）
        primary = None
        for term in _terms:
            cur.execute(
                """
                SELECT * FROM code_entities
                WHERE project_id = %s
                  AND entity_type NOT IN ('tool_flow', 'audit_event')
                  AND (entity_name ILIKE %s OR signature ILIKE %s)
                LIMIT 1
            """,
                (project_id, f"%{term}%", f"%{term}%"),
            )
            _cand = cur.fetchone()
            if _cand is None:
                continue
            # 检索精度闸（老板 2026-10-03 裁 · 词边界）：SQL 是 ILIKE **模糊**匹配，
            # 命中须再过一道词边界复验 —— 否则 "no" 会命中 "nonexistent"。
            if boundary_hit(term, _cand.get("entity_name")) or boundary_hit(term, _cand.get("signature")):
                primary = _cand
                break

        if not primary:
            cur.close()
            self._pool.putconn(conn)
            return {"primary": None, "related": []}

        # Step 2: 动态超边 — 沿 related_entities 扩展
        cur.execute(
            """
            SELECT DISTINCT e.* FROM code_entities e
            WHERE e.project_id = %s
            AND e.entity_name = ANY(
                SELECT unnest(related_entities) FROM code_entities WHERE id = %s
            )
            LIMIT %s
            """,
            (project_id, primary["id"], limit),
        )
        related = cur.fetchall()

        # Step 3: 反向关联 — 谁引用了主实体
        cur.execute(
            """
            SELECT * FROM code_entities
            WHERE project_id = %s
            AND %s = ANY(related_entities)
            LIMIT %s
            """,
            (project_id, primary["entity_name"], limit),
        )
        referers = cur.fetchall()

        cur.close()
        self._pool.putconn(conn)

        # 统一路径格式：返回给 Agent 前 file_path 统一走 _format_path_for_agent
        def _fmt(row):
            if not row:
                return row
            row = dict(row)
            if row.get("file_path"):
                row["file_path"] = _format_path_for_agent(str(row["file_path"]))
            return row

        # 相关性评分：关键词命中数 / 总关键词数
        def _term_hit(term, row):
            name = str(row.get("entity_name") or "")
            sig = str(row.get("signature") or "")
            return term in name or term in sig

        total_keywords = max(len(_terms), 1)
        hit_terms = [t for t in _terms if primary and _term_hit(t, primary)]
        relevance_score = round(len(hit_terms) / total_keywords, 2) if primary else 0.0

        if hit_terms:
            match_type = "keyword"  # 主实体命中
        elif related or referers:
            match_type = "graph"  # 超边扩展
        else:
            match_type = "semantic"  # 无关键词命中兜底

        # match_context：按 entity_type 归类 function/class/task/bug/hypothesis
        def _entity_type_bucket(etype):
            etype = str(etype or "unknown").lower()
            for bucket in ("function", "class", "task", "bug", "hypothesis"):
                if bucket in etype:
                    return bucket
            return "other"

        match_context = {}
        for row in filter(None, [primary] + list(related) + list(referers)):
            bucket = _entity_type_bucket(row.get("entity_type"))
            match_context.setdefault(bucket, []).append(row.get("entity_name"))

        return {
            "primary": _fmt(primary) if primary else None,
            "related": [_fmt(r) for r in related],
            "referers": [_fmt(r) for r in referers],
            "relevance_score": relevance_score,
            "match_type": match_type,
            "match_context": match_context,
        }

    def query_context_by_keywords(self, keywords: List[str], task_name: str = None) -> List[Dict]:
        """在 steps_summary 和 code_entities 中按关键词模糊匹配，返回上下文摘要列表"""
        # 关键词闸（老板 2026-10-03 裁）：空/坏关键词（""／None）⇒ 早退 · ⛔ 查库
        # 由：`ILIKE '%%'` 命中全表 ⇒ 空关键词 ＝ 面作废（与「反例空」同族），且它是静默的。
        _raw_kw = list(keywords) if keywords else []
        _valid_kw = [k for k in _raw_kw if isinstance(k, str) and k.strip()]
        if len(_valid_kw) != len(_raw_kw):
            logger.warning(
                "[code_entity_extractor] 关键词闸：丢弃 %d 个空/坏关键词（⛔ 未查库 —— ILIKE '%%' 会命中全表）",
                len(_raw_kw) - len(_valid_kw),
            )
        if not _valid_kw:
            return []
        keywords = _valid_kw
        conn = self._pool.getconn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        results = []

        try:
            # 查询 steps_summary 表
            if task_name:
                cur.execute(
                    """
                    SELECT * FROM steps_summary
                    WHERE task_name = %s
                    ORDER BY step_number
                """,
                    (task_name,),
                )
                rows = cur.fetchall()
                for row in rows:
                    summary = row.get("summary_json", {})
                    if isinstance(summary, str):
                        try:
                            summary = json.loads(summary)
                        except Exception:
                            summary = {}
                    summary_str = json.dumps(summary, ensure_ascii=False)
                    if any(kw.lower() in summary_str.lower() for kw in keywords):
                        results.append(
                            {
                                "source": "steps_summary",
                                "task_name": row["task_name"],
                                "step_number": row["step_number"],
                                "summary": summary,
                                "relevance": 1.0,
                            }
                        )

            # 查询 code_entities 表
            for kw in keywords:
                cur.execute(
                    """
                    SELECT * FROM code_entities
                    WHERE project_id = %s
                      AND entity_type NOT IN ('tool_flow', 'audit_event')
                      AND (entity_name ILIKE %s OR signature ILIKE %s)
                    LIMIT 20
                """,
                    (SEARCH_DOMAIN_PROJECT_ID, f"%{kw}%", f"%{kw}%"),
                )
                entities = cur.fetchall()
                for e in entities:
                    results.append(
                        {
                            "source": "code_entities",
                            "entity_name": e["entity_name"],
                            "entity_type": e["entity_type"],
                            "file_path": e["file_path"],
                            "signature": e.get("signature", ""),
                            "related_entities": e.get("related_entities", []),
                            "relevance": 0.8,
                        }
                    )

            # 域闸自检（域 ＝ default）：被滤掉之「非 default 域」件数 > 0 ⇒ 喊一行（⛔ 静默丢）
            _kw_pats = [f"%{str(k)}%" for k in keywords if k]
            if _kw_pats:
                try:
                    cur.execute(
                        """
                        SELECT count(*) AS n FROM code_entities
                        WHERE project_id <> %s
                          AND entity_type NOT IN ('tool_flow', 'audit_event')
                          AND (entity_name ILIKE ANY(%s::text[]) OR signature ILIKE ANY(%s::text[]))
                    """,
                        (SEARCH_DOMAIN_PROJECT_ID, _kw_pats, _kw_pats),
                    )
                    _dropped = cur.fetchone()["n"]
                    if _dropped:
                        logger.warning(
                            "[code_entity_extractor] 域闸 project_id=%s：本次检索滤掉 %d 件非本域之件 ⇒ 若须跨域，须先定语义",
                            SEARCH_DOMAIN_PROJECT_ID, _dropped,
                        )
                except Exception as _e:
                    logger.warning("[code_entity_extractor] 域闸自检失败（⛔ 不动检索结果）: %s", _e)
        finally:
            cur.close()
            self._pool.putconn(conn)

        # 按匹配度排序
        results.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        return results

    def traverse_edges(self, entity_name: str, depth: int = 2, project_id: str = "default") -> List[Dict]:
        """沿 code_edges 图遍历，从 entity_name 出发遍历 depth 层，返回关联实体签名。

        带权排序：优先返回高权重边关联的实体
        多样化去重：相同文件只保留最相关的实体
        """
        visited = set()
        results = []
        # queue: (entity_name, depth, accumulated_weight)
        queue = [(entity_name, 0, 1.0)]
        visited.add(entity_name)

        conn = self._pool.getconn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        try:
            while queue:
                # 弹出队列中累计权重最高的节点（带权优先）
                queue.sort(key=lambda x: -x[2])
                current, current_depth, acc_weight = queue.pop(0)
                if current_depth > depth:
                    break

                # 获取当前实体的签名（排除起始实体本身）
                if current != entity_name:
                    cur.execute(
                        "SELECT entity_name, entity_type, signature, file_path FROM code_entities "
                        "WHERE entity_name = %s AND project_id = %s LIMIT 1",
                        (current, project_id),
                    )
                    entity = cur.fetchone()
                    if entity:
                        results.append(dict(entity))

                if current_depth < depth:
                    # 查询从 current 出发的边 (source -> target)，带 weight
                    cur.execute(
                        "SELECT target_name, weight FROM code_edges WHERE source_name = %s AND project_id = %s",
                        (current, project_id),
                    )
                    for row in cur.fetchall():
                        target = row["target_name"]
                        edge_weight = row.get("weight", 1.0) or 1.0
                        if target not in visited:
                            visited.add(target)
                            queue.append((target, current_depth + 1, acc_weight * edge_weight))

                    # 查询指向 current 的边 (target <- source)，带 weight
                    cur.execute(
                        "SELECT source_name, weight FROM code_edges WHERE target_name = %s AND project_id = %s",
                        (current, project_id),
                    )
                    for row in cur.fetchall():
                        source = row["source_name"]
                        edge_weight = row.get("weight", 1.0) or 1.0
                        if source not in visited:
                            visited.add(source)
                            queue.append((source, current_depth + 1, acc_weight * edge_weight))
        finally:
            cur.close()
            self._pool.putconn(conn)

        # 多样化去重：相同文件只保留权重最高的实体
        seen_files = {}
        deduped = []
        for r in results:
            fp = r.get("file_path", "")
            if fp not in seen_files:
                seen_files[fp] = r
                deduped.append(r)
            else:
                # 按权重降序排列，如果有更高权重的已经在列表中，跳过
                pass

        return deduped


# 全局实例 — P0: shim 代理, 延迟解析到 V9Context 容器(测试可 provide_override 替换, 无需 monkeypatch sys.modules)
class _ExtractorProxy:
    """属性转发到容器内 extractor。业务代码 import extractor 零改动。"""

    def __getattr__(self, name):
        return getattr(_get_extractor(), name)

    def __dir__(self):
        return dir(_get_extractor())

    def __repr__(self):
        return repr(_get_extractor())


def _get_extractor():
    """从容器取 extractor; 未注册时惰性构造并注册(兼容 import 即用)。"""
    from core.os.context import get_v9_context as _get_ctx

    _ctx = _get_ctx()
    _ext = _ctx.get_opt("extractor")
    if _ext is not None:
        return _ext
    if not _DB_BREAKER.allow():
        raise DbUnavailable(
            "DB 不可达，断路器打开中（已压制 %d 条，窗内不建连）" % _DB_BREAKER.skipped_downgraded
        )
    try:
        _ext = CodeEntityExtractor()
    except Exception as e:
        _DB_BREAKER.fail(e)
        raise
    _DB_BREAKER.ok()
    _ctx.provide("extractor", _ext)
    return _ext


extractor = _ExtractorProxy()


# searcher 同模式惰性化(消除模块 import 时的 DB 依赖, 与 extractor 对齐)
class _SearcherProxy:
    """属性转发到容器内 searcher。业务代码 import searcher 零改动。"""

    def __getattr__(self, name):
        return getattr(_get_searcher(), name)

    def __dir__(self):
        return dir(_get_searcher())

    def __repr__(self):
        return repr(_get_searcher())


def _get_searcher():
    """从容器取 searcher; 未注册时惰性构造并注册。"""
    from core.os.context import get_v9_context as _get_ctx

    _ctx = _get_ctx()
    _sr = _ctx.get_opt("searcher")
    if _sr is None:
        _sr = CodeEntitySearcher()
        _ctx.provide("searcher", _sr)
    return _sr


searcher = _SearcherProxy()


class TaskStateMachine:
    """任务状态机：协调 agent_actions 和 task_progress 的写入"""

    def __init__(self, task_name, session_id, extractor):
        self.task_name = task_name
        self.session_id = session_id
        self.extractor = extractor
        self.current_step = 1

    def record_step(self, tool_name, file_path, status, error=None):
        """记录一步操作，同时写入 agent_actions 和 task_progress"""
        capability_chain = self._resolve_capability_chain()
        self.extractor.insert_agent_action(
            session_id=self.session_id,
            task_name=self.task_name,
            tool_name=tool_name,
            result=status,
            file_type="unknown",
            agent_reaction="",
            detail=error or "",
            capability_chain=capability_chain,
        )
        self.extractor.update_task_progress(
            task_name=self.task_name,
            session_id=self.session_id,
            step_number=self.current_step,
            step_description=f"调用 {tool_name}",
            tool_name=tool_name,
            file_path=file_path,
            status=status,
            error_message=error or "",
        )
        if status == "completed":
            self.current_step += 1
        elif status == "failed":
            self._check_rollback()

    def _resolve_capability_chain(self):
        """查询任务关联的能力链"""
        try:
            import psycopg2

            conn = psycopg2.connect(self.extractor.db_url)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT array_agg(DISTINCT entity_name) as chain
                FROM code_entities
                WHERE entity_name = %s
                   OR entity_name = ANY(
                       SELECT unnest(related_entities) FROM code_entities WHERE entity_name = %s
                   )
            """,
                (self.task_name, self.task_name),
            )
            row = cur.fetchone()
            cur.close()
            conn.close()
            return list(row[0]) if row and row[0] else []
        except Exception:
            return []

    def _check_rollback(self):
        """检查是否需要回退：恢复文件快照 + 标记 rolled_back"""
        try:
            import psycopg2

            conn = psycopg2.connect(self.extractor.db_url)
            cur = conn.cursor()
            cur.execute(
                "SELECT status, snapshot_path, file_path FROM task_progress WHERE task_name=%s AND step_number=%s",
                (self.task_name, self.current_step - 1),
            )
            row = cur.fetchone()
            if row and row[0] == "completed" and row[1]:
                # 从快照恢复文件
                import shutil

                snapshot = Path(row[1])
                target = Path(row[2]) if row[2] else None
                if snapshot.exists() and target:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(snapshot, target)
                # 标记回退
                self.extractor.update_task_progress(
                    task_name=self.task_name,
                    session_id=self.session_id,
                    step_number=self.current_step - 1,
                    status="rolled_back",
                    error_message=f"步骤 {self.current_step} 失败，已恢复到步骤 {self.current_step - 1} 的文件状态",
                )
            cur.close()
            conn.close()
        except Exception:
            pass

    def create_snapshot(self, file_path):
        """创建文件快照，返回快照路径"""
        import shutil
        from pathlib import Path as _P

        _fp = _P(file_path)
        if not _fp.exists():
            return None
        _snap_dir = _P(f"data/projects/{self.session_id}/snapshots/{self.task_name}")
        _snap_dir.mkdir(parents=True, exist_ok=True)
        _snap_path = _snap_dir / f"step_{self.current_step}_{_fp.name}"
        shutil.copy(_fp, _snap_path)
        return str(_snap_path)
