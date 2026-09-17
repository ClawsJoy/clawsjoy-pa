#!/usr/bin/env python3
"""Route Handlers - Route Handlers 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)
from core.lib.marketplace_data import marketplace_data
from core.lib.unified_config import unified_config

"""路由处理器注册中心 - ClawsJoy 配置驱动"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from flask import jsonify, request, send_from_directory

from core.lib.agent_communication import agent_comm
from core.lib.agent_registry import agent_registry
from core.lib.log_aggregator import log_aggregator
from core.lib.unified_skill_manager import unified_manager as skill_loader

# 处理器注册表
HANDLERS = {}


def register(name):
    def decorator(func):
        HANDLERS[name] = func
        return func

    return decorator


# ========== Web 路由 ==========
@register("web_index")
def web_index():
    return send_from_directory("../renderer", "index_root.html")


@register("web_static")
def web_static(filename):
    return send_from_directory("../renderer", filename)


# ========== 系统路由 ==========
@register("health")
def health():
    return jsonify({"service": "gateway", "status": "ok", "version": "4.0.0"})


# ========== 技能路由 ==========
@register("list_skills")
def list_skills():
    try:
        from core.lib.unified_skill_manager import unified_manager

        skills = unified_manager.list_all()
        return jsonify({"skills": skills, "total": len(skills)})
    except Exception as e:
        return jsonify({"skills": [], "total": 0, "error": str(e)})


@register("execute_skill_enhanced")
def execute_skill_enhanced():
    """增强版技能执行 - 支持自然语言"""
    import re

    from core.lib.skill_executor import skill_executor

    data = request.get_json() or {}
    skill = data.get("skill", "")
    params = data.get("params", {})

    # 自然语言识别
    text = params.get("text", "")
    if not skill and text:
        if "+" in text or "加" in text or "计算" in text:
            skill = "calculator"
            numbers = re.findall(r"\d+", text)
            if numbers:
                params["expression"] = "+".join(numbers)
        elif "天气" in text:
            skill = "weather"
            import re

            city_match = re.search(r"([一-龥]+)(?:天气|市)", text)
            if city_match:
                params["city"] = city_match.group(1)
        elif "翻译" in text:
            skill = "translate"

    result = skill_executor.execute(skill, params)
    return jsonify({"success": True, "result": result, "skill": skill})


@register("execute_skill")
def execute_skill():
    """执行技能"""
    from core.lib.skill_executor import skill_executor

    data = request.get_json() or {}
    skill = data.get("skill", "")
    params = data.get("params", {})

    if not skill:
        # 尝试从参数中识别
        text = params.get("text", "")
        if "+" in text or "计算" in text:
            skill = "calculator"
        elif "天气" in text:
            skill = "weather"
        elif "翻译" in text:
            skill = "translate"
        else:
            return jsonify({"success": False, "error": "请指定技能名称"}), 400

    result = skill_executor.execute(skill, params)
    return jsonify(result)


# do_anything skill 已删除(bff9ce70)，路由移除（残留函数体已清理，避免吸入前一个函数）
@register("skill_search")
def skill_search():
    # 支持 GET 和 POST
    if request.method == "POST":
        data = request.get_json() or {}
        keyword = data.get("query", data.get("q", ""))
    else:
        keyword = request.args.get("q", "")

    if not keyword:
        return jsonify({"error": "query required", "success": False}), 400

    skills = skill_loader.search_skills(keyword)
    return jsonify({"skills": skills, "total": len(skills), "success": True})


# ========== Agent 路由 ==========
@register("list_agents")
def list_agents():
    agents = agent_registry.list_all()
    return jsonify({"agents": agents, "total": len(agents)})


@register("agents_health")
def agents_health():
    return jsonify({})


@register("agents_info")
def agents_info():
    return jsonify({"info": "agent info"})


@register("get_agent_messages")
def get_agent_messages():
    return jsonify({"messages": []})


@register("send_agent_message")
def send_agent_message():
    return jsonify({"success": True})


