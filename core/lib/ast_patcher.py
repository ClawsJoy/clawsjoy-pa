"""AST 补丁工具：解析 Python 文件，替换指定函数后写回。"""

import ast
from typing import Dict, List


def replace_function(filepath: str, function_name: str, new_code: str) -> dict:
    """读取文件 → ast.parse → 找到 function_name → 用 new_code 替换 → ast.unparse → 写回。

    成功返回 {"success": True, "function": function_name}
    函数不存在返回 {"success": False, "error": "函数未找到"}
    """
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)

    target = None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            target = node
            break

    if target is None:
        return {"success": False, "error": "函数未找到"}

    new_tree = ast.parse(new_code)
    replacement = None
    for node in new_tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            replacement = node
            break

    if replacement is None:
        return {"success": False, "error": "新代码中未找到函数定义"}

    if not replacement.decorator_list and target.decorator_list:
        replacement.decorator_list = target.decorator_list

    for i, node in enumerate(tree.body):
        if node is target:
            tree.body[i] = replacement
            break

    new_source = ast.unparse(tree)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_source)

    return {"success": True, "function": function_name}


def get_function_names(filepath: str) -> List[str]:
    """返回文件中所有顶级函数名列表。"""
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)

    names = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.append(node.name)

    return names
