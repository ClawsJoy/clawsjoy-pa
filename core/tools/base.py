"""工具插件基类 — 统一接口（#238 + #213）"""


class ToolPlugin:
    """所有工具插件的基类

    接口：
    - name: 工具名
    - execute(args, ctx): 执行，返回结构化结果
    - validate(args): 参数校验
    - quota_consumed(): 配额消耗数
    """
    name: str = ""
    quota: int = 10

    def execute(self, args: dict, ctx) -> dict:
        raise NotImplementedError

    def validate(self, args: dict) -> bool:
        return True

    def quota_consumed(self) -> int:
        return 1
