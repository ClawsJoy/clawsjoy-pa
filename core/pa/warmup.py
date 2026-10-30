# -*- coding: utf-8 -*-
"""PA 本地模型启动预热。

问题：7B q4 冷加载约 40s；用户第一问恰好踩在冷加载上。
做法：app 启动后后台发一个 1-token 请求，按实际 num_ctx/keep_alive 把模型装好；
      用户第一问只付推理时间，不再付 40s 装载。
边界：只预热本地 Ollama；失败静默（不影响主流程）；CLAWSJOY_WARMUP=0 可关。
"""
from __future__ import annotations

import logging
import os
import threading

_LOCK = threading.Lock()
_STARTED = False
_LOG = logging.getLogger(__name__)


def _warm() -> None:
    try:
        from core.lib.llm_client import LLMClient

        # 1 token 足够把模型按当前 num_ctx/keep_alive 装入并驻留
        LLMClient().generate("你好", max_tokens=1, timeout=180)
        _LOG.info("[PA] 本地模型预热完成")
    except Exception as e:
        _LOG.warning("[PA] 本地模型预热失败（不影响主流程）：%s", str(e)[:200])


def start_warmup() -> bool:
    """启动一次后台预热；已有线程则跳过。返回是否新起线程。"""
    global _STARTED
    if os.environ.get("CLAWSJOY_WARMUP", "1") == "0":
        return False
    with _LOCK:
        if _STARTED:
            return False
        _STARTED = True
    threading.Thread(target=_warm, name="pa-model-warmup", daemon=True).start()
    return True
