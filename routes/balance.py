# -*- coding: utf-8 -*-
"""余额查询路由（P1 拆出，Blueprint）—— DeepSeek / GLM / 汇总（无编排逻辑）。"""

import os

from flask import Blueprint, jsonify

bp = Blueprint("balance_routes", __name__)


@bp.route("/v9/user/balance", methods=["GET"])
def v9_user_balance():
    """查询 DeepSeek 账户余额（GET 端点，无编排逻辑）。"""
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        return jsonify({"success": False, "error": "未配置 API Key"})
    try:
        import requests as _r

        resp = _r.get(
            "https://api.deepseek.com/user/balance",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
            proxies={"http": None, "https": None},  # 防御：不继承外部代理 env
        )
        if resp.status_code == 200:
            data = resp.json()
            balance_info = data.get("balance_infos", [{}])[0]
            return jsonify(
                {
                    "success": True,
                    "available": data.get("is_available", False),
                    "currency": balance_info.get("currency", "CNY"),
                    "total": balance_info.get("total_balance", "0"),
                    "topped_up": balance_info.get("topped_up_balance", "0"),
                    "granted": balance_info.get("granted_balance", "0"),
                }
            )
        return jsonify({"success": False, "error": f"API错误: {resp.status_code}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@bp.route("/v9/glm/balance", methods=["GET"])
def v9_glm_balance():
    api_key = os.getenv("GLM_API_KEY", "")
    if not api_key:
        return jsonify({"success": False, "error": "未配置 GLM API Key"})
    try:
        import requests as _r

        resp = _r.get(
            "https://open.bigmodel.cn/api/paas/v4/user/balance",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            balance_info = data.get("balance_infos", [{}])[0] if data.get("balance_infos") else {}
            return jsonify(
                {
                    "success": True,
                    "total": balance_info.get("total_balance", data.get("balance", "0")),
                    "currency": balance_info.get("currency", "CNY"),
                }
            )
        return jsonify({"success": False, "error": f"API错误: {resp.status_code}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@bp.route("/v9/balance", methods=["GET"])
def v9_balance():
    result = {"deepseek": {}, "glm": {}, "total_cost": 0}

    # DeepSeek 余额
    try:
        ds_key = os.getenv("DEEPSEEK_API_KEY", "")
        if ds_key:
            import requests as _r

            resp = _r.get(
                "https://api.deepseek.com/user/balance",
                headers={"Authorization": f"Bearer {ds_key}"},
                timeout=10,
                proxies={"http": None, "https": None},
            )  # 防御：不继承外部代理 env
            if resp.status_code == 200:
                data = resp.json()
                info = data.get("balance_infos", [{}])[0]
                result["deepseek"] = {"total": info.get("total_balance", "0"), "currency": "CNY"}
    except Exception:
        pass

    # GLM 余额
    try:
        glm_key = os.getenv("GLM_API_KEY", "")
        if glm_key:
            resp = _r.get(
                "https://open.bigmodel.cn/api/paas/v4/user/balance",
                headers={"Authorization": f"Bearer {glm_key}"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                result["glm"] = {"total": data.get("balance", "0"), "currency": "CNY"}
    except Exception:
        pass

    # 总花费
    try:
        from core.lib.v8.ledger import ledger

        billing = ledger.get_billing("default")
        result["total_cost"] = round(billing.get("total", 0), 4)
    except Exception:
        pass

    return jsonify({"success": True, **result})
