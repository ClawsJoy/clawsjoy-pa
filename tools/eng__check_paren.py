import re

with open("web/dashboard/workbench.html", encoding="utf-8") as f:
    html = f.read()

# Find JS content between script tags
m = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
if not m:
    print("No <script> tag found")
    exit(1)

js = m.group(1)
lines = js.split(chr(10))
print("JS lines:", len(lines))

# Track parens/braces with template-string awareness
depth_paren = 0
depth_brace = 0
in_tmpl = False
tmpl_brace_depth = 0

for i, line in enumerate(lines):
    j = 0
    while j < len(line):
        c = line[j]
        nc = line[j + 1] if j + 1 < len(line) else ""

        if c == chr(92):
            if in_tmpl or True:
                j += 2
                continue

        if c == "`":
            if not in_tmpl:
                in_tmpl = True
                tmpl_brace_depth = 0
            else:
                if tmpl_brace_depth == 0:
                    in_tmpl = False
            j += 1
            continue

        if in_tmpl and c == "$" and nc == "{":
            tmpl_brace_depth += 1
            j += 2
            continue
        if in_tmpl and c == "}":
            if tmpl_brace_depth > 0:
                tmpl_brace_depth -= 1
                j += 1
                continue

        if not in_tmpl or tmpl_brace_depth > 0:
            if c == "(":
                depth_paren += 1
            elif c == ")":
                depth_paren -= 1
                if depth_paren < 0:
                    print(f"Extra ) at JS L{i+1}")
                    depth_paren = 0
            elif c == "{":
                depth_brace += 1
            elif c == "}":
                depth_brace -= 1
                if depth_brace < 0:
                    print(f"Extra }} at JS L{i+1}")
                    depth_brace = 0
        j += 1

print(f"Final depth: paren={depth_paren}, brace={depth_brace}")
if depth_paren == 0 and depth_brace == 0:
    print("OK - balanced")
else:
    print(f"UNBALANCED: paren={depth_paren}, brace={depth_brace}")
