import re

path = "agent_gateway_enhanced.py"
with open(path, "r") as f:
    content = f.read()

old1 = """    if not command or not cmd_name:
        _is_heredoc = \\\\\\"<< 'PYEOF'\\\\\\" in command or '<< \\\\\\"PYEOF\\\\\\"' in command or \\\\\\"<< 'EOF'\\\\\\" in command
        _sandbox_note = None
        if _is_heredoc and (\\\\\\"subprocess\\\\\\" in command or \\\\\\"os.system\\\\\\" in command or \\\\\\"popen\\\\\\" in command.lower()):
            _sandbox_note = \\\\\\"heredoc 内 subprocess 可执行任意命令\\\\\\"
        print(f\\\\\\"[HEREDOC-DETECT] _is_heredoc={_is_heredoc}, cmd[:150]={command[:150]}\\\\\\", flush=True)
        _log.getLogger('werkzeug').info(f'[EXEC_DEBUG] command为空或cmd_name为空: command={repr(command[:200])}, raw_keys={list(data.keys())}')"""

new1 = """    if not command or not cmd_name:
        print(f\\\\\\"[HEREDOC-DETECT] command为空或cmd_name为空: cmd_name={cmd_name}, cmd[:150]={command[:150]}\\\\\\", flush=True)
        _log.getLogger('werkzeug').info(f'[EXEC_DEBUG] command为空或cmd_name为空: command={repr(command[:200])}, raw_keys={list(data.keys())}')"""

if old1 in content:
    content = content.replace(old1, new1, 1)
    print("Change 1 applied successfully")
else:
    print("Change 1: pattern not found!")

old2 = """            if _sandbox_note or _sandbox_note_sync:
                _result[\\\\\\"_sandbox_note\\\\\\"] = _sandbox_note or _sandbox_note_sync"""

new2 = """            if _sandbox_note_sync:
                _result[\\\\\\"_sandbox_note\\\\\\"] = _sandbox_note_sync"""

if old2 in content:
    content = content.replace(old2, new2, 1)
    print("Change 2 applied successfully")
else:
    print("Change 2: pattern not found!")

with open(path, "w") as f:
    f.write(content)
print("File written successfully")