@register("broadcast_message")
def broadcast_message():
    """广播消息到所有订阅的 Agent"""
    from flask import jsonify, request

    from core.lib.agent_bus import get_bus

    data = request.get_json() or {}
    topic = data.get("topic", "")
    message = data.get("message", {})
    sender = data.get("sender", "system")

    if not topic:
        return jsonify({"success": False, "error": "topic required"}), 400

    bus = get_bus()
    message_id = bus.publish(sender, topic, message)

    return jsonify({"success": True, "message_id": message_id, "topic": topic, "broadcast": True})


@register("subscribe_agent")
def subscribe_agent():
    """Agent 订阅主题"""
    from flask import jsonify, request

    from core.lib.agent_bus import get_bus

    data = request.get_json() or {}
    agent_name = data.get("agent_name", "")
    topic = data.get("topic", "")

    if not agent_name or not topic:
        return (
            jsonify({"success": False, "error": "agent_name and topic required"}),
            400,
        )

    bus = get_bus()
    bus.subscribe(agent_name, topic)

    return jsonify(
        {
            "success": True,
            "agent_name": agent_name,
            "topic": topic,
            "message": f"{agent_name} 已订阅 {topic}",
        }
    )


# ========== 聊天路由 ==========
@register("chat")
def chat():
    from flask import g

    from agents.chat_agent.agent import chat_agent
    from core.agents.builtin.personal_butler_v2 import PersonalButlerV2

    data = request.get_json()
    # user_id = data.get('user_id', 'default')
    message = data.get("message", "")
    user_role = data.get("user_role", "guest")
    session_id = data.get("session_id", None)

    if not message:
        return jsonify({"error": "消息为空", "success": False}), 400

    if user_role == "guest":
        result = chat_agent.process(message, session_id)
    else:
        try:
            request_user_id = data.get("user_id", g.user_id)
            butler = PersonalButlerV2(user_id=request_user_id)  # ✅ 使用正确的变量名
            result = butler.process(message)
        except Exception as e:
            import traceback

            print("=" * 50)
            print("❌ PersonalButlerV2 处理失败:")
            traceback.print_exc()
            print("=" * 50)
            return (
                jsonify(
                    {
                        "response": f"处理失败: {str(e)}",
                        "success": False,
                        "error": str(e),
                    }
                ),
                500,
            )

    return jsonify(
        {
            "response": result.get("response", ""),
            "success": result.get("success", True),
            "session_id": result.get("session_id"),
        }
    )


# ========== 日志路由 ==========
@register("get_logs")
def get_logs():
    service = request.args.get("service")
    lines = int(request.args.get("lines", 50))
    logs = log_aggregator.get_logs(service, lines)
    return jsonify({"logs": logs})


@register("search_logs")
def search_logs():
    keyword = request.args.get("q", "")
    service = request.args.get("service")
    lines = int(request.args.get("lines", 20))
    results = log_aggregator.search_logs(keyword, service, lines)
    return jsonify({"results": results})


@register("get_errors")
def get_errors():
    service = request.args.get("service")
    lines = int(request.args.get("lines", 50))
    errors = log_aggregator.get_errors(service, lines)
    return jsonify({"errors": errors})


# ========== 服务路由 ==========
@register("list_services")
def list_services():
    return jsonify({"services": []})


@register("metrics")
def metrics():
    return jsonify({"metrics": {}})


