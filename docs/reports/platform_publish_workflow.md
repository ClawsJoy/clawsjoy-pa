---
type: sop
tags: [平台发布工作流, SOP]
created: 2026-09-10
updated: 2026-09-10
---

## 任务决策 2026-09-10

- **第 7 步点击前二次只读确认**（防误触）：目标选择器全页仅命中 **1 个**元素，类名 `ds-button--primary ds-button--filled ds-button--circle`，含 `<svg>`、未禁用、位于右下角 (x=1230, y=925) → 判定为发送键，**非 x=980 胶囊键、非 turnstile**，才执行点击。
1. **发送键选择器与旧记忆不一致**：跨会话记忆称"发送键选择器已锁定为 `a`"，但本轮实测左下角 `_020ab5b` 容器内的发送键是 `div.ds-button--circle`（primary+filled，`role=button`），页面无 `a` 型发送键；我按本轮指定 selector 执行，并以"点击前唯一性+属性校验 → 点击后 textarea 清零 + markdo
