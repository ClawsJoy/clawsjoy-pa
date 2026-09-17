"""从 pyc 输出 dis 指令"""
import dis
import marshal
import sys

pyc_path = "clawsjoy_dev/__pycache__/agent_gateway_enhanced.cpython-313.pyc"

with open(pyc_path, "rb") as f:
    f.read(16)
    code = marshal.load(f)

lines = []


def walk(co, depth=0, seen=None):
    if seen is None:
        seen = set()
    if id(co) in seen:
        return
    seen.add(id(co))
    p = "  " * depth
    lines.append(f"{p}--- {co.co_name} (L{co.co_firstlineno}) ---")
    try:
        for instr in dis.get_instructions(co):
            arg = f" {instr.argrepr}" if instr.argrepr else ""
            lines.append(f'{p}  L{instr.starts_line or "?"}: {instr.opname}{arg}')
    except Exception as e:
        lines.append(f"{p}  [err: {e}]")
    lines.append("")
    for c in co.co_consts:
        if hasattr(c, "co_code"):
            walk(c, depth + 1, seen)


walk(code)
with open("clawsjoy_dev/_dis_output.txt", "w", encoding="utf-8") as f:
    f.write(
        "\
".join(
            lines
        )
    )
print(f"Done: {len(lines)} lines")
