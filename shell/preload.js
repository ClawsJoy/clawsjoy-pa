'use strict';
/*
 * preload.js —— 壳之桥（**一处定形** · 承 pm_1657 §二.2 ／ pm_1885 §三.3 ／ pm_1890 §一 ／ pm_1896 §三）。
 *
 * 约（照 `openFeedbackDir` 之族）：**名** ／ **参** ／ **返** 之形唯在此处出（⛔ 二处各写）；
 *   ⛔ 出网：本档 ⛔ 引任何网络之能（唯本机 ipc）。
 *
 * ① `openFeedbackDir()` ⇒ `Promise<{ok:true,path}|{ok:false,code,message}>`（**参 ＝ 无** · 径由壳自算）。
 * ② `shellUpdateState()` ⇒ **收壳层更新之态**（幂等 · 只读 · ⛔ 副作用）—— ⭐ **态之唯一真源（拉）**（pm_1890 §一.2）。
 *    返：成 `{ok:true, phase, current, latest, progress}` ∨ 败 `{ok:false, phase, code, message}`
 *      （`phase` ∈ 八字 · `code` ∈ 七码 · `message` ＝ 人话 ＋ 去处 · ⛔ 行话上屏 · ⛔ 本机径 ／ ⛔ 端点）。
 * ③ `shellUpdateInstall()` ⇒ **触发「重启并安装」**（⭐ 唯由用户之点 ⇒ ⛔ 自动装 ／ ⛔ 偷重启 · pm_1885 §三.2）。
 * ④ `onShellUpdate(cb)` ⇒ 壳**唤面再拉**（⭐ **⛔ 传态** —— 免得「拉与推不一」而用户见二真相 · pm_1890 §一.2）；
 *    返**退订之器**（`function () {}` · 面之清理用）。
 * ⚠ 失败之面 ⛔ 静默：面必明书**因 ＋ 去处**（`message` 已载 ⇒ 面直接显示 · ⛔ 再拼）。
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('paShell', {
  openFeedbackDir: function () {
    return ipcRenderer.invoke('pa:open-feedback-dir');
  },
  shellUpdateState: function () {
    return ipcRenderer.invoke('pa:shell-update-state');
  },
  shellUpdateInstall: function () {
    return ipcRenderer.invoke('pa:shell-update-install');
  },
  // 召出浮窗之「发」：文字交壳 ⇒ 壳交主窗（出计划卡 · 一处）。参：文本；返：{ok}（壳侧之果）。
  summonSend: function (text) {
    return ipcRenderer.invoke('pa:summon-send', String(text == null ? '' : text));
  },
  summonCommand: function (cmd) {
    return ipcRenderer.invoke('pa:summon-command', String(cmd == null ? '' : cmd));
  },
  // 录屏悬浮控制条（独立置顶窗）
  recShow: function () { return ipcRenderer.invoke('pa:rec-show'); },
  recHide: function () { return ipcRenderer.invoke('pa:rec-hide'); },
  recStop: function () { return ipcRenderer.invoke('pa:rec-stop'); },
  recMicToggle: function () { return ipcRenderer.invoke('pa:rec-mic'); },
  // 选择本地目录（导入 md）
  pickDirectory: function () { return ipcRenderer.invoke('pa:pick-directory'); },
  // 打开本机产物（仅 PA 数据目录、白名单类型）
  openPath: function (p) { return ipcRenderer.invoke('pa:open-path', String(p || '')); },
  // 屏幕录播来源（仅本机）
  screenSources: function () { return ipcRenderer.invoke('pa:screen-sources'); },
  screenSelect: function (id, audio) { return ipcRenderer.invoke('pa:screen-select', { id: String(id || ''), audio: audio === true }); },
  // 内置浏览器 P0（只读／存 note；远程页无 Node）
  browserShow: function (opt) { return ipcRenderer.invoke('pa:browser-show', opt || {}); },
  browserHide: function () { return ipcRenderer.invoke('pa:browser-hide'); },
  browserClose: function () { return ipcRenderer.invoke('pa:browser-close'); },
  browserFullscreen: function (on) { return ipcRenderer.invoke('pa:browser-fullscreen', on); },
  browserAsrStart: function () { return ipcRenderer.invoke('pa:browser-asr-start'); },
  browserAsrStop: function () { return ipcRenderer.invoke('pa:browser-asr-stop'); },
  browserAsrPoll: function () { return ipcRenderer.invoke('pa:browser-asr-poll'); },
  browserGo: function (url) { return ipcRenderer.invoke('pa:browser-go', String(url || '')); },
  browserRead: function () { return ipcRenderer.invoke('pa:browser-read'); },
  browserState: function () { return ipcRenderer.invoke('pa:browser-state'); },
  browserBack: function () { return ipcRenderer.invoke('pa:browser-back'); },
  browserForward: function () { return ipcRenderer.invoke('pa:browser-forward'); },
  browserReload: function () { return ipcRenderer.invoke('pa:browser-reload'); },
  onBrowserPing: function (cb) {
    if (typeof cb !== 'function') { return function () { }; }
    const h = function () { try { cb(); } catch (e) { } };
    ipcRenderer.on('pa:browser-ping', h);
    return function () { try { ipcRenderer.removeListener('pa:browser-ping', h); } catch (e) { } };
  },
  onShellUpdate: function (cb) {
    if (typeof cb !== 'function') { return function () { }; }
    const h = function () { try { cb(); } catch (e) { /* 面之错 ⛔ 阻壳 */ } };
    ipcRenderer.on('pa:shell-update-ping', h);
    return function () { try { ipcRenderer.removeListener('pa:shell-update-ping', h); } catch (e) { } };
  }
});
