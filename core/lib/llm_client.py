# core/lib/llm_client.py
"""统一LLM客户端 - 所有Agent的唯一LLM入口"""

import logging
import json
import os
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, Optional

# 测试效率优化: tiktoken BPE 词表首次加载 ~9.7s, 模块级缓存避免重复 encoding_for_model
_TIKTOKEN_ENC_LLM = None


def _get_tiktoken_enc_llm():
    global _TIKTOKEN_ENC_LLM
    if _TIKTOKEN_ENC_LLM is None:
        import tiktoken

        _TIKTOKEN_ENC_LLM = tiktoken.encoding_for_model("gpt-4")
    return _TIKTOKEN_ENC_LLM


import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.lib.os_event_logger import write_os_event
from pathlib import Path

from core.lib import _proc as _proc  # ⭐ 子进程唯一出口（窗隐）

logger = logging.getLogger(__name__)


# X-21（2026-09-18 拍）：本机服务探测**不得走代理**。
# `.env` 注入 `HTTP_PROXY`（为沙箱 yt-dlp 下载有意保留）；不显式绕开时，
# 连 `http://127.0.0.1:11434` 也会被送去代理 —— 代理未监听时探测恒失败。
# 独立 session：`trust_env=False`，且**不挂重试适配器**（探测＝只探一次，不重试）。
_PROBE_SESSION = requests.Session()
_PROBE_SESSION.trust_env = False


