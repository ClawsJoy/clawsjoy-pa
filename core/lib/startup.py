#!/usr/bin/env python3
"""系统启动器 - 后台预热+健康检查"""

import threading
import time
import sys
from pathlib import Path


class StartupManager:
    """系统启动管理器"""
    
    def __init__(self):
        self._ready = False
        self._progress = 0
        self._status = "initializing"
        self._errors = []
    
    def start(self):
        """启动系统（异步预热）"""
        threading.Thread(target=self._startup_sequence, daemon=True).start()
    
    def _startup_sequence(self):
        """启动序列"""
        steps = [
            ("硬件检测", self._step_hardware),
            ("LLM就绪检查", self._step_llm),
            ("Agent池预热", self._step_agent_pool),
            ("联邦知识加载", self._step_federated),
            ("就绪", lambda: None),
        ]
        
        for i, (name, func) in enumerate(steps):
            self._status = name
            self._progress = int(i / len(steps) * 100)
            try:
                func()
            except Exception as e:
                self._errors.append(f"{name}: {e}")
        
        self._ready = True
        self._progress = 100
        self._status = "ready"
        print("✅ ClawsJoy 系统就绪")
    
    def _step_hardware(self):
        from core.lib.hardware_probe import hardware_probe
        rec = hardware_probe.report()["recommended"]
        print(f"  硬件: {rec['tier'].upper()} | 最大{rec['max_concurrent_agents']}并发")
    
    def _step_llm(self):
        from core.lib.llm_client import llm_client
        result = llm_client.generate("ping", max_tokens=1, timeout=10)
        if result is not None:
            print("  LLM: 就绪")
        else:
            raise RuntimeError("LLM服务不可用")
    
    def _step_agent_pool(self):
        from core.agents.wisdom.wisdom_factory import wisdom_factory
        stats = wisdom_factory.get_stats()
        print(f"  Agent池: {stats.get('registry_stats', {}).get('total', '?')}个实例就绪")
    
    def _step_federated(self):
        from core.lib.federated_bus import federated_bus
        stats = federated_bus.get_stats()
        print(f"  联邦: {stats['knowledge_files']}文件, {stats['total_entries']}条知识")
    
    @property
    def ready(self) -> bool:
        return self._ready
    
    def status(self) -> dict:
        return {
            "ready": self._ready,
            "progress": self._progress,
            "status": self._status,
            "errors": self._errors,
        }


startup_manager = StartupManager()