# ========== Agent 消息 API ==========
@register("agent_message")
def agent_message(agent_name):
    """向指定 Agent 发送消息 - 统一版本，支持动态加载"""
    import importlib

    from flask import g, jsonify, request

    from core.agents.builtin.agent_manager import agent_manager

    data = request.get_json() or {}
    message = data.get("message", "")
    user_id = data.get("user_id", g.get("user_id", "default"))

    if not message:
        return jsonify({"success": False, "error": "message required"}), 400

    # 优先从 agent_manager 获取 Agent 配置
    agent_config = agent_manager.get_agent(agent_name)

    if agent_config:
        module_name = agent_config.get("module")
        class_name = agent_config.get("class")
        if module_name and class_name:
            try:
                module = importlib.import_module(module_name)
                agent_class = getattr(module, class_name)
                agent = agent_class(user_id=user_id)
                result = agent.process(message)
                # 获取响应内容，优先 response，其次 result
                response_text = result.get("response", "")
                if not response_text and "result" in result:
                    response_text = str(result["result"])

                return jsonify(
                    {
                        "success": result.get("success", True),
                        "response": response_text,
                        "user_id": user_id,
                        "agent": agent_name,
                    }
                )
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

    # 降级：尝试直接导入 core.agents.builtin.{agent_name}
    try:
        module = importlib.import_module(f"core.agents.builtin.{agent_name}")
        # 查找 Agent 类
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if hasattr(attr, "__bases__") and agent_name.capitalize() in attr_name:
                agent = attr(user_id=user_id)
                result = agent.process(message)
                return jsonify(
                    {
                        "success": result.get("success", True),
                        "response": result.get("response", ""),
                        "user_id": user_id,
                        "agent": agent_name,
                    }
                )
    except Exception as e:
        pass

    return jsonify({"success": False, "error": f"Agent {agent_name} not found"}), 404


# ========== 认证路由 ==========
@register("auth_register")
def auth_register():
    """用户注册"""
    from flask import jsonify, request

    from core.lib.auth_api import auth_manager

    data = request.get_json() or {}
    result = auth_manager.register(
        username=data.get("username", ""),
        password=data.get("password", ""),
        role=data.get("role", "user"),
    )
    return jsonify(result)


@register("auth_login")
def auth_login():
    """用户登录"""
    from flask import jsonify, request

    from core.lib.auth_api import auth_manager

    data = request.get_json() or {}
    result = auth_manager.login(username=data.get("username", ""), password=data.get("password", ""))
    return jsonify(result)


@register("auth_verify")
def auth_verify():
    """验证 Token"""
    from flask import jsonify, request

    from core.lib.auth_api import auth_manager

    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")

    if not token:
        return jsonify({"success": False, "error": "Token required"}), 401

    payload = auth_manager.verify_token(token)
    if payload:
        return jsonify({"success": True, "payload": payload})

    return jsonify({"success": False, "error": "Invalid token"}), 401


# ========== 技能推荐 ==========
@register("recommend_skills")
def recommend_skills():
    """基于语义的技能推荐"""
    from api.skill_market import skill_recommender
    from flask import jsonify, request

    data = request.get_json() or {}
    query = data.get("query", "")
    category = data.get("category")
    n = data.get("n", 5)

    if not query:
        return jsonify({"success": False, "error": "query required"}), 400

    results = skill_recommender.recommend(query, n, category)
    return jsonify({"success": True, "recommendations": results})


# ========== 热重载路由 ==========
@register("hot_reload_routes")
def hot_reload_routes():
    """热重载路由配置"""
    from flask import jsonify

    from core.lib.config_auto_watcher import config_auto_watcher
    from core.lib.route_registry import route_registry

    # 重新加载路由
    route_registry.reload()

    # 触发配置重载
    config_auto_watcher.start()

    return jsonify(
        {
            "success": True,
            "message": "路由配置已热重载",
            "routes_count": len(route_registry._routes),
        }
    )


@register("hot_reload_config")
def hot_reload_config():
    """热重载配置文件"""
    from flask import jsonify

    from core.lib.config_auto_watcher import config_auto_watcher

    config_auto_watcher.start()

    return jsonify({"success": True, "message": "配置已重新加载"})


# ========== 管理员路由 ==========
@register("admin_list_agents")
def admin_list_agents():
    """管理员 - 列出所有 Agent"""
    from flask import jsonify

    from core.agents.builtin.agent_manager import agent_manager

    agents = agent_manager.list_agents()
    agents_info = {}
    for aid in agents:
        info = agent_manager.get_agent(aid)
        if info:
            agents_info[aid] = {
                "name": info.get("name", aid),
                "type": info.get("type", "unknown"),
                "enabled": info.get("enabled", True),
                "capabilities": info.get("capabilities", []),
            }

    return jsonify({"success": True, "agents": agents_info, "total": len(agents_info)})


