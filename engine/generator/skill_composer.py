"""技能组合链 - 智能组合多个原子技能"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ChainType(Enum):
    SEQUENTIAL = "sequential"  # 顺序执行
    PARALLEL = "parallel"  # 并行执行
    CONDITIONAL = "conditional"  # 条件执行
    LOOP = "loop"  # 循环执行


@dataclass
class ChainStep:
    """组合链步骤"""

    skill: str
    params: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None
    output_key: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)


@dataclass
class SkillChain:
    """技能组合链"""

    name: str
    description: str
    steps: List[ChainStep]
    chain_type: ChainType = ChainType.SEQUENTIAL
    created_at: str = ""


class SkillComposer:
    """技能组合器 - 智能组合原子技能"""

    def __init__(self):
        self.chains: Dict[str, SkillChain] = {}
        self._load_default_chains()
        print("🔗 技能组合器已初始化")

    def _load_default_chains(self):
        """加载默认组合链"""
        # 视频制作链
        video_chain = SkillChain(
            name="video_creation",
            description="完整的视频制作流程",
            steps=[
                ChainStep(
                    skill="script_generator",
                    params={"topic": "topic"},
                    output_key="script",
                ),
                ChainStep(
                    skill="audio_generator",
                    params={"text": "{{script}}"},
                    output_key="audio",
                ),
                ChainStep(
                    skill="video_composer",
                    params={"audio": "{{audio}}", "images": "images"},
                    output_key="video",
                ),
                ChainStep(
                    skill="video_uploader",
                    params={"video": "{{video}}"},
                    output_key="url",
                ),
            ],
            chain_type=ChainType.SEQUENTIAL,
        )
        self.chains["video_creation"] = video_chain

        # 数据分析链
        analysis_chain = SkillChain(
            name="data_analysis",
            description="数据分析处理流程",
            steps=[
                ChainStep(
                    skill="data_collector",
                    params={"source": "source"},
                    output_key="raw_data",
                ),
                ChainStep(
                    skill="data_cleaner",
                    params={"data": "{{raw_data}}"},
                    output_key="clean_data",
                ),
                ChainStep(
                    skill="data_analyzer",
                    params={"data": "{{clean_data}}"},
                    output_key="analysis",
                ),
                ChainStep(
                    skill="report_generator",
                    params={"analysis": "{{analysis}}"},
                    output_key="report",
                ),
            ],
        )
        self.chains["data_analysis"] = analysis_chain

        # 翻译链
        translate_chain = SkillChain(
            name="translate_pipeline",
            description="多语言翻译流程",
            steps=[
                ChainStep(
                    skill="language_detector",
                    params={"text": "text"},
                    output_key="lang",
                ),
                ChainStep(
                    skill="translator",
                    params={"text": "text", "target": "en"},
                    output_key="en_text",
                ),
                ChainStep(
                    skill="translator",
                    params={"text": "{{en_text}}", "target": "zh"},
                    output_key="zh_text",
                ),
            ],
        )
        self.chains["translate_pipeline"] = translate_chain

    def create_chain(
        self, name: str, description: str, steps: List[Dict]
    ) -> SkillChain:
        """创建组合链"""
        chain_steps = []
        for step in steps:
            chain_steps.append(
                ChainStep(
                    skill=step["skill"],
                    params=step.get("params", {}),
                    condition=step.get("condition"),
                    output_key=step.get("output_key"),
                    depends_on=step.get("depends_on", []),
                )
            )

        chain = SkillChain(name=name, description=description, steps=chain_steps)
        self.chains[name] = chain
        return chain

    def execute_chain(
        self, chain_name: str, initial_params: Dict, skill_executor
    ) -> Dict:
        """执行组合链"""
        if chain_name not in self.chains:
            return {"error": f"组合链 {chain_name} 不存在"}

        chain = self.chains[chain_name]
        context = initial_params.copy()
        results = {}

        for step in chain.steps:
            # 准备参数
            params = self._prepare_params(step.params, context)

            # 检查条件
            if step.condition and not self._check_condition(step.condition, context):
                continue

            # 执行技能
            result = skill_executor(step.skill, params)
            results[step.skill] = result

            # 保存输出
            if step.output_key and result.get("success"):
                context[step.output_key] = result.get("result", result)

        return {
            "success": True,
            "chain": chain_name,
            "results": results,
            "context": context,
        }

    def _prepare_params(self, params: Dict, context: Dict) -> Dict:
        """准备参数（替换模板变量）"""
        import re

        prepared = {}
        for key, value in params.items():
            if isinstance(value, str):
                # 替换 {{variable}} 格式
                matches = re.findall(r"\{\{(\w+)\}\}", value)
                for match in matches:
                    if match in context:
                        value = value.replace(f"{{{{{match}}}}}", str(context[match]))
            prepared[key] = value
        return prepared

    def _check_condition(self, condition: str, context: Dict) -> bool:
        """检查条件"""
        try:
            # 简单的条件评估
            return eval(condition, {"__builtins__": {}}, context)
        except Exception as e:
            return True

    def list_chains(self) -> List[str]:
        """列出所有组合链"""
        return list(self.chains.keys())

    def get_chain(self, name: str) -> Optional[SkillChain]:
        """获取组合链"""
        return self.chains.get(name)


skill_composer = SkillComposer()
