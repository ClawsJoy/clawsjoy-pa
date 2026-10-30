# 签名路线：SignPath vs 自签（2026-10-28 23:5x）

- 令：只考虑 SignPath Foundation（开源）与自签
- 判：**SignPath 不适用闭源 PA；自签适用内测；已出 9.0.16 自签包。**

## 一 SignPath Foundation

条件（terms.html）：
- OSI 认可开源许可，且**无商业双许可**；
- **无任何专有/闭源组件**（含维护者发布的闭源件）；
- 项目活跃、已发布、有文档；
- 证书由 SignPath Foundation 签发 ⇒ **发布者显示 SignPath Foundation**；
- 只能签自己团队、自己源码构建的产物。

⇒ ClawsJoy PA 是闭源/自有产品，**不符合**；不申请、不伪装开源。

## 二 自签

- 证书：CN=ClawsJoy Internal，thumb 654F9E0C…，2029-10-28；
- PFX：dist/pa_shell/ClawsJoy_Internal.pfx（私钥，离线保管）；
- 公钥：dist/pa_shell/ClawsJoy_Internal.cer（780 B，sha256 6A2A2DF2…）；
- 9.0.16 已签：signtool Successfully signed；Get-AuthenticodeSignature=UnknownError/UntrustedRoot。

### 信任机器上导入

管理员：
```powershell
certutil -addstore -f Root ClawsJoy_Internal.cer
certutil -addstore -f TrustedPublisher ClawsJoy_Internal.cer
```

或当前用户（不需管理员，但仅本用户）：
```powershell
Import-Certificate -FilePath .\ClawsJoy_Internal.cer -CertStoreLocation Cert:\CurrentUser\Root
Import-Certificate -FilePath .\ClawsJoy_Internal.cer -CertStoreLocation Cert:\CurrentUser\TrustedPublisher
```

- 效果：本机信任该发布者，UAC/属性显示 CN=ClawsJoy Internal；
- **仍不解决 SmartScreen**；新机器不导入则 UntrustedRoot；
- 每次发布用同一证书签，PFX 不随包分发。

## 三 结论

- 内测/自有机器：自签，0 成本，继续；
- 对外公开：自签不够；SignPath 也不适用闭源 ⇒ 要么真 OV/EV，要么保持内测；
- 9.0.16 已在 _share；Program Files 未验。

（完 —— 本件末行 · LF 终 · 悬）
