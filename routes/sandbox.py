# -*- coding: utf-8 -*-
"""沙箱路由（P1 拆出，Blueprint）

5 个薄包装路由 → core.gateway.sandbox_ops 的 handler。
另 3 个（list/rollback/checkpoint）仍在主文件（重内联逻辑，依赖主文件局部全局，待下一刀归位）。
"""
from flask import Blueprint

bp = Blueprint("sandbox", __name__)


@bp.route("/v9/sandbox/read", methods=["POST"])
def v9_sandbox_read():
    from core.gateway.sandbox_ops import v9_sandbox_read_handler

    return v9_sandbox_read_handler()


@bp.route("/v9/sandbox/search", methods=["POST"])
def v9_sandbox_search():
    from core.gateway.sandbox_ops import v9_sandbox_search_handler

    return v9_sandbox_search_handler()


@bp.route("/v9/sandbox/query_index", methods=["POST"])
def v9_sandbox_query_index():
    from core.gateway.sandbox_ops import v9_sandbox_query_index_handler

    return v9_sandbox_query_index_handler()


@bp.route("/v9/sandbox/exec", methods=["POST"])
def v9_sandbox_exec():
    from core.gateway.sandbox_ops import v9_sandbox_exec_handler

    return v9_sandbox_exec_handler()


@bp.route("/v9/sandbox/edit", methods=["POST"])
def v9_sandbox_edit():
    from core.gateway.sandbox_ops import v9_sandbox_edit_handler

    return v9_sandbox_edit_handler()


@bp.route("/v9/sandbox/checkpoint", methods=["POST"])
def v9_sandbox_checkpoint():
    from core.gateway.sandbox_ops import v9_sandbox_checkpoint_handler

    return v9_sandbox_checkpoint_handler()


@bp.route("/v9/sandbox/rollback", methods=["POST"])
def v9_sandbox_rollback():
    from core.gateway.sandbox_ops import v9_sandbox_rollback_handler

    return v9_sandbox_rollback_handler()


@bp.route("/v9/sandbox/list", methods=["POST"])
def v9_sandbox_list():
    from core.gateway.sandbox_ops import v9_sandbox_list_handler

    return v9_sandbox_list_handler()