@register("admin_toggle_agent")
def admin_toggle_agent():
    """管理员 - 启用/禁用 Agent"""
    from flask import jsonify, request

    from core.agents.builtin.agent_manager import agent_manager
    from core.lib.agent_registry import agent_registry

    data = request.get_json() or {}
    agent_id = data.get("agent_id", "")
    enabled = data.get("enabled", True)

    if not agent_id:
        return jsonify({"success": False, "error": "agent_id required"}), 400

    # 更新 agent_manager
    if agent_id in agent_manager.agents:
        agent_manager.agents[agent_id]["enabled"] = enabled
        agent_manager._save()

    # 更新 agent_registry
    agent_info = agent_registry.get(agent_id)
    if agent_info:
        agent_info["status"] = "active" if enabled else "inactive"
        agent_registry._save()

    return jsonify(
        {
            "success": True,
            "message": f"Agent {agent_id} 已{'启用' if enabled else '禁用'}",
        }
    )


def admin_delete_agent():
    """管理员 - 删除 Agent（占位）"""
    from flask import jsonify

    return jsonify({"success": True, "message": "删除 Agent 功能开发中"})


# ========== 市场路由 ==========
@register("marketplace_list")
def marketplace_list():
    """市场产品列表"""
    from flask import jsonify

    from core.lib.marketplace_data import marketplace_data

    products = marketplace_data.list_products()
    return jsonify({"success": True, "products": products, "total": len(products)})


@register("marketplace_install")
def marketplace_install():
    """安装产品"""
    from flask import jsonify, request

    from core.lib.marketplace_data import marketplace_data

    data = request.get_json() or {}
    product_id = data.get("product_id", "")
    user_id = data.get("user_id", "default")

    if not product_id:
        return jsonify({"success": False, "error": "product_id required"}), 400

    result = marketplace_data.install_product(product_id, user_id)
    return jsonify(result)


@register("marketplace_installed")
def marketplace_installed():
    """已安装列表"""
    from flask import jsonify, request

    from core.lib.marketplace_data import marketplace_data

    user_id = request.args.get("user_id", "default")
    installed = marketplace_data.list_installed(user_id)

    return jsonify({"success": True, "agents": installed, "total": len(installed)})


@register("marketplace_uninstall")
def marketplace_uninstall():
    """卸载产品"""
    from flask import jsonify, request

    from core.lib.marketplace_data import marketplace_data

    data = request.get_json() or {}
    product_id = data.get("product_id", "")
    user_id = data.get("user_id", "default")

    if not product_id:
        return jsonify({"success": False, "error": "product_id required"}), 400

    result = marketplace_data.uninstall_product(product_id, user_id)
    return jsonify(result)


@register("marketplace_upload")
def marketplace_upload():
    """上传技能到市场"""
    import uuid
    from datetime import datetime

    from flask import jsonify, request

    from core.lib.marketplace_data import marketplace_data

    data = request.get_json() or {}
    skill_name = data.get("name", "")
    skill_code = data.get("code", "")
    author = data.get("author", "developer")

    if not skill_name or not skill_code:
        return jsonify({"success": False, "error": "name and code required"}), 400

    # 保存到待审核
    product_id = str(uuid.uuid4())[:8]
    product = {
        "id": product_id,
        "name": skill_name,
        "type": "skill",
        "version": "1.0.0",
        "description": data.get("description", ""),
        "code": skill_code,
        "author": author,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }

    result = marketplace_data.add_pending(product)
    return jsonify({"success": True, "product_id": product_id, "message": "技能已提交审核"})


@register("marketplace_review")
def marketplace_review():
    """审核产品"""
    from flask import jsonify, request

    from core.lib.marketplace_data import marketplace_data

    data = request.get_json() or {}
    product_id = data.get("product_id", "")
    action = data.get("action", "")  # approve / reject
    comment = data.get("comment", "")

    if not product_id or action not in ["approve", "reject"]:
        return (
            jsonify({"success": False, "error": "product_id and action required"}),
            400,
        )

    result = marketplace_data.review_product(product_id, action, comment)
    return jsonify(result)


@register("marketplace_list_products")
def marketplace_list_products():
    """市场产品列表（别名）"""
    return marketplace_list()


