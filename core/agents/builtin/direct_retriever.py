#!/usr/bin/env python3
"""Direct Retriever - Direct Retriever 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

#!/usr/bin/env python3
"""直接检索 Agent - 不依赖 LLM 总结"""

import sys

from core.lib.memory_vector import vector_memory


class DirectRetriever:
    VERSION = "5.7.0"

    def __init__(self):
        pass

    def search(self, query: str) -> str:
        """直接搜索并返回内容"""
        results = vector_memory.search(query, n=5)

        if not results:
            return "没有找到相关信息"

        output = []
        for r in results:
            text = r.get("text", "")
            score = r.get("similarity", 0)
            if score > 0.3 and len(text) > 50:
                output.append(f"[相似度: {score:.2f}]\n{text[:500]}")

        if output:
            return "\n\n---\n\n".join(output)
        return "没有找到匹配的内容"


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-q", "--query", required=True)
    args = parser.parse_args()

    retriever = DirectRetriever()
    result = retriever.search(args.query)
    print(result)


if __name__ == "__main__":
    main()
