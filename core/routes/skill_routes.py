"""
技能管理路由（独立 Blueprint）
==============================
将 agent_gateway_enhanced.py 中的 /api/skills/ 系列路由提取到独立 Blueprint。

依赖（unified_skill_manager / skill_loader_v3）通过路由函数内惰性导入获取，
避免导入阶段产生循环依赖或加载开销。路由路径保持 /api/skills/ 不变，
确保对外 API 兼容。

路由:
- GET  /api/skills/list     列出所有可用技能
- POST /api/skills/execute  执行指定技能
"""

from flask import Blueprint, jsonify, request

skill_bp = Blueprint("skill", __name__)


@skill_bp.route("/api/skills/list", methods=["GET"])
def list_skills():
    """列出所有可用技能"""
    from core.lib.unified_skill_manager import unified_manager
    skills = unified_manager.list_all()
    return jsonify({"success": True, "skills": skills, "total": len(skills)})


# ⭐ 2026-10-04 修（PM b136893 授权 · 见信通 825/826）：
#   病：原 `from core.lib.skill_loader_v3 import skill_loader` 取到的是**占位 None**
#       （core\lib\skill_loader_v3.py:295 `skill_loader = None`）⇒ 恒 AttributeError
#       ⇒ 实测 POST /api/skills/execute 对 4 载荷 × 4 技能 = 16/16 皆 HTTP 500。
#   修：改取**工厂** `get_skill_loader()`（＝ /api/skills/list 之 unified_manager 同一真源
#       ⇒ 两值同源 · 承 L83 单源）；且**不可执行者回 JSON（⛔ 500）**，免"列表说有、执行就崩"。
@skill_bp.route("/api/skills/execute", methods=["POST"])
def execute_skill():
    """执行指定技能（不可执行 ⇒ success:false ＋ error，⛔ 500）"""
    from core.lib.skill_loader_v3 import get_skill_loader

    data = request.json or {}
    name = data.get("skill", "")
    params = data.get("params", {}) or {}
    try:
        loader = get_skill_loader()
        skill = loader.get_skill(name)
    except Exception as e:  # 取器失败亦回 JSON
        return jsonify({"success": False, "error": "取技能器失败: %s" % str(e)[:160]})
    if skill is None:
        return jsonify({"success": False, "error": "技能不存在: %s" % name})
    if not hasattr(skill, "execute"):
        return jsonify({"success": False, "error": "技能不可执行（注册表项无 execute）: %s" % name})
    try:
        return jsonify({"success": True, "result": skill.execute(params)})
    except Exception as e:
        return jsonify({"success": False, "error": "执行失败: %s" % str(e)[:160]})


# ⭐ 新增（2026-10-04 · PM 授权）：本机**精确计算**出口 —— 供 PA「精确计算走工具」一格。
#   真源：core.lib.safe_calculator.SafeCalculator（AST 白名单 · 字符白名单 · ⛔ eval）
#   入：{"expr": "200*1.1*0.9"}   出：{"ok": true, "expr": "...", "value": 198.0}
#   纯函数：⛔ DB ／ ⛔ 子进程 ／ ⛔ 网络 ／ ⛔ 落盘 ⇒ 可被对话面安全调用。
@skill_bp.route("/api/tools/calc", methods=["POST"])
def calc_tool():
    """本机安全算器（AST 白名单）· 入 {expr} ⇒ 出 {ok, value}"""
    from core.lib.safe_calculator import SafeCalculator

    data = request.json or {}
    expr = str(data.get("expr", "") or "").strip()
    if not expr:
        return jsonify({"ok": False, "error": "缺 expr"})
    if len(expr) > 200:
        return jsonify({"ok": False, "expr": expr[:200], "error": "表达式过长"})
    try:
        return jsonify({"ok": True, "expr": expr, "value": SafeCalculator.calculate(expr)})
    except Exception as e:
        return jsonify({"ok": False, "expr": expr, "error": str(e)[:200]})