# ========== 主动服务 API ==========
@register("proactive_status")
def proactive_status():
    """主动服务状态"""
    from flask import jsonify

    return jsonify(
        {
            "success": True,
            "status": "running",
            "services": [
                "morning_greeting",
                "idle_reminder",
                "todo_reminder",
                "health_check",
            ],
        }
    )


@register("trigger_meeting")
def trigger_meeting():
    """触发会议（闭环）"""
    from flask import jsonify, request

    from core.lib.feedback_system import feedback_system

    data = request.get_json() or {}
    user_id = data.get("user_id")
    issue = data.get("issue", "")
    level = data.get("level", "info")

    result = feedback_system.should_trigger_meeting(user_id)

    return jsonify({"success": True, "trigger": result, "issue": issue, "level": level})


# ========== 知识中心处理器 ==========
@register("knowledge_search")
def knowledge_search():
    """知识库语义搜索"""
    from flask import jsonify, request

    from core.lib.knowledge_registry import knowledge_registry

    data = request.get_json() or {}
    query = data.get("query", "")
    category = data.get("category")
    n = data.get("n", 5)

    if not query:
        return jsonify({"success": False, "error": "query required"}), 400

    results = knowledge_registry.search(query, category, n)
    return jsonify({"success": True, "results": results})


@register("knowledge_stats")
def knowledge_stats():
    """知识库统计"""
    from flask import jsonify

    from core.lib.knowledge_registry import knowledge_registry

    stats = knowledge_registry.get_stats()
    return jsonify({"success": True, "stats": stats})


@register("knowledge_add")
def knowledge_add():
    """添加知识条目"""
    from flask import jsonify, request

    from core.lib.knowledge_registry import knowledge_registry

    data = request.get_json() or {}
    title = data.get("title", "")
    content = data.get("content", "")
    category = data.get("category", "general")
    tags = data.get("tags", [])

    if not title or not content:
        return jsonify({"success": False, "error": "title and content required"}), 400

    knowledge_registry.add_knowledge(title, content, category, tags=tags)
    return jsonify({"success": True, "message": "知识已添加"})


# ========== 俱乐部处理器 ==========
@register("club_stats")
def club_stats():
    """俱乐部统计"""
    from flask import jsonify

    return jsonify(
        {
            "success": True,
            "stats": {
                "total_members": 0,
                "active_members": 0,
                "levels": {"bronze": 0, "silver": 0, "gold": 0, "diamond": 0},
            },
        }
    )


@register("club_member")
def club_member():
    """俱乐部成员信息"""
    from flask import jsonify, request

    user_id = request.args.get("user_id", "default")
    return jsonify(
        {
            "success": True,
            "member": {
                "user_id": user_id,
                "level": "bronze",
                "interactions": 0,
                "joined_at": None,
            },
        }
    )


@register("club_leaderboard")
def club_leaderboard():
    """俱乐部排行榜"""
    from flask import jsonify

    return jsonify({"success": True, "leaderboard": []})


# ========== 开发者注册 ==========
@register("developer_register")
def developer_register():
    """开发者注册"""
    from flask import jsonify, request

    from core.lib.developer_api import developer_api

    data = request.get_json() or {}
    developer_id = data.get("developer_id", "")
    name = data.get("name", "")
    email = data.get("email", "")

    if not developer_id or not name or not email:
        return (
            jsonify({"success": False, "error": "developer_id, name, email required"}),
            400,
        )

    result = developer_api.register_developer(developer_id, name, email)
    return jsonify(result)


# ========== 工作流执行 ==========
@register("execute_workflow")
def execute_workflow():
    """执行工作流"""
    from flask import jsonify, request

    from core.lib.skill_chain_executor import skill_chain

    data = request.get_json() or {}
    workflow_name = data.get("workflow", data.get("name", ""))
    params = data.get("params", {})

    if not workflow_name:
        return jsonify({"success": False, "error": "workflow name required"}), 400

    result = skill_chain.execute_workflow(workflow_name, params)
    return jsonify(result)