def _get_model_context_window(model):
    """读取模型实际 context_window（与 gateway 侧 agent_gateway_enhanced._get_model_context_window 一致）。

    优先从 config/v8/available_models.yaml 的模型条目中读取 context_window 配置；
    未配置时回退默认值 65536。
    """
    try:
        import yaml

        with open("config/v8/available_models.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for m in (data or {}).get("models", []) or []:
            if m.get("value") == model and m.get("context_window"):
                return int(m["context_window"])
    except Exception:
        pass
    # deepseek-v4-flash 默认 context_window
    return 65536


def _calc_token_budget(model="deepseek-v4-flash", tools=None):
    """计算当前模型/工具集的 Token 预算（统一截断预算基准，与 gateway 侧 agent_gateway_enhanced._calc_token_budget 一致）。

    公式：budget = context_window - max_tokens(输出预留4000) - tg_estimate(tools)
    - context_window：模型实际上下文窗口（_get_model_context_window 读取，默认 65536）
    - max_tokens：输出预留固定 4000 tokens
    - tg_estimate(tools)：工具定义本身占用的上下文 token
    所有截断决策（TOKEN_GUARD / MSG_CAP / 主动压缩）均应以本预算为统一基准。
    """
    _cw = _get_model_context_window(model)
    _out_reserve = 4000
    _tools_est = 0
    if tools:
        try:
            _enc = _get_tiktoken_enc_llm()
            _tools_est = len(_enc.encode(str(tools)))
        except Exception:
            _tools_est = int(len(str(tools)) * 0.5)
    _budget = _cw - _out_reserve - _tools_est
    return max(_budget, 0)


@dataclass
class LLMConfig:
    provider: str = "ollama"
    base_url: str = "http://127.0.0.1:11434"
    default_model: str = "qwen2.5:7b-instruct-q4_0-gpu"
    light_model: str = "qwen2.5:7b-instruct-q4_0-gpu"
    medium_model: str = "qwen2.5:7b-instruct-q4_0-gpu"
    temperature: float = 0.4
    timeout: int = 120
    max_retries: int = 3


class LLMClient:
    """统一LLM客户端 - 单例"""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self.config = LLMConfig()
        self._session = requests.Session()
        self._session.trust_env = False
        retry = Retry(total=3, backoff_factor=2.0, status_forcelist=[500, 502, 503])
        adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20, max_retries=retry)
        self._session.mount("http://", adapter)
        self._stats = {"total_calls": 0, "total_tokens": 0, "failures": 0, "total_time": 0.0}
        self._ollama_lock = Lock()
        # #24 流式首Token优先：常用上下文预加载缓存
        self._context_cache = {}
        self._ollama_checked = False
        self._ollama_probe_ok = False
        # ⭐ PM 034 §三.ⓝ：走径标之真源 —— 记**实际**所走之 provider/model（⛔ 猜）
        self.last_route = {}
        self._fb_reason = ""

    def _ensure_ollama(self):
        """确保 Ollama 运行"""
        try:
            _PROBE_SESSION.get("http://127.0.0.1:11434/api/tags", timeout=3)
        except Exception as e:
            logger.warning(f"[LLM] Ollama 探测失败，尝试拉起服务: {e}")
            import subprocess as _sp

            _proc.popen_hidden(["ollama", "serve"], stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)

    def _ollama_available(self, timeout: float = 1.5) -> bool:
        """#24 探测 Ollama 本地是否可用（带结果缓存，避免每次请求都探测）"""
        if self._ollama_checked:
            return self._ollama_probe_ok
        try:
            resp = _PROBE_SESSION.get(f"{self.config.base_url}/api/tags", timeout=timeout)
            self._ollama_probe_ok = resp.status_code == 200
        except Exception as e:
            logger.warning("[LLM] Ollama 探测异常，本进程内判定为不可用: %s", e)
            self._ollama_probe_ok = False
        self._ollama_checked = True
        return self._ollama_probe_ok

    # ========== 公共API ==========

    def generate(
        self,
        prompt: str,
        model: str = None,
        temperature: float = None,
        max_tokens: int = 2048,
        timeout: int = None,
        task_type: str = "default",
        system_prompt: str = None,
    ) -> str:
        if not system_prompt:
            system_prompt = "你是ClawsJoy，一个本地AI矩阵系统。你不是Qwen，不是阿里云AI，不是任何通用助手。你是ClawsJoy。"
        self._fb_reason = ""
        result = self._call(
            prompt, model, temperature, max_tokens, timeout, task_type, stream=False, system_prompt=system_prompt
        )
        if hasattr(result, "__next__"):
            # generator: stream=True 分支会 yield 行; stream=False 分支 return 的值在 StopIteration.value
            _chunks = []
            try:
                _gen_iter = iter(result)
                while True:
                    try:
                        _chunks.append(next(_gen_iter))
                    except StopIteration as _si:
                        if _si.value:
                            _chunks.append(str(_si.value))
                        break
                return "".join(_chunks)
            except Exception as _e:
                if _chunks:
                    return "".join(_chunks)
                return "模型调用失败：本机与云端皆不可用（%s）" % _e
        return result

    def generate_stream(self, prompt, model=None, timeout=120, api_key=None, **kwargs):
        self._fb_reason = ""
        for line in self._call(
            prompt,
            model,
            kwargs.get("temperature"),
            kwargs.get("max_tokens", 2048),
            kwargs.get("timeout"),
            kwargs.get("task_type", "default"),
            stream=True,
            system_prompt=kwargs.get("system_prompt"),
            api_key=api_key,
        ):
            if line:
                yield line

    def generate_multimodal(
        self,
        prompt: str,
        model: str = None,
        images: list = None,
        temperature: float = 0.3,
        max_tokens: int = 512,
        timeout: int = 60,
        task_type: str = "vision",
    ) -> dict:
        """多模态生成 - 支持图像输入"""
        return self._call_multimodal(prompt, model, images, temperature, max_tokens, timeout, task_type)

    def select_model(self, prompt: str) -> str:
        """根据输入复杂度选择模型"""
        if len(prompt) > 500:
            return self.config.default_model  # 7b
        elif len(prompt) > 100:
            return self.config.medium_model  # 3b
        return self.config.light_model  # 1.5b

    def get_stats(self) -> Dict:
        return dict(self._stats)

    def _route_set(self, provider, model, fell_back=False, reason=""):
        self.last_route = {"provider": provider, "model": model,
                           "fell_back": bool(fell_back), "reason": reason}

    def get_last_route(self):
        return dict(self.last_route or {})

    def _call(
        self,
        prompt: str,
        model: str = None,
        temperature: float = None,
        max_tokens: int = 2048,
        timeout: int = None,
        task_type: str = "default",
        stream: bool = False,
        system_prompt: str = None,
        api_key: str = None,
    ) -> str:
        # ⭐ P2 正式化（PA 自病单 · 原 PM 2026-10-05 测试脚手架 ⇒ 今立为制）：**先代默认模型, 再判 provider**
        # 由: PA 之路以 model=None 调 ⇒ 若 provider 判在前, 远端支永不入 ⇒
        #     默认名被喂给本机 Ollama ⇒ API_UNAVAILABLE: HTTP 404（实测）。
        # 复查（技总一手 · 2026-10-05）：glm （:311）／ claude（:345）两支位于此定点之**下游** ⇒ 一处 hoist 受益三者（⛔ 三处各改）。
        model = model or self.config.default_model
        # ⭐ DeepSeek 分支：先检查 api_key，无 key 则降级到 Ollama
        if model and model.startswith("deepseek"):
            api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("[LLM] DeepSeek API Key 未设置，降级到 Ollama 默认模型")
                self._fb_reason = "no_api_key"
                model = None  # 降级：走下面的 Ollama 分支
            else:
                self._route_set("deepseek", model)
                # #24 请求前预加载常用上下文到缓存，减少首Token等待
                self._preload_context_cache(system_prompt, task_type)
                try:
                    gen = self._call_openai_compatible(
                        prompt,
                        model,
                        temperature or 0.7,
                        max_tokens,
                        timeout or 60,
                        stream,
                        system_prompt,
                        api_key=api_key,
                    )
                    if stream:
                        # ★ §二.3 裁（PM 2026-10-05 · 拆混路）：云端流式 ⛔ 掺本机首 token
                        # 由：首 token 本机 ／ 后续云端 ⇒ 答体两模型混成 ⇒ 走径标必假 ⇒ 路径须唯一可归
                        yield from gen
                        return
                    try:
                        while True:
                            next(gen)
                    except StopIteration as e:
                        return e.value
                except Exception as e:
                    _em = str(e)
                    if _em.startswith("API_EMPTY:"):
                        # ★ P3：空答 ≠ 故障（因与量入走径标）
                        logger.warning(f"[LLM] 云端 支空答（非故障），降级到 Ollama：{_em}")
                        self._fb_reason = "empty_answer: " + _em.split(":", 1)[1].strip()
                    else:
                        logger.warning(f"[LLM] 云端 API 不可用，降级到 Ollama: {e}")
                        self._fb_reason = "cloud_unavailable"
                    model = None

        # ⭐ GLM 分支
        if model and model.startswith("glm"):
            api_key = api_key or os.getenv("GLM_API_KEY", "")
            if not api_key:
                logger.warning("[LLM] GLM API Key 未设置，降级到 Ollama 默认模型")
                self._fb_reason = "no_api_key"
                model = None
            else:
                self._route_set("glm", model)
                try:
                    gen = self._call_openai_compatible(
                        prompt,
                        model,
                        temperature or 0.7,
                        max_tokens,
                        timeout or 60,
                        stream,
                        system_prompt,
                        endpoint="https://open.bigmodel.cn/api/paas/v4",
                        api_key=api_key,
                    )
                    if stream:
                        yield from gen
                        return
                    try:
                        while True:
                            next(gen)
                    except StopIteration as e:
                        return e.value
                except Exception as e:
                    _em = str(e)
                    if _em.startswith("API_EMPTY:"):
                        # ★ P3：空答 ≠ 故障（因与量入走径标）
                        logger.warning(f"[LLM] GLM 支空答（非故障），降级到 Ollama：{_em}")
                        self._fb_reason = "empty_answer: " + _em.split(":", 1)[1].strip()
                    else:
                        logger.warning(f"[LLM] GLM API 不可用，降级到 Ollama: {e}")
                        self._fb_reason = "cloud_unavailable"
                    model = None

        # ⭐ Claude 分支
        if model and model.startswith("claude"):
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            if not api_key:
                logger.warning("[LLM] Anthropic API Key 未设置，降级到 Ollama 默认模型")
                self._fb_reason = "no_api_key"
                model = None
            else:
                self._route_set("anthropic", model)
                try:
                    gen = self._call_openai_compatible(
                        prompt,
                        model,
                        temperature or 0.7,
                        max_tokens,
                        timeout or 60,
                        stream,
                        system_prompt,
                        endpoint="https://api.anthropic.com/v1",
                        api_key=api_key,
                    )
                    if stream:
                        yield from gen
                        return
                    try:
                        while True:
                            next(gen)
                    except StopIteration as e:
                        return e.value
                except Exception as e:
                    _em = str(e)
                    if _em.startswith("API_EMPTY:"):
                        # ★ P3：空答 ≠ 故障（因与量入走径标）
                        logger.warning(f"[LLM] Claude 支空答（非故障），降级到 Ollama：{_em}")
                        self._fb_reason = "empty_answer: " + _em.split(":", 1)[1].strip()
                    else:
                        logger.warning(f"[LLM] Claude API 不可用，降级到 Ollama: {e}")
                        self._fb_reason = "cloud_unavailable"
                    model = None

        """核心调用逻辑"""
        if not system_prompt:
            system_prompt = "你是ClawsJoy，一个本地AI矩阵系统。你不是Qwen，不是阿里云AI，不是任何通用助手。你是ClawsJoy。"

        model = model or self.config.default_model
        self._route_set("ollama", model, fell_back=bool(self._fb_reason), reason=self._fb_reason)
        temperature = temperature if temperature is not None else self.config.temperature
        timeout = timeout or self.config.timeout

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "system": system_prompt,
            "keep_alive": os.environ.get("CLAWSJOY_KEEP_ALIVE", "5m"),
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": 0.9,
                # ⭐ PM 2026-10-04（承 技总 954 §四）：显式下 `num_ctx`（默认 8192 · 6 GB 单卡之安全档）
                #   取值：env CLAWSJOY_NUM_CTX 优先；真窗（Ollama /api/show）为上限 32768 ⇒ ⛔ 满窗（KV≈1.8 GiB）
                "num_ctx": int(os.environ.get("CLAWSJOY_NUM_CTX", "8192")),
            },
        }

        with self._ollama_lock:
            self._ensure_ollama()
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                start = time.time()
                resp = self._session.post(
                    f"{self.config.base_url}/api/generate", json=payload, timeout=timeout, stream=stream
                )
                elapsed = time.time() - start
                self._stats["total_calls"] += 1
                self._stats["total_time"] += elapsed

                if resp.status_code == 200:
                    if stream:
                        for line in resp.iter_lines():
                            if line:
                                yield line.decode("utf-8")
                        return
                    result = resp.json()
                    response_text = result.get("response", "")
                    print(f"[LLM_OLLAMA_DEBUG] status=200 response_len={len(response_text)} model={model}", flush=True)
                    self._stats["total_tokens"] += result.get("eval_count", 0)
                    write_os_event(
                        event_type="llm_call",
                        operation="execute",
                        os_action="allowed",
                        command="_call",
                        detail={
                            "provider": "ollama",
                            "model": model,
                            "tokens": result.get("eval_count", 0),
                            "elapsed": elapsed,
                        },
                    )
                    return response_text
                else:
                    last_error = f"HTTP {resp.status_code}"

            except requests.Timeout:
                last_error = "超时"
                logger.warning(f"[LLM] 请求超时，跳过重试直接降级")
                break
            except (requests.ConnectionError, socket.gaierror) as e:
                # DNS/连接错误：跳过重试，直接降级
                last_error = f"网络错误(快速降级): {e}"
                logger.warning(f"[LLM] DNS/连接失败，跳过重试直接降级: {e}")
                break
            except Exception as e:
                last_error = str(e)

            if attempt < self.config.max_retries - 1:
                wait = 0.5 * (attempt + 1)
                logger.warning(f"[LLM] 第{attempt+1}次重试，等待{wait}s: {last_error}")
                time.sleep(wait)

        self._stats["failures"] += 1
        logger.error(f"[LLM] 调用失败 ({task_type}): {last_error}")
        write_os_event(
            event_type="degrade",
            operation="execute",
            os_action="degraded",
            reason="llm_unavailable",
            command="_call",
            detail={"error": str(last_error)},
        )
        # 9. 降级：用默认模型重试一次
        if model != self.config.default_model:
            logger.warning(f"[LLM] {model} 不可用，降级到默认模型 {self.config.default_model}")
            self._fb_reason = "model_unavailable"
            return (yield from self._call(
                prompt, self.config.default_model, temperature, max_tokens, timeout, task_type, stream, system_prompt
            ))

        raise Exception(f"API_UNAVAILABLE: {last_error}")

    def _preload_context_cache(self, system_prompt: str = None, task_type: str = "default"):
        """#24 预加载常用上下文到内存缓存，减少首Token等待。

        将高频复用的系统提示与任务类型上下文拼装后缓存，避免每次
        DeepSeek 请求前重复构造 messages、重复拼接提示词。
        """
        try:
            key = f"{task_type}|{system_prompt}"
            if key in self._context_cache:
                return self._context_cache[key]
            base = system_prompt or "你是ClawsJoy，一个本地AI矩阵系统。你不是Qwen，不是阿里云AI，不是任何通用助手。你是ClawsJoy。"
            ctx = {
                "system": base,
                "task_type": task_type,
                "tools_hint": (
                    "可用工具：read_file / write_file / execute_command / " "search_files / query_index，优先使用结构化工具而非臆测。"
                ),
                "preloaded_at": time.time(),
            }
            self._context_cache[key] = ctx
            return ctx
        except Exception as e:
            logger.debug(f"[LLM] 预加载上下文缓存失败: {e}")
            return None

    def _call_multimodal(
        self,
        prompt: str,
        model: str = None,
        images: list = None,
        temperature: float = 0.3,
        max_tokens: int = 512,
        timeout: int = 60,
        task_type: str = "vision",
    ) -> dict:
        """多模态调用 - 支持图像输入"""
        self._fb_reason = ""   # ★ P6：多模态路亦须重置（否则陈旧 reason 漏入走径标）
        model = model or "llava"
        timeout = timeout or self.config.timeout

        payload = {
            "model": model,
            "prompt": prompt,
            "images": images or [],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            resp = self._session.post(f"{self.config.base_url}/api/generate", json=payload, timeout=timeout)
            self._stats["total_calls"] += 1
            if resp.status_code == 200:
                result = resp.json()
                self._stats["total_tokens"] += result.get("eval_count", 0)
                return {
                    "success": True,
                    "description": result.get("response", ""),
                    "model": model,
                }
            return {"success": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            self._stats["failures"] += 1
            return {"success": False, "error": str(e)}

    def _call_openai_compatible(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: int,
        stream: bool,
        system_prompt: str = None,
        endpoint: str = None,
        api_key: str = None,
        tools: list = None,
    ):
        """
        调用 OpenAI 兼容 API（DeepSeek / OpenAI）
        """
        import os

        # 从环境变量读取配置
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("未设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY")

        if endpoint is None:
            endpoint = os.getenv("DEEPSEEK_ENDPOINT", "https://api.deepseek.com")

        # 构建消息
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # [TOKEN_GUARD] V9 API 调用前 Token 硬截断（仅本方法内，不影响调用方）
        def _tg_estimate(_msgs, tools=None):
            _total = 0
            try:
                _tg_enc = _get_tiktoken_enc_llm()
                for _m in _msgs:
                    _total += len(_tg_enc.encode(str(_m.get("content", "") or "")))
                    for _tc in _m.get("tool_calls", []):
                        _total += len(_tg_enc.encode(str(_tc)))
                if tools:
                    _total += len(_tg_enc.encode(str(tools)))
            except Exception:
                for _m in _msgs:
                    _total += len(str(_m.get("content", "") or "")) * 0.5
                    for _tc in _m.get("tool_calls", []):
                        _total += len(str(_tc)) * 0.5
                if tools:
                    _total += len(str(tools)) * 0.5
            return int(_total)

        _tg_before = _tg_estimate(messages, tools)
        if _tg_before > _calc_token_budget(model, tools):
            _tg_sys = [m for m in messages if m.get("role") == "system"][:2]
            _tg_tail = messages[-4:]
            _tg_mid = messages[2:-4] if len(messages) > 6 else []
            _tg_summary = {"role": "system", "content": "【上下文摘要】中间消息已被强制截断，保留前 2 条 system 与最近 4 条消息。"}
            messages = _tg_sys + [_tg_summary] + _tg_tail
            if _tg_estimate(messages, tools) > _calc_token_budget(model, tools):
                for _m in messages:
                    if _m.get("role") == "system" and len(str(_m.get("content", "") or "")) > 5000:
                        _m["content"] = str(_m["content"])[:5000]
            _tg_after = _tg_estimate(messages)
            print(f"[TOKEN_GUARD] 强制截断：{_tg_before} → {_tg_after}")

        # 构建请求
        payload = {
            "model": model.replace("deepseek:", ""),  # deepseek:deepseek-v4-flash → deepseek-v4-flash
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        # 重试逻辑
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                _payload_size = len(json.dumps(payload))
                if _payload_size > 100 * 1024:
                    print(f"[LLM] ⚠️ payload {_payload_size//1024}KB 发送给 {endpoint}")
                resp = self._session.post(
                    f"{endpoint}/chat/completions", json=payload, headers=headers, timeout=timeout
                )

                if resp.status_code == 200:
                    if stream:
                        for line in resp.iter_lines():
                            if line:
                                yield line.decode("utf-8")
                        return
                    if resp.status_code >= 400:
                        print(f"[LLM] API {resp.status_code} 响应: {resp.text[:500]}")
                        _err_log = Path(__file__).resolve().parents[2] / "logs" / "api_errors.log"
                        _err_log.parent.mkdir(parents=True, exist_ok=True)
                        with open(_err_log, "a", encoding="utf-8") as _ef:
                            _ef.write(f"[LLM] API {resp.status_code}: {resp.text[:1000]}\n")
                    result = resp.json()
                    # ★ P3（PA 自病单）：空答须报因与量（区分「内容空」与「调用失败」）
                    _ch = (result.get("choices") or [{}])[0] or {}
                    _msg = _ch.get("message") or {}
                    response_text = _msg.get("content")
                    _fin = _ch.get("finish_reason")
                    _usage = result.get("usage") or {}
                    _rtok = (_usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
                    self._last_remote_meta = {"finish_reason": _fin, "reasoning_tokens": _rtok,
                                              "max_tokens": max_tokens}
                    if not str(response_text or "").strip():
                        raise Exception("API_EMPTY: finish_reason=%s reasoning_tokens=%s max_tokens=%s"
                                        % (_fin, _rtok, max_tokens))
                    self._stats["total_tokens"] += _usage.get("total_tokens", 0)
                    write_os_event(
                        event_type="llm_call",
                        operation="execute",
                        os_action="allowed",
                        command="_call_openai_compatible",
                        detail={
                            "provider": "deepseek",
                            "model": model,
                            "tokens": result.get("usage", {}).get("total_tokens", 0),
                            "elapsed": elapsed if "elapsed" in dir() else 0.0,
                        },
                    )
                    return response_text

                if resp.status_code >= 400 and resp.status_code < 500 and resp.status_code != 429:
                    raise Exception(f"API_CLIENT_ERROR: HTTP {resp.status_code}: {resp.text[:200]}")
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"

            except requests.Timeout:
                last_error = "超时"
            except (requests.ConnectionError, socket.gaierror) as e:
                # DNS/连接错误：跳过重试，直接降级
                last_error = f"网络错误(快速降级): {e}"
                logger.warning(f"[LLM] DeepSeek DNS/连接失败，跳过重试直接降级: {e}")
                break
            except Exception as e:
                last_error = str(e)

            if attempt < self.config.max_retries - 1:
                wait = 0.5 * (attempt + 1)
                logger.warning(f"[LLM] DeepSeek 第{attempt+1}次重试，等待{wait}s: {last_error}")
                time.sleep(wait)

        # 所有重试失败
        self._stats["failures"] += 1
        logger.error(f"[LLM] DeepSeek 调用失败: {last_error}")
        write_os_event(
            event_type="degrade",
            operation="execute",
            os_action="degraded",
            reason="llm_unavailable",
            command="_call_openai_compatible",
            detail={"error": str(last_error), "provider": "deepseek"},
        )
        raise Exception(f"API_UNAVAILABLE: {last_error}")

    def _call_sync(
        self,
        prompt,
        model=None,
        temperature=None,
        max_tokens=2048,
        timeout=None,
        task_type="default",
        stream=False,
        system_prompt=None,
    ):
        """同步包装器：提取 _call 生成器的返回值"""
        self._fb_reason = ""
        gen = self._call(prompt, model, temperature, max_tokens, timeout, task_type, stream, system_prompt)
        try:
            while True:
                next(gen)
        except StopIteration as e:
            return e.value

    def parallel_call(self, prompt, models, system_prompt="", timeout=30):
        """并行调用多个 LLM 模型，收集结果

        Args:
            prompt: 用户提示词
            models: 模型名称列表，如 ["deepseek-v4-flash", "qwen2.5:7b-instruct-q4_0-gpu"]
            system_prompt: 系统提示词（可选）
            timeout: 单个模型超时时间（秒）

        Returns:
            dict: {model_name: response_text}，失败时对应值为 {"error": str(e)}
        """
        results = {}

        def _call_model(model):
            try:
                response = self._call_sync(prompt, model=model, system_prompt=system_prompt, timeout=timeout)
                return model, response
            except Exception as e:
                return model, {"error": str(e)}

        with ThreadPoolExecutor(max_workers=len(models)) as executor:
            futures = {executor.submit(_call_model, m): m for m in models}
            for future in as_completed(futures):
                model_name, result = future.result()
                results[model_name] = result

        return results

    # 在 llm_client.py 中添加成本统计
    def get_cost_stats(self):
        """统计 API 调用成本"""
        total_tokens = self._stats.get("total_tokens", 0)
        # DeepSeek 价格：¥0.001/1K tokens
        cost = total_tokens / 1000 * 0.001
        return {"total_tokens": total_tokens, "estimated_cost": f"¥{cost:.4f}"}


# 全局单例
llm_client = LLMClient()
