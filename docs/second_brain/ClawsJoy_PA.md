# ClawsJoy PA · 第二大脑

> 单一事实源（本仓）· 最后更新：2026-10-29 00:1x · 维护：PA Lead
> 原则：这里只放**已定方向/当前实况/待决**；细节报告在 `docs/reports/_pa_groundwork_20261027/`。

## 0 一句话

ClawsJoy PA 是**本地优先的个人 Agent（第二大脑）**；用户本地部署、数据在本机；GEO 社区门户做连接与社区服务；Web3 只做身份/记账/存证，**不发币**。

> 产品核心问题见 [00_产品核心_为什么用PA.md](00_产品核心_为什么用PA.md)：用户为什么用 PA，而不是功能清单。

## 0.1 第二大脑

PA 自带 note/知识库（Markdown + 索引），**不依赖 Obsidian**；Obsidian 仅可选导入/导出。见 [01_第二大脑_note系统.md](01_第二大脑_note系统.md)。

## 1 产品形态

- Windows 桌面壳 `ClawsJoyPA.exe`；新窗 v1（`?paWin=1`）为默认；旧窗仅回退。
- Today / 席（Agents）/ 账 / 库 / 门；设置、密钥、更多、更新、真发送、附件、停、回执。
- 本地模型默认：`local:ollama / qwen2.5:7b-instruct-q4_0-gpu`；DeepSeek key 可配但不再默认。
- 本地优先：数据、日志、账本在 `%LOCALAPPDATA%\ClawsJoyPA`；安装根只放程序。

## 2 当前实况（2026-10-29）

| 项 | 状态 |
|---|---|
| 版本 | **9.0.36**（per-user 已装；陪伴通道自然对话提示词） |
| 新窗默认 | 是；壳载 `/web/pa.html?paWin=1` |
| 默认模型 | 本机 qwen2.5 7B |
| 安装 | 10,772 件 / 495.7 MB；三 junction 正确 |
| 健康 | `/health` 200；version 9.0.36 |
| 签名 | 内部自签 `CN=ClawsJoy Internal`；本机已导入 Root/TrustedPublisher ⇒ Valid；**UntrustedRoot / 不解 SmartScreen** |
| 发布 | 自签 9.0.16 已发 `_share`；无 9.0.16 增量 manifest |
| Program Files | **未验**（UAC） |
| 真 OV/EV | **未申请** |
| 审批 | 两窗只读；Phase 1 后端缺 |

## 3 商业模型

- 用户**本地部署**；免费提供客户端；
- **GEO 网站**：社区服务/发现/活动/声誉/配对；
- **Web3**：钱包/设备身份、社区归属、链上记账；
- **不做代币**；不做链上交易/结算；链上只做记账/存证；
- 付费方向：社区订阅、托管/中继、市场服务；不靠发币。

## 4 链上记账（已定方向，未实现）

- 交易在**用户本地**发生、本地保存；
- 每约 **100 单**（或 24h 超时）建 Merkle 树；
- L2 只发 **1 笔 anchor**：`root / prevRoot / batchId / count / fromTs / toTs / CID`；
- 原始交易、金额明细、用户身份**不上链**；整批数据放 IPFS/Arweave；
- **不是 rollup**：不做状态转换证明，只做存在性/顺序锚定；
- 合约最小、不可升级；anchorer 用 2-of-3 Safe；
- 免费用户 gas 由运营方/paymaster 承担；不引入代币；
- 把 release hash 也纳入批次（建议）。

## 5 身份/配对

- 钱包登录：SIWE（只做社区账户）；
- 设备 DID：每台本地 PA 自生成密钥；私钥不上传；
- 配对：钱包 ↔ 设备，一次性码/QR；
- 门户连接信任靠设备密钥，不靠 exe 代码签名；
- 代码签名只证明软件来源。

## 6 签名/分发

- 早期/可信用户：**我们自签，用户只导入公钥 `.cer`**；不发 PFX；
- 导入脚本：`scripts/win_pa/install_internal_cert.ps1`；
- 证书：`CN=ClawsJoy Internal`，thumb `654F9E0CE9709A5FCB5A8B3347C1E7293F930651`；
- SignPath Foundation：**仅开源**，PA 闭源 ⇒ 不适用；
- 公开分发：Azure Trusted Signing Basic（约 $10/月）或 OV（约 $200–400/年）；
- 自签不解决 SmartScreen；公开下载前必须重新评估。

## 7 已决

1. 本地优先，不做云端集中存储；
2. 新窗 v1 为产品终态；旧窗只回退；
3. 默认本地模型；
4. 不加代币；
5. 链上只记账/存证，交易本地；
6. 100 单/批 Merkle 锚定，不每单上链；
7. 设备 DID/配对做节点信任；
8. 自签只做早期分发；
9. SignPath 不适用闭源；
10. 审批后端未接前，两窗只读。

## 8 待决

- L2：Base / Arbitrum / Optimism；
- 交易是双边用户交易，还是用户自有业务记账；
- 批次默认公开/私密；
- anchorer 多签成员；
- GEO 门户先做哪些社区服务；
- 公开分发签名预算（Azure vs OV/EV）。

## 9 关键路径

- 壳：`shell/main.js`；
- 新窗：`web/pa/faces/window.js`；
- 模型/通道：`core/pa/providers.py`、`web/pa/faces/config.js`；
- 安装根：`scripts/win_pa/ensure_roots.py`；
- 证书导入：`scripts/win_pa/install_internal_cert.ps1`；
- 相关报告：`docs/reports/_pa_groundwork_20261027/84–89`。

## 10 禁止

- 不把 PFX 私钥发给用户；
- 不把个人数据/金额明文上链；
- 不发币、不承诺收益；
- 不用自签冒充公开可信签名；
- 不把代码签名当节点身份；
- 不在新窗未验的路径上切默认。

（完 —— 本件末行 · LF 终 · 悬）
