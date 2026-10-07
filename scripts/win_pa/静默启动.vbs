' ClawsJoy silent launch shell (PRODUCTION, 2026-09-24, tech lead f202f89)
'   usage: wscript.exe //B "silent_launch.vbs" "<exe>" ["<arg1>" ...]
' why:  the Task Scheduler creates a NEW console window for a console app, and the app
'       can only hide that window AFTER it exists (measured: 0.45-0.53 s VISIBLE, once
'       per 07/08/09/10/11 slot plus once at logon).
'       WshShell.Run with window style 0 passes SW_HIDE at CreateProcess time
'       => the hidden console is created hidden => 0 visible frames (measured 4x).
' provenance: workflow-lab prototype (11_<lab folder>/..._/silent_launch.vbs),
'       1,036 B, sha16 c9670303ab07dd0f, landed here as a production file per the
'       CEO ruling of 2026-09-24 (codex/_CEO..._20260924_0025.md, sha16 259bb6e89f6d825b).
'       Logic below is byte-identical to the prototype; only this header was added.
' exit code = exit code of the launched process (the task keeps its rc semantics).
' NOTE: this file is intentionally pure ASCII (comments included) -- WSH reads .vbs
'       using the machine ANSI code page, so non-ASCII bytes would decode differently
'       per machine. The Chinese documentation lives in the companion .md instead.
' ---- shipped in-package copy (pm_1865 sec2.1 (b) -- 'silent shell' form) ----
'   why here: install_win_pa.py::task_items() must register the two PA tasks on a
'   NET machine, where the vault path (D:\Obsidian\...\08_tools\) does not exist.
'   scripts/win_pa/ is part of make_client_bundle.PAYLOAD, so this file travels
'   with the client.  Logic is byte-identical to the vault original; only these
'   comment lines were added.  KEEP THIS FILE PURE ASCII (WSH/ANSI code page).
Option Explicit
Dim sh, q, cmd, i, rc
If WScript.Arguments.Count < 1 Then WScript.Quit 3
q = Chr(34)
cmd = q & WScript.Arguments(0) & q
For i = 1 To WScript.Arguments.Count - 1
  cmd = cmd & " " & q & WScript.Arguments(i) & q
Next
Set sh = CreateObject("WScript.Shell")
rc = sh.Run(cmd, 0, True)
WScript.Quit rc