import re

with open("web/dashboard/workbench.html", "r", encoding="utf-8") as f:
    html = f.read()

start_idx = html.find("<script>")
end_idx = html.find("</script>", start_idx)
js_code = html[start_idx + len("<script>") : end_idx]
lines = js_code.split("\n")

prefix = html[:start_idx]
prefix_lines = prefix.count("\n")

print("=" * 70)
print("  JavaScript 深度分析报告")
print("=" * 70)
print(f"  JS 代码总行数: {len(lines)}")
print(f"  <script> 标签位于 HTML 第 {prefix_lines + 1} 行")
print(f"  JS 内容从 HTML 第 {prefix_lines + 2} 行开始")
print()

# 括号平衡检查
print("-" * 70)
print("  1. 括号平衡检查")
print("-" * 70)
stack = []
errors = []
for i, line in enumerate(lines):
    js_line = i + 1
    html_line = prefix_lines + 1 + js_line
    in_string = False
    string_char = None
    in_regex = False
    j = 0
    while j < len(line):
        ch = line[j]
        if ch in "\"'" and not in_regex:
            if not in_string:
                in_string = True
                string_char = ch
            elif ch == string_char and (j == 0 or line[j - 1] != "\\"):
                in_string = False
            j += 1
            continue
        if in_string:
            j += 1
            continue
        if ch == "/" and j + 1 < len(line):
            if line[j + 1] == "/":
                break
            if line[j + 1] == "*":
                j += 2
                while j < len(line):
                    if line[j] == "*" and j + 1 < len(line) and line[j + 1] == "/":
                        j += 2
                        break
                    j += 1
                continue
        if ch in "({[":
            stack.append((ch, html_line, j))
        elif ch in ")}]":
            if not stack:
                errors.append(f"  额外闭合 {ch} 位于 HTML L{html_line}: {line[max(0,j-20):j+20]}")
            else:
                open_ch, open_line, _ = stack.pop()
                expected = {"(": ")", "{": "}", "[": "]"}[open_ch]
                if ch != expected:
                    errors.append(f"  括号不匹配: {open_ch} (L{open_line}) vs {ch} (L{html_line})")
        j += 1

if not stack and not errors:
    print("  ✓ 所有括号平衡")
else:
    for e in errors:
        print(e)
    for ch, line_num, pos in stack:
        print(f"  未闭合 {ch} 位于 HTML L{line_num}")

print()
# 缩进一致性检查
print("-" * 70)
print("  2. 缩进一致性检查")
print("-" * 70)
indent_issues = 0
for i, line in enumerate(lines):
    if not line.strip() or line.strip().startswith("//") or line.strip().startswith("/*"):
        continue
    leading = len(line) - len(line.lstrip())
    if leading % 2 != 0:
        indent_issues += 1
        if indent_issues <= 20:
            print(f"  非2倍数缩进: L{prefix_lines+1+i+1} ({leading}空格)")

if indent_issues == 0:
    print("  ✓ 缩进一致")
else:
    print(f"  共 {indent_issues} 处缩进问题")

print()
# 行尾分号检查（非JSX）
print("-" * 70)
print("  3. 行尾分号检查")
print("-" * 70)
semi_missing = 0
for i, line in enumerate(lines):
    stripped = line.strip()
    if not stripped:
        continue
    if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
        continue
    if stripped.endswith("{") or stripped.endswith("}") or stripped.endswith(";"):
        continue
    if stripped.startswith("if") or stripped.startswith("else") or stripped.startswith("for"):
        continue
    if stripped.startswith("function") or stripped.startswith("var ") or stripped.startswith("let "):
        continue
    if stripped.startswith("const ") or stripped.startswith("class ") or stripped.startswith("import "):
        continue
    if stripped.startswith("export ") or stripped.startswith("return ") or stripped.startswith("throw "):
        continue
    if stripped.startswith("switch") or stripped.startswith("case ") or stripped.startswith("default"):
        continue
    if stripped.startswith("try") or stripped.startswith("catch") or stripped.startswith("finally"):
        continue
    if stripped.startswith("//"):
        continue
    semi_missing += 1
    if semi_missing <= 20:
        print(f"  L{prefix_lines+1+i+1}: {stripped[:60]}")

if semi_missing == 0:
    print("  ✓ 没有缺少分号")
else:
    print(f"  共 {semi_missing} 处可能缺少分号")

print()
print("=" * 70)
print("  报告完毕")
print("=" * 70)
