#!/usr/bin/env python3
"""硬件探测器 - 自动检测GPU/NPU/CPU/内存，推荐最优配置"""

import os
import platform
import subprocess

from core.lib import _proc as _proc  # ⭐ 子进程唯一出口（窗隐）
from pathlib import Path
from typing import Dict, List, Optional


class HardwareProbe:
    """硬件探测器"""

    def __init__(self):
        self._info: Dict = {}
        self._probe()

    def _probe(self):
        self._info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "arch": platform.machine(),
            "hostname": platform.node(),
            "cpu": self._probe_cpu(),
            "memory": self._probe_memory(),
            "gpu": self._probe_gpu(),
            "disk": self._probe_disk(),
        }
        self._info["recommended"] = self._recommend()

    def _probe_cpu(self) -> Dict:
        try:
            import psutil

            return {
                "model": platform.processor() or "Unknown",
                "cores": psutil.cpu_count(logical=False),
                "threads": psutil.cpu_count(logical=True),
                "freq_mhz": psutil.cpu_freq().max if psutil.cpu_freq() else 0,
            }
        except Exception:
            return {"model": platform.processor(), "cores": os.cpu_count()}

    def _probe_memory(self) -> Dict:
        try:
            import psutil

            mem = psutil.virtual_memory()
            return {
                "total_gb": round(mem.total / (1024**3), 1),
                "available_gb": round(mem.available / (1024**3), 1),
                "percent_used": mem.percent,
            }
        except Exception:
            return {"total_gb": 0, "available_gb": 0}

    def _probe_gpu(self) -> Dict:
        gpus = []

        # NVIDIA GPU
        try:
            result = _proc.run_hidden(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,memory.free,memory.used",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5, encoding="utf-8", errors="replace"
            )
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split("\n"):
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 3:
                        gpus.append(
                            {
                                "vendor": "NVIDIA",
                                "name": parts[0],
                                "memory_total_mb": int(parts[1]) if len(parts) > 1 else 0,
                                "memory_free_mb": int(parts[2]) if len(parts) > 2 else 0,
                            }
                        )
        except Exception:
            pass

        # Apple Silicon / Metal
        if not gpus and platform.system() == "Darwin":
            try:
                result = _proc.run_hidden(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True, encoding="utf-8", errors="replace")
                if "Apple" in result.stdout:
                    gpus.append(
                        {
                            "vendor": "Apple",
                            "name": "Apple Silicon (Integrated)",
                            "memory_total_mb": int(self._info.get("memory", {}).get("total_gb", 0) * 1024 * 0.7),
                            "memory_free_mb": int(self._info.get("memory", {}).get("available_gb", 0) * 1024 * 0.5),
                        }
                    )
            except Exception:
                pass

        # Intel/AMD集成显卡（Linux）
        if not gpus and platform.system() == "Linux":
            try:
                result = _proc.run_hidden(["lspci"], capture_output=True, text=True, encoding="utf-8", errors="replace")
                for line in result.stdout.split("\n"):
                    if "VGA" in line or "3D" in line:
                        gpus.append(
                            {
                                "vendor": "Intel/AMD" if "Intel" in line or "AMD" in line else "Unknown",
                                "name": line.split(":")[-1].strip(),
                                "memory_total_mb": 0,
                                "memory_free_mb": 0,
                            }
                        )
            except Exception:
                pass

        return {
            "count": len(gpus),
            "devices": gpus,
            "has_gpu": len(gpus) > 0,
        }

    def _probe_disk(self) -> Dict:
        try:
            import psutil

            disk = psutil.disk_usage("/")
            return {
                "total_gb": round(disk.total / (1024**3), 1),
                "free_gb": round(disk.free / (1024**3), 1),
            }
        except Exception:
            return {"total_gb": 0, "free_gb": 0}

    def _recommend(self) -> Dict:
        """根据硬件推荐模型配置"""
        mem_gb = self._info.get("memory", {}).get("total_gb", 0)
        has_gpu = self._info.get("gpu", {}).get("has_gpu", False)
        gpu_mem_mb = 0
        for g in self._info.get("gpu", {}).get("devices", []):
            gpu_mem_mb = max(gpu_mem_mb, g.get("memory_total_mb", 0))

        # 推荐配置
        if has_gpu and gpu_mem_mb >= 8000:
            tier = "ultra"
            models = ["qwen2.5:7b-instruct-q4_0-gpu", "qwen2.5:7b-instruct-q4_0-gpu", "codellama:7b", "llava:latest"]
            max_concurrent = 10
        elif has_gpu and gpu_mem_mb >= 4000:
            tier = "high"
            models = ["qwen2.5:7b-instruct-q4_0-gpu", "qwen2.5:7b-instruct-q4_0-gpu", "codellama:7b"]
            max_concurrent = 5
        elif mem_gb >= 16:
            tier = "medium"
            models = ["qwen2.5:7b-instruct-q4_0-gpu", "qwen2:1.5b-instruct"]
            max_concurrent = 3
        elif mem_gb >= 8:
            tier = "basic"
            models = ["qwen2:1.5b-instruct"]
            max_concurrent = 1
        else:
            tier = "minimal"
            models = []
            max_concurrent = 0

        return {
            "tier": tier,
            "models": models,
            "max_concurrent_agents": max_concurrent,
            "gpu_available": has_gpu,
            "offline_capable": len(models) > 0,
        }

    def report(self) -> Dict:
        return self._info

    def print_report(self):
        info = self._info
        rec = info["recommended"]
        gpu = info["gpu"]

        print("=" * 60)
        print("  ClawsJoy 硬件检测报告")
        print("=" * 60)
        print(f"  系统: {info['os']} {info['os_version'][:30]}")
        print(f"  CPU:  {info['cpu'].get('model','?')} ({info['cpu'].get('threads','?')}线程)")
        print(f"  内存: {info['memory'].get('total_gb','?')}GB (可用{info['memory'].get('available_gb','?')}GB)")

        if gpu["devices"]:
            for g in gpu["devices"]:
                print(f"  GPU:  {g['vendor']} {g['name']} ({g.get('memory_total_mb','?')}MB)")
        else:
            print(f"  GPU:  未检测到独立GPU")

        print(f"  磁盘: {info['disk'].get('total_gb','?')}GB (可用{info['disk'].get('free_gb','?')}GB)")
        print(f"  ---")
        print(f"  推荐配置: {rec['tier'].upper()}")
        print(f"  推荐模型: {', '.join(rec['models']) if rec['models'] else '无(内存不足)'}")
        print(f"  最大并发: {rec['max_concurrent_agents']}个Agent")
        print("=" * 60)


hardware_probe = HardwareProbe()


if __name__ == "__main__":
    hardware_probe.print_report()
