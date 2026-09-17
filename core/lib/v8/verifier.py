#!/usr/bin/env python3
"""Verifier v1.0 — 步骤结果验证器：AST 语法检查 + LLM 语义验证"""

import ast
import json
from typing import Dict, Any, Optional

import requests

from core.lib.unified_config import unified_config


class Verifier:
    """单例 Verifier — 验证步骤执行结果

    职责:
        1. 轻量验证：AST 语法检查（检测结果中是否含 Python 代码）
        2. 语义验证：用 LLM 对比执行输出与步骤目标
        3. 返回 {"passed": bool, "reason": str, "score": float}
    """

    _instance: Optional["Verifier"] = None

    def __new__(cls) -> "Verifier":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        _llm_endpoint = unified_config.get("llm.endpoint", "http://localhost:11434")
        self.ollama_url = f"{_llm_endpoint.rstrip('/')}/api/generate"
        self.model = unified_config.get(
            "llm.fast_model",
            unified_config.get("llm.default_model", "qwen2.5:7b"),
        )
        self.timeout = unified_config.get("llm.timeout", 30)

    # ----------------------------------------------------------
    # 公有接口
    # ----------------------------------------------------------

    def verify(self, step_result: str, step_goal: str, task_name: str = "", step_description: str = "", skill: str = "") -> Dict[str, Any]:
        """验证步骤执行结果

        Args:
            step_result: 步骤执行输出
            step_goal: 步骤目标描述

        Returns:
            {"passed": bool, "reason": str, "score": float}
        """
        reason_parts: list[str] = []
        score = 1.0

        # 1. AST 语法检查
        ast_result = self._check_ast(step_result)
        if not ast_result["passed"]:
            reason_parts.append(f"[AST] {ast_result['reason']}")
            score *= 0.5

        # 2. LLM 语义验证
        llm_result = self._check_semantic(step_result, step_goal, task_name, step_description, skill)
        reason_parts.append(f"[语义] {llm_result['reason']}")
        score *= llm_result["score"]

        passed = score >= 0.4
        reason = "；".join(reason_parts) if reason_parts else "验证通过"

        return {
            "passed": passed,
            "reason": reason,
            "score": round(score, 2),
        }

    # ----------------------------------------------------------
    # AST 语法检查
    # ----------------------------------------------------------

    @staticmethod
    def _check_ast(text: str) -> Dict[str, Any]:
        """检测文本中是否包含 Python 代码，并检查语法

        策略:
            - 以 ```python / ``` 包裹的代码块
            - 或缩进一致的 Python 语句（含 import/def/class/if/for 等关键词）
        """
        # 提取代码块
        code_blocks = Verifier._extract_code_blocks(text)

        if not code_blocks:
            return {"passed": True, "reason": "未检测到 Python 代码，跳过 AST 检查"}

        errors = []
        for idx, block in enumerate(code_blocks):
            try:
                ast.parse(block)
            except SyntaxError as e:
                errors.append(f"代码块 #{idx} 语法错误: {e}")

        if errors:
            return {"passed": False, "reason": " | ".join(errors)}
        return {"passed": True, "reason": f"{len(code_blocks)} 个代码块语法检查通过"}

    @staticmethod
    def _extract_code_blocks(text: str) -> list[str]:
        """从文本中提取 Python 代码块"""
        import re

        blocks: list[str] = []

        # 1. 匹配 ```python ... ``` 代码块
        fenced = re.findall(r"```(?:python|py)\n(.*?)```", text, re.DOTALL)
        blocks.extend(fenced)

        # 2. 匹配行首缩进的 Python 语句（以 import/def/class/if/for/while/with/try 开头）
        lines = text.split("\n")
        current_block: list[str] = []
        in_block = False
        for line in lines:
            stripped = line.strip()
            if (
                not in_block
                and stripped
                and not stripped.startswith("#")
                and not stripped.startswith("\"\"\"")
                and not stripped.startswith("'")
                and (
                    stripped.startswith("import ")
                    or stripped.startswith("from ")
                    or stripped.startswith("def ")
                    or stripped.startswith("class ")
                    or stripped.startswith("if ")
                    or stripped.startswith("for ")
                    or stripped.startswith("while ")
                    or stripped.startswith("with ")
                    or stripped.startswith("try:")
                    or stripped.startswith("except")
                    or stripped.startswith("finally:")
                )
            ):
                in_block = True
                current_block.append(line)
            elif in_block:
                if stripped == "" or line.startswith(" "):
                    current_block.append(line)
                else:
                    if current_block:
                        blocks.append("\n".join(current_block))
                        current_block = []
                    in_block = False

        if current_block:
            blocks.append("\n".join(current_block))

        return blocks

    # ----------------------------------------------------------
    # LLM 语义验证
    # ----------------------------------------------------------

    def _check_semantic(self, step_result: str, step_goal: str, task_name: str = "", step_description: str = "", skill: str = "") -> Dict[str, Any]:
        """用 LLM 对比步骤结果与目标，评估语义一致性"""
        prompt = f"""你是一个严格但公平的执行结果验证器。请评估以下步骤的输出是否达到了步骤目标。

## 步骤目标
{step_goal}

## 步骤输出
{step_result}

请从以下三个维度打分（0.0 ~ 1.0）：
1. **完整性**：输出是否完整覆盖了目标的所有要求
2. **正确性**：输出中是否有明显错误或偏差
3. **相关性**：输出是否紧密围绕目标，没有离题

请只返回 JSON 格式（不要 markdown 包裹）：
{{"passed": true/false, "reason": "一句话说明", "score": 0.0~1.0}}

注意：score >= 0.4 时 passed 应为 true，否则为 false。"""

        try:
            resp = requests.post(
                self.ollama_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("response", "")
            # 清理可能的 markdown 包裹
            cleaned = self._extract_json(raw)
            result = json.loads(cleaned)
            return {
                "passed": result.get("passed", False),
                "reason": result.get("reason", "LLM 未返回有效理由"),
                "score": float(result.get("score", 0.0)),
            }
        except Exception as e:
            # LLM 不可用时降级：使用简单的关键词匹配
            return self._fallback_check(
                step_result, step_goal, str(e),
                task_name=task_name,
                step_description=step_description,
                skill=skill,
            )

    @staticmethod
    def _extract_json(text: str) -> str:
        """从文本中提取 JSON 内容"""
        import re

        # 去掉 ```json ... ``` 包裹
        cleaned = re.sub(r"```(?:json)?\n?", "", text).strip()
        # 找到第一个 { 和最后一个 }
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            return cleaned[start : end + 1]
        return cleaned

    @staticmethod
    def _fallback_check(
        step_result: str,
        step_goal: str,
        error: str,
        task_name: str = "",
        step_description: str = "",
        skill: str = "",
    ) -> Dict[str, Any]:
        """LLM 不可用时的降级验证：关键词匹配

        关键词来源：step_goal + task_name + step_description + skill 拼接后提取；
        中文按常见标点/连词切分，英文按 camelCase/snake_case 拆分；
        task_name 中的词权重为 2，其余来源词权重为 1。
        """
        import re

        result_lower = step_result.lower()
        # 中文切分：常见标点 + 连词（作为分隔符，不计入关键词）
        cn_delimiters = [
            "的", "了", "是", "在", "和", "与", "请", "把", "将", "对", "进行", "需要",
        ]
        punct_pattern = re.compile(r"[，。！？、；：,.!?;:()（）\[\]【】\"\'\s]+")

        def extract_keywords(text: str) -> set:
            """提取关键词：中文按标点/连词切分，英文按 camelCase/snake_case 拆分"""
            if not text:
                return set()
            # camelCase：大写字母前切开（须在 lower 之前，保留大小写边界）
            t = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
            t = t.lower()
            for d in cn_delimiters:
                t = t.replace(d, " ")
            t = punct_pattern.sub(" ", t)
            kws = set()
            for token in t.split():
                for part in token.split("_"):  # snake_case
                    part = part.strip()
                    if part:
                        kws.add(part)
            return kws

        # 关键词来源及权重（task_name 权重 2，其余 1）
        sources = [
            (step_goal, 1),
            (task_name, 2),
            (step_description, 1),
            (skill, 1),
        ]
        stop_words = {
            "a", "an", "the",
            "to", "of", "in", "for", "on", "at", "by", "with",
        }
        keyword_weights: Dict[str, int] = {}
        for text, weight in sources:
            for kw in extract_keywords(text):
                if kw in stop_words:
                    continue
                keyword_weights[kw] = keyword_weights.get(kw, 0) + weight

        if not keyword_weights:
            return {"passed": True, "reason": f"LLM 不可用，降级验证跳过（{error}）", "score": 0.8}

        total_weight = sum(keyword_weights.values())
        matched_count = sum(1 for kw in keyword_weights if kw in result_lower)
        matched_weight = sum(w for kw, w in keyword_weights.items() if kw in result_lower)
        ratio = matched_weight / total_weight
        # 目标关键词 <= 2 个时，至少命中 1 个即通过；否则 ratio >= 0.1 算通过
        if len(keyword_weights) <= 2:
            passed = matched_count >= 1
        else:
            passed = ratio >= 0.1
        return {
            "passed": passed,
            "reason": (
                f"LLM 不可用，降级关键词匹配: "
                f"目标关键词 {matched_count}/{len(keyword_weights)} 命中 "
                f"(加权 {matched_weight}/{total_weight}, {ratio:.0%}) — "
                f"{'通过' if passed else '未通过'}"
            ),
            "score": round(max(0.2, ratio), 2),
        }