# ========== Agent 记忆自检 API ==========
@register("agent_self_check")
def agent_self_check():
    """Agent 自检 - 检查技能、知识、记忆状态"""
    from flask import jsonify

    from core.lib.agent_memory_self_check import agent_memory_self_check

    stats = agent_memory_self_check.get_stats()
    return jsonify({"success": True, "stats": stats})


@register("agent_skill_search")
def agent_skill_search():
    """语义搜索技能"""
    from flask import jsonify, request

    from core.lib.agent_memory_self_check import agent_memory_self_check

    data = request.get_json() or {}
    query = data.get("query", "")
    n = data.get("n", 5)

    if not query:
        return jsonify({"success": False, "error": "query required"}), 400

    results = agent_memory_self_check.search_skill(query, n)
    return jsonify({"success": True, "results": results})


@register("agent_knowledge_search")
def agent_knowledge_search():
    """语义搜索知识"""
    from flask import jsonify, request

    from core.lib.agent_memory_self_check import agent_memory_self_check

    data = request.get_json() or {}
    query = data.get("query", "")
    n = data.get("n", 5)

    if not query:
        return jsonify({"success": False, "error": "query required"}), 400

    results = agent_memory_self_check.search_knowledge(query, n)
    return jsonify({"success": True, "results": results})


# ========== 热重载技能 ==========
@register("hot_reload_skills")
def hot_reload_skills():
    """热重载技能 - 重新索引所有技能"""
    from api.skill_market import skill_recommender
    from flask import jsonify

    from core.lib.skill_loader_v3 import skill_loader

    # 重新加载技能
    skill_loader._load_all()

    # 重新索引技能向量
    skill_recommender._index_existing_skills()

    return jsonify(
        {
            "success": True,
            "message": "技能已热重载",
            "skills_count": len(skill_loader.list_skills()),
        }
    )


# ========== 管理类处理器 ==========
@register("admin_list_agents")
def admin_list_agents():
    from flask import jsonify

    from core.agents.builtin.agent_manager import agent_manager

    return jsonify({"success": True, "agents": list(agent_manager.agents.keys())})


@register("admin_toggle_agent")
def admin_toggle_agent():
    from flask import jsonify, request

    return jsonify({"success": True, "message": "Agent状态已切换"})


@register("admin_reload_config")
def admin_reload_config():
    from flask import jsonify

    from core.lib.unified_config import unified_config

    unified_config.reload()
    return jsonify({"success": True, "message": "配置已重载"})


@register("admin_create_agent")
def admin_create_agent():
    from flask import jsonify

    return jsonify({"success": True, "message": "创建Agent功能开发中"})


@register("admin_update_agent")
def admin_update_agent():
    from flask import jsonify

    return jsonify({"success": True, "message": "更新Agent功能开发中"})


@register("admin_delete_agent")
def admin_delete_agent():
    from flask import jsonify

    return jsonify({"success": True, "message": "删除Agent功能开发中"})


@register("admin_reload_agents")
def admin_reload_agents():
    from flask import jsonify

    from core.agents.builtin.agent_manager import agent_manager

    agent_manager.reload()
    return jsonify({"success": True, "message": "Agent配置已重载"})


# ========== 反馈类处理器 ==========
@register("feedback_submit")
def feedback_submit():
    """提交反馈 - 触发闭环学习"""
    import threading

    from flask import jsonify, request

    from core.learner.self_learning_coordinator import SelfLearningCoordinator
    from core.lib.feedback_system import feedback_system

    data = request.get_json() or {}
    user_id = data.get("user_id", "anonymous")
    skill_id = data.get("skill_id", "")
    rating = data.get("rating", 3)
    comment = data.get("comment", "")

    # 记录反馈
    result = feedback_system.update_satisfaction(user_id, {"skill_id": skill_id, "rating": rating, "comment": comment})

    # 低分反馈触发学习
    if rating <= 2:

        def trigger_learning():
            coordinator = SelfLearningCoordinator()
            scenario = {
                "type": "feedback_improvement",
                "input": (f"优化技能 {skill_id}: {comment}" if comment else f"用户对 {skill_id} 不满意"),
                "expected": f"{skill_id} 质量提升",
            }
            coordinator.learn_from_scenario(scenario)

        threading.Thread(target=trigger_learning, daemon=True).start()

    return jsonify({"success": True, "message": "反馈已提交", "auto_learning": rating <= 2})


