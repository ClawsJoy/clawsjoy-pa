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


@skill_bp.route("/api/skills/execute", methods=["POST"])
def execute_skill():
    """执行指定技能"""
    from core.lib.skill_loader_v3 import skill_loader
    data = request.json or {}
    result = skill_loader.execute(data.get("skill", ""), data.get("params", {}))
    return jsonify({"success": True, "result": result})
