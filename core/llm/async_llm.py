#!/usr/bin/env python3
"""Async Llm - 基于统一LLM客户端的异步封装

@version: 5.1.0
@author: ClawsJoy
@date: 2026-6-21
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from core.lib.llm_client import llm_client
from core.lib.config_helper import get_llm_model


class AsyncLLMClient:
    """异步 LLM 客户端 - 连接池 + 并发控制"""

    def __init__(self, max_connections: int = 10):
        self.llm = llm_client
        self.model = get_llm_model(fast=True)
        self.executor = ThreadPoolExecutor(max_workers=max_connections)
        self._semaphore = asyncio.Semaphore(max_connections)
        self._stats = {"total": 0, "success": 0, "timeout": 0, "error": 0}

    async def generate(self, prompt: str, timeout: int = 30,
                       temperature: float = 0.7, max_tokens: int = 2048,
                       task_type: str = "default") -> str:
        """异步生成（使用信号量控制并发）"""
        async with self._semaphore:
            self._stats["total"] += 1
            loop = asyncio.get_event_loop()

            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        self.executor,
                        lambda: self.llm.generate(
                            prompt=prompt,
                            model=self.model,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            timeout=timeout,
                            task_type=task_type
                        )
                    ),
                    timeout=timeout + 5
                )
                if result:
                    self._stats["success"] += 1
                    return result
                else:
                    self._stats["error"] += 1
                    return "服务返回空响应"
            except asyncio.TimeoutError:
                self._stats["timeout"] += 1
                return "请求超时，请稍后重试"
            except Exception as e:
                self._stats["error"] += 1
                print(f"LLM 异步调用失败: {e}")
                return "服务暂时不可用"

    async def generate_batch(self, prompts: list, **kwargs) -> list:
        """批量异步生成"""
        tasks = [self.generate(p, **kwargs) for p in prompts]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def generate_with_priority(self, prompts: list,
                                      priorities: list = None) -> list:
        """按优先级异步生成"""
        if not priorities:
            return await self.generate_batch(prompts)

        # 按优先级排序
        paired = sorted(zip(prompts, priorities), key=lambda x: x[1], reverse=True)
        sorted_prompts = [p for p, _ in paired]
        return await self.generate_batch(sorted_prompts)

    def generate_sync(self, prompt: str, timeout: int = 30, **kwargs) -> str:
        """同步包装（兼容旧接口）"""
        try:
            return self.llm.generate(
                prompt=prompt,
                model=self.model,
                timeout=timeout,
                **kwargs
            )
        except Exception as e:
            print(f"LLM 同步调用失败: {e}")
            return "服务暂时不可用"

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            **self._stats,
            "model": self.model,
            "success_rate": (
                self._stats["success"] / max(self._stats["total"], 1)
            ),
        }

    async def close(self):
        """关闭资源"""
        self.executor.shutdown(wait=True)


# 全局实例
async_llm = AsyncLLMClient(max_connections=10)
