# -*- coding: utf-8 -*-
"""批187 · A 段：PA 前端「老板能用」真浏览器复核（入口可见性 + 8 步流程 + 8 态迁移观察）。

原则（按批187 定稿与体检 122/111）：
  - 真 Chromium（playwright），**非脚本注入**：不伪造 DOM/状态；
  - 状态迁移用**观察器**（包 window.paSetState 记录每次迁移）——体检 122 认可的做法；
  - **不代老板点写审批**：审批卡只截图 + 断言可点，**不点**（B 段是老板的动作）；
  - 每步存 PNG；末尾输出 JSON（供报告引用）。
"""
import argparse
import json
import os
import sys
import time

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5002"
OBSERVER = """
window.__paStates = [];
(function(){
  var t0 = Date.now();
  function wrap(){
    if (typeof window.paSetState === 'function' && !window.__paWrapped) {
      var orig = window.paSetState;
      window.paSetState = function(k, note){ window.__paStates.push({t: Date.now()-t0, k: k, note: note||''}); return orig.apply(this, arguments); };
      window.__paWrapped = true; return true;
    }
    return false;
  }
  if (!wrap()) { var iv = setInterval(function(){ if (wrap()) clearInterval(iv); }, 50); }
})();
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="在沙箱 data/reports 下新建一个 hello187.md，内容写「批187 前端自检」，然后读回来给我看")
    ap.add_argument("--out", default="/tmp/p187_shots")
    ap.add_argument("--wait-approval", type=int, default=150)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    out = {"visibility": {}, "steps": [], "states": [], "approval": None}

    def shot(page, name, note=""):
        page.screenshot(path=os.path.join(a.out, name))
        out["steps"].append({"shot": name, "note": note})
        print("  [shot] %-32s %s" % (name, note))

    with sync_playwright() as pw:
        br = pw.chromium.launch()
        ctx = br.new_context(viewport={"width": 1440, "height": 900})
        ctx.add_init_script(OBSERVER)
        page = ctx.new_page()
        print("--- A1：pa.html 入口可见性 ---")
        r = page.goto(BASE + "/web/pa.html", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        v = {}
        v["http"] = r.status if r else None
        ta = page.locator("#input")
        v["输入框_可见"] = ta.is_visible()
        v["输入框_可编辑"] = ta.is_editable()
        cb = page.locator("#modelText")
        v["通道徽章_可见"] = cb.is_visible()
        v["通道徽章_文本"] = cb.inner_text()[:40]
        cs = page.locator("#chanSwitch")
        v["切换按钮_可见(当前模式)"] = cs.is_visible()
        v["切换按钮_可点"] = cs.is_enabled()
        shot(page, "01_pa_open.png", "打开 PA 页（入口区）")
        print("  当前徽章 =", v["通道徽章_文本"], "| 切换按钮可见 =", v["切换按钮_可见(当前模式)"])
        print("--- A1b：模式往返（验证「一键切换」真能点）---")
        try:
            page.locator('#modes .mode[data-mode="chat"]').first.click()
            page.wait_for_timeout(600)
            v["切到聊天后_切换按钮可见"] = cs.is_visible()
            shot(page, "02_mode_chat.png", "切到聊天模式（徽章应变「聊天」）")
            if cs.is_visible():
                cs.click()
                page.wait_for_timeout(600)
                v["点切换后_徽章文本"] = cb.inner_text()[:40]
                shot(page, "03_mode_work.png", "点「切到工作模式」后（徽章应显示真执行）")
        except Exception as e:
            v["模式往返_错误"] = str(e)[:120]
        out["visibility"] = v
        print("  模式往返结果:", {k: v[k] for k in v if "模式" in k or "切换" in k or "徽章" in k})

        print("--- A1c：workbench.html 入口 ---")
        wb = ctx.new_page()
        wb.goto(BASE + "/web/dashboard/workbench.html", wait_until="domcontentloaded", timeout=30000)
        wb.wait_for_timeout(2500)
        wv = {}
        btn = wb.locator('button.nav-btn[data-tab="agent"]').first
        wv["入口按钮_可见"] = btn.is_visible()
        wv["入口按钮_文本"] = btn.inner_text()[:30]
        ai = wb.locator("#agentInput")
        wv["agentInput_可见(首访默认展开)"] = ai.is_visible()
        wv["agentModal_display"] = wb.evaluate(
            "() => { const m=document.getElementById('agentModal'); return m ? getComputedStyle(m).display : 'NA'; }"
        )
        wb.screenshot(path=os.path.join(a.out, "04_workbench.png"))
        out["steps"].append({"shot": "04_workbench.png", "note": "工作台入口 + agentInput 首访"})
        out["workbench"] = wv
        print("  工作台:", wv)
        wb.close()

        print("--- A3：8 步流程（DSH 真浏览器复现，不代老板点审批）---")
        page.bring_to_front()
        page.locator("#input").fill(a.task)
        page.wait_for_timeout(300)
        shot(page, "05_task_typed.png", "步骤4：键入任务")
        page.locator("#sendBtn").click()
        t0 = time.time()
        seen = []
        approval = None
        while time.time() - t0 < a.wait_approval:
            page.wait_for_timeout(1000)
            card = page.locator(".pa-write-card")
            if card.count() > 0 and card.first.is_visible():
                approval = {"found_after_s": round(time.time() - t0, 1)}
                break
            try:
                txt = page.evaluate('() => (window.__paStates||[]).map(x => x.k).join(" > ")')
            except Exception:
                txt = ""
            if txt and txt not in seen:
                seen.append(txt)
                print("  迁移序列(进行中):", txt[-120:])
        page.screenshot(path=os.path.join(a.out, "06_after_send.png"))
        out["steps"].append({"shot": "06_after_send.png", "note": "步骤5-6：发送后状态"})
        out["states"] = page.evaluate("() => window.__paStates || []")
        print("  状态迁移序列:", " > ".join(x["k"] for x in out["states"]))
        if approval:
            card = page.locator(".pa-write-card").first
            btn = card.locator('button[data-act="approve"]').first
            approval["card_text"] = card.inner_text()[:160].replace(chr(10), " / ")
            approval["approve_可见"] = btn.is_visible()
            approval["approve_可点"] = btn.is_enabled()
            shot(page, "07_write_approval.png", "步骤7：写审批卡（**未点**，留给老板）")
            print("  ✅ 写审批卡出现:", approval["card_text"][:90])
        else:
            print("  ⚠ 等待 %ds 未见写审批卡（如实记录）" % a.wait_approval)
            shot(page, "07_no_approval.png", "未出现写审批卡（如实记录）")
        out["approval"] = approval
        br.close()
    io_path = os.path.join(a.out, "report.json")
    open(io_path, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print("--- 结论 ---")
    print("  入口:", {k: out["visibility"].get(k) for k in ("输入框_可见", "通道徽章_可见", "切换按钮_可见(当前模式)", "切到聊天后_切换按钮可见")})
    print("  工作台:", {k: out.get("workbench", {}).get(k) for k in ("agentInput_可见(首访默认展开)", "入口按钮_可见")})
    print("  写审批卡:", bool(out["approval"]), "| JSON:", io_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