@register("feedback_stats")
def feedback_stats():
    from flask import jsonify

    from core.lib.feedback_system import feedback_system

    stats = feedback_system.get_stats()
    return jsonify({"success": True, "stats": stats})


# ========== 学习类处理器 ==========
@register("learning_stats")
def learning_stats():
    from flask import jsonify

    from core.learner.self_learning_coordinator import SelfLearningCoordinator

    coordinator = SelfLearningCoordinator()
    return jsonify({"success": True, "stats": coordinator.stats})


@register("learning_trigger")
def learning_trigger():
    """手动触发学习"""
    from flask import jsonify, request

    from core.learner.self_learning_coordinator import SelfLearningCoordinator

    data = request.get_json() or {}
    scenario = data.get("scenario", {})
    user_id = data.get("user_id", "default")

    if not scenario:
        return jsonify({"success": False, "error": "scenario required"}), 400

    coordinator = SelfLearningCoordinator()
    result = coordinator.learn_from_scenario(scenario)

    # 记录学习历史
    import json
    from pathlib import Path

    history_file = Path(f"data/users/{user_id}/learning_history.json")
    history = []
    if history_file.exists():
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)

    history.append(
        {
            "scenario": scenario,
            "result": result,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }
    )
    history = history[-100:]
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    return jsonify({"success": result.get("success", False), "result": result})


# ========== 本地Agent处理器 ==========
@register("local_agent_list")
def local_agent_list():
    """列出本地Agent"""
    from flask import jsonify

    from core.agents.builtin.agent_manager import agent_manager

    agents = agent_manager.list_agents()
    return jsonify({"success": True, "agents": agents, "total": len(agents)})


@register("local_agent_register")
def local_agent_register():
    """注册本地Agent"""
    from flask import jsonify, request

    from core.agents.builtin.agent_manager import agent_manager

    data = request.get_json() or {}
    agent_id = data.get("agent_id", "")
    agent_info = data.get("agent_info", {})

    if not agent_id:
        return jsonify({"success": False, "error": "agent_id required"}), 400

    agent_manager.agents[agent_id] = agent_info
    agent_manager._save()

    return jsonify({"success": True, "message": f"Agent {agent_id} 已注册"})


@register("local_agent_call")
def local_agent_call():
    """调用本地Agent"""
    import importlib

    from flask import jsonify, request

    from core.agents.builtin.agent_manager import agent_manager

    data = request.get_json() or {}
    agent_name = data.get("agent", "")
    message = data.get("message", "")
    user_id = data.get("user_id", "default")

    if not agent_name or not message:
        return jsonify({"success": False, "error": "agent and message required"}), 400

    agent_config = agent_manager.get_agent(agent_name)
    if not agent_config:
        return (
            jsonify({"success": False, "error": f"Agent {agent_name} not found"}),
            404,
        )

    module_name = agent_config.get("module")
    class_name = agent_config.get("class")

    if module_name and class_name:
        module = importlib.import_module(module_name)
        agent_class = getattr(module, class_name)
        agent = agent_class(user_id=user_id)
        result = agent.process(message)
        return jsonify(
            {
                "success": result.get("success", True),
                "response": result.get("response", ""),
                "agent": agent_name,
                "user_id": user_id,
            }
        )

    return jsonify({"success": False, "error": "Agent 配置不完整"}), 500


@register("local_agent_test")
def local_agent_test():
    """测试本地Agent"""
    from flask import jsonify

    from core.agents.builtin.agent_manager import agent_manager

    agents = agent_manager.list_agents()
    return jsonify(
        {
            "success": True,
            "message": "本地Agent系统正常",
            "agents_count": len(agents),
            "status": "healthy",
        }
    )


