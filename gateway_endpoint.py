# -*- coding: utf-8 -*-
"""cheap reader —— **出口层**（`web/` · `engine/`）可读的轻量网关地址出口。

为什么要独立于 ``core/lib/port_config.py``（DS 2026-09-20 裁 · 标"DS 代理拍板·待追认"）
--------------------------------------------------------------------------------
**出口层不得直接 import 应用内核（core）**。实测（本树，非推断）：

    $ python web\\_x12_import_probe.py
    ModuleNotFoundError: No module named 'core'

（脚本方式 ``sys.path[0] = web/``，仓根不在路径上 —— `start_all.sh:26` 就是
 ``streamlit run web/app_complete.py`` 这种脚本方式。）⇒ 直连 core 是"一跑就炸"，
 且 ``core.lib.unified_config`` 初始化有代价（web 侧每 rerun 都付）。

本件因此**不 import core、不做 config 初始化**，只做两件事：
  ① env ``V9_URL``（**启动侧注入** = 兼容层；不落盘、不写文件）
  ② 直读真源文件 ``config/system/system_unified.yaml`` 的 ``services.gateway.port``
     —— **纯文本行扫**（不引 yaml、不建配置管理器）

判据（该红的那一格）
--------------------
本件给出 **5102**（本树真源），而**旧路径给 5002** ⇒ 两边取值不同（L-62）。
未配 ⇒ **拒启**（同 core 侧出口的 fail-loud 口径；不回落字面量）。
"""
import os

_ROOT = os.path.dirname(os.path.abspath(__file__))
_CONFIG = os.path.join(_ROOT, "config", "system", "system_unified.yaml")

# 客户端默认主机（不是 services.gateway.host —— 那是 0.0.0.0 **绑定**地址）
CLIENT_HOST = "127.0.0.1"


def _port_from_config():
    """纯文本扫 ``services.gateway.port``：不引 yaml、不建配置管理器。取不到 ⇒ None。"""
    try:
        with open(_CONFIG, encoding="utf-8") as f:
            in_gateway = False
            for line in f:
                s = line.rstrip("\n")
                if not s.strip() or s.lstrip().startswith("#"):
                    continue
                indent = len(s) - len(s.lstrip(" "))
                body = s.strip()
                if indent == 2 and body.endswith(":"):
                    in_gateway = (body == "gateway:")
                    continue
                if in_gateway and indent == 4 and body.startswith("port:"):
                    return int(body.split(":", 1)[1].strip().strip('"\''))
    except OSError:
        return None
    return None


def gateway_port():
    """网关端口（真源）。未配 ⇒ 拒启（fail-loud，不回落字面量）。"""
    v = _port_from_config()
    if v is None:
        raise RuntimeError(
            "services.gateway.port 未配 ⇒ 拒启（cheap reader；真源 = config/system/system_unified.yaml）")
    return v


def gateway_base_url(host=None):
    """网关基址（无尾斜杠）。优先级：env ``V9_URL`` > 真源端口 + ``CLIENT_HOST``。"""
    env = os.environ.get("V9_URL")
    if env:
        return env.rstrip("/")
    return "http://%s:%d" % (host or CLIENT_HOST, gateway_port())