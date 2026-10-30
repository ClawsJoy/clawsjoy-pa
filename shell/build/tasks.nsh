; tasks.nsh -- re-form the 'scheduled task shape' right after install.
;   one definition / no second copy (pm_1885 sec2.2 + pm_1896 sec2.3(c), tech lead f202f89, 2026-10-08)
;
; WHY: the NSIS shell installer does NOT touch scheduled tasks (three first-hand proofs, TD 1895 sec2.2).
;      So a NET machine that still has old-form tasks (host cmd.exe) would keep them, and the 9.0.10
;      flash fix (which only changed scripts) would NOT take effect there.  This macro re-forms them.
;
; HOW: run the payload's silent recorder with the BUNDLED runtime --
;        <payload>\runtime\python.exe -X utf8 -B <payload>\scripts\win_pa\install_tasks_silent.py --go
;      The recorder imports install_win_pa.py and calls its plan()/render_and_maybe_apply() with
;      register_tasks=True -- the SAME single place that registers the two PA tasks and (pm_1877)
;      migrates existing old-form tasks => one definition, no second copy.
;      The RECORDER (not the installer) writes the log, because install_win_pa.py is guarded by its own
;      self-test against any non-read open() and must never write a file (pm_1896 sec2.3(c), TD note).
;      vault: the recorder always passes vault_dir=None => built-in empty vault (an installer has no
;      stdin, so it must never prompt; --skip-vault equivalent).
;
; RC: the recorder's exit code IS the record -- nsExec pushes it in $0 and THIS macro writes it to
;      <logs>\install_tasks.rc (single writer; the recorder deliberately never writes that file).
;      A stale .rc from a previous install is deleted first, so 'no file' means 'recorded nothing'
;      and the shell reports it honestly on first start (main.js::reportInstallTasksOnce).
;
; WINDOW: nsExec::ExecToStack runs the child with a HIDDEN console (that is nsExec's purpose).
;      ExecWait would show a console window for a console app => forbidden here (this whole batch
;      exists to reach '0 visible console windows').
; FAILURE: NEVER abort the install (a missing shell is worse than an old-form task, pm_1896 sec2.3(c)).
;      The record goes to <logs>\install_tasks.rc + .log; the shell reports a non-zero rc once.
; ASCII: this file is intentionally pure ASCII (makensis code page safety).

!macro customInstall
  CreateDirectory "$LOCALAPPDATA\ClawsJoyPA\shell"
  Delete "$LOCALAPPDATA\ClawsJoyPA\shell\install_tasks.rc"
  Delete "$LOCALAPPDATA\ClawsJoyPA\shell\install_tasks.log"
  DetailPrint "ClawsJoy PA: scheduled tasks (shape) ..."
  nsExec::ExecToStack '"$INSTDIR\resources\payload\runtime\python.exe" -X utf8 -B "$INSTDIR\resources\payload\scripts\win_pa\install_tasks_silent.py" --go --log-file "$LOCALAPPDATA\ClawsJoyPA\shell\install_tasks.log"'
  Pop $0
  Pop $1
  FileOpen $2 "$LOCALAPPDATA\ClawsJoyPA\shell\install_tasks.rc" w
  FileWrite $2 "rc=$0$\r$\n"
  FileClose $2
  DetailPrint "ClawsJoy PA: tasks rc=$0 (install continues regardless)"
  ; --- PA 9.0.14 P0-2: writable roots as junctions ---
  ; payload\logs/data/vec -> %LOCALAPPDATA%\ClawsJoyPA\{logs,data,vec}
  ; why: gateway writes relative to install root; install root may be read-only.
  ; never abort: a shell that starts with old roots is worse than a junction miss.
  CreateDirectory "$LOCALAPPDATA\ClawsJoyPA\logs"
  DetailPrint "ClawsJoy PA: writable roots (junction) ..."
  nsExec::ExecToStack '"$INSTDIR\resources\payload\runtime\python.exe" -X utf8 -B "$INSTDIR\resources\payload\scripts\win_pa\ensure_roots.py" ensure --root "$INSTDIR\resources\payload" --base "$LOCALAPPDATA\ClawsJoyPA" --log-file "$LOCALAPPDATA\ClawsJoyPA\logs\ensure_roots.log"'
  Pop $0
  Pop $1
  DetailPrint "ClawsJoy PA: roots rc=$0 (install continues regardless)"
!macroend

; uninstall: unlink junctions ONLY; never delete target dirs (user data lives there).
!macro customUnInstall
  DetailPrint "ClawsJoy PA: unlink writable roots (junction) ..."
  nsExec::ExecToStack '"$INSTDIR\resources\payload\runtime\python.exe" -X utf8 -B "$INSTDIR\resources\payload\scripts\win_pa\ensure_roots.py" remove --root "$INSTDIR\resources\payload" --base "$LOCALAPPDATA\ClawsJoyPA" --log-file "$LOCALAPPDATA\ClawsJoyPA\logs\ensure_roots.log"'
  Pop $0
  Pop $1
  DetailPrint "ClawsJoy PA: roots unlink rc=$0 (targets kept)"
!macroend