# ========== 沙箱处理器 ==========
@register("sandbox_list")
def sandbox_list():
    """列出沙箱"""
    from pathlib import Path

    from flask import jsonify

    sandboxes = []
    sandbox_dir = Path("data/sandboxes")
    if sandbox_dir.exists():
        for d in sandbox_dir.iterdir():
            if d.is_dir():
                sandboxes.append(d.name)

    return jsonify({"success": True, "sandboxes": sandboxes, "total": len(sandboxes)})


@register("sandbox_call")
def sandbox_call():
    """调用沙箱"""
    from pathlib import Path

    from flask import jsonify, request

    data = request.get_json() or {}
    sandbox_id = data.get("sandbox_id", "")
    action = data.get("action", "")

    if not sandbox_id:
        return jsonify({"success": False, "error": "sandbox_id required"}), 400

    sandbox_path = Path(f"data/sandboxes/{sandbox_id}")
    if not sandbox_path.exists():
        return jsonify({"success": False, "error": f"沙箱 {sandbox_id} 不存在"}), 404

    return jsonify(
        {
            "success": True,
            "message": f"沙箱 {sandbox_id} 执行 {action}",
            "sandbox_id": sandbox_id,
            "action": action,
        }
    )


@register("sandbox_destroy")
def sandbox_destroy():
    """销毁沙箱"""
    import shutil
    from pathlib import Path

    from flask import jsonify, request

    data = request.get_json() or {}
    sandbox_id = data.get("sandbox_id", "")

    if not sandbox_id:
        return jsonify({"success": False, "error": "sandbox_id required"}), 400

    sandbox_path = Path(f"data/sandboxes/{sandbox_id}")
    if sandbox_path.exists():
        shutil.rmtree(sandbox_path)
        return jsonify({"success": True, "message": f"沙箱 {sandbox_id} 已销毁"})

    return jsonify({"success": False, "error": f"沙箱 {sandbox_id} 不存在"}), 404


@register("marketplace_install")
def marketplace_install():
    from flask import jsonify, request

    return jsonify({"success": True, "message": "安装成功"})


# ========== 向量搜索 ==========
@register("vector_search")
def vector_search():
    """向量搜索"""
    from flask import jsonify, request

    from core.lib.memory import memory

    data = request.get_json() or {}
    query = data.get("query", "")
    user_id = data.get("user_id", "default")
    n = data.get("n", 5)

    if not query:
        return jsonify({"success": False, "error": "query required"}), 400

    results = memory.recall(query, user_id=user_id, n=n)
    return jsonify({"success": True, "results": results})


@register("vector_add")
def vector_add():
    """添加向量"""
    from flask import jsonify, request

    from core.lib.memory import memory

    data = request.get_json() or {}
    text = data.get("text", "")
    category = data.get("category", "general")
    user_id = data.get("user_id", "default")

    if not text:
        return jsonify({"success": False, "error": "text required"}), 400

    memory.remember(text, category=category, user_id=user_id)
    return jsonify({"success": True, "message": "向量已添加"})


# ========== 私人管家（兼容旧版 API）==========
import requests


@register("butler_chat")
@register("butler_chat")
def butler_chat():
    """私人管家对话 - 统一调用私人管家"""
    from flask import jsonify, request

    from core.agents.builtin.personal_butler_v2 import PersonalButlerV2

    data = request.get_json() or {}
    user_id = data.get("user_id", "default")
    message = data.get("message", "")

    if not message:
        return jsonify({"success": False, "error": "message required"}), 400

    butler = PersonalButlerV2(user_id=user_id)
    result = butler.process(message)

    return jsonify(
        {
            "success": result.get("success", True),
            "response": result.get("response", ""),
            "user_id": user_id,
        }
    )

    #     from flask import jsonify, request

    from core.agents.builtin.personal_butler_v2 import PersonalButlerV2

    data = request.get_json() or {}
    user_id = data.get("user_id", "default")
    message = data.get("message", "")

    if not message:
        return jsonify({"success": False, "error": "message required"}), 400

    butler = PersonalButlerV2(user_id=user_id)
    result = butler.process(message)

    return jsonify(
        {
            "success": result.get("success", True),
            "response": result.get("response", ""),
            "user_id": user_id,
        }
    )
