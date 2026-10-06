#!/usr/bin/env node
/**
 * 批191 · 渲器漂移闸（承 pm_1399 §二.1 ／ §二.5）
 *
 * 一 钉什么：
 *   web/static/js/md.js 之 mdToHtml  ⟷  web/pa/faces/session.js 之 paMdToHtml
 *   —— md.js:4 自陈「来源：批187 web/pa.html 的 paMdToHtml 纯函数块（算法逐行搬运）」
 *   ⇒ 二份同算法 ⇒ 改一处而漏另一处 ⇒ 二面之渲形必漂（而人 ⛔ 觉）
 *   ⇒ 本闸以「同一输入 ⇒ 输出逐字相等」钉其等（承 pm_1399 §二.1 之律）。
 *
 * 二 反控九条（承 pm_1397 §一 ／ §二 ／ pm_1399 §二.5）：
 *   ① 属性注入（href 之 " 须先转 ⇒ ⛔ 出属性境）
 *   ② javascript: ／ ③ data: URL（⛔ 协议白名单 ⇒ 降级为纯文本 · ⛔ 出 a）
 *   ④ iframe ／ ⑤ script（整段 esc ⇒ ⛔ 出标签）
 *   ⑥ *.py ／ ⑦ 2*3*4（词界 ⇒ 字面 · ⛔ 判强调）
 *   ⑧ *很* ／ ⑨ **很**（真强调 ⇒ 仍须渲）
 *
 * 三 用法：node tests/js/md.test.js        0 = 过 ／ 1 = 漂 或 反控失
 *   依赖：无（node 内置 fs ／ path）。
 *
 * 四 ⚠ 已知限（⛔ 判红 · 承实）：
 *   session.js 之 paMdEsc 走 DOM（esc ＝ textContent→innerHTML）；浏览器除 & < > 外，
 *   还会把 \u00a0 序列化为 &nbsp;，而 md.js 之 mdEsc 只转 & < >。
 *   ⇒ 含 NBSP 之文本仍存一处潜在漂 —— 本闸以「& < >」垫片代 DOM，⚠ 看不见该差（列「待补」）。
 *   ⚠ 并立：本闸 ⛔ 证「渲器安全」（唯证「二份相等 ＋ 九反控之行为」）—— ⛔ 以闸绿自评「已通过」。
 */
'use strict'

var fs = require('fs')
var path = require('path')

var ROOT = path.resolve(__dirname, '..', '..')
var MD_JS = path.join(ROOT, 'web', 'static', 'js', 'md.js')
var SESSION_JS = path.join(ROOT, 'web', 'pa', 'faces', 'session.js')

/* 垫片：session.js 之纯函数块依赖外层 esc()（DOM）⇒ 以「& < >」之语义代（≡ mdEsc 之契约） */
function escShim(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

/* 载体一：md.js 之 mdToHtml（整件载入 · 以 stub window 收其导出） */
function loadMdToHtml() {
  var src = fs.readFileSync(MD_JS, 'utf8')
  var fn = new Function('window', src + '\n; return window.mdToHtml;')
  var f = fn({})
  if (typeof f !== 'function') throw new Error('md.js ⛔ 出 mdToHtml（导出名或 IIFE 已改？）')
  return f
}

/* 载体二：session.js 之 paMdToHtml（按「纯函数块」标记抽取 ⇒ ⛔ 依赖 DOM） */
function loadPaMdToHtml() {
  var lines = fs.readFileSync(SESSION_JS, 'utf8').split('\n')
  var b = -1, e = -1
  for (var i = 0; i < lines.length; i++) {
    if (b < 0 && /Markdown 智能渲染/.test(lines[i]) && /BEGIN/.test(lines[i])) { b = i }
    else if (b >= 0 && /MD 渲染纯函数块 END/.test(lines[i])) { e = i; break }
  }
  if (b < 0 || e < 0) throw new Error('session.js ⛔ 见「纯函数块 BEGIN ／ MD 渲染纯函数块 END」标记（抽取败）')
  var fn = new Function('esc', lines.slice(b, e + 1).join('\n') + '\n; return paMdToHtml;')
  var f = fn(escShim)
  if (typeof f !== 'function') throw new Error('session.js 之纯函数块 ⛔ 出 paMdToHtml')
  return f
}

/* 一 · 漂移之料（同输入 ⇒ 输出须逐字相等 · 覆盖各构造） */
var DRIFT = [
  { name: '空串', md: '' },
  { name: '纯空白', md: '   \n  ' },
  { name: '单段', md: '这是正文一段。' },
  { name: '多段', md: '甲段\n\n乙段\n\n丙段' },
  { name: '标题 1-4', md: '# 一\n## 二\n### 三\n#### 四' },
  { name: '无序表', md: '- 甲\n- 乙\n* 丙\n+ 丁' },
  { name: '有序表', md: '1. 甲\n2. 乙\n3) 丙' },
  { name: '表', md: '| 列甲 | 列乙 |\n|---|---|\n| a | b |\n| c | d |' },
  { name: '围栏码', md: '前言\n```python\nx = "`" * 3\n```\n后记' },
  { name: '引文', md: '> 引一\n> 引二' },
  { name: '分隔线', md: '甲\n\n---\n\n乙\n\n***\n\n丙' },
  { name: '行内码', md: '见 `a < b & c` 之式' },
  { name: '链接 https', md: '见 [例](https://example.com/a?b=1&c=2) 处' },
  { name: '链接 mailto', md: '邮 [我](mailto:a@b.com)' },
  { name: '强调混排', md: '*甲* 与 **乙** 及 `丙`' },
  { name: '转义面', md: '<b>&</b> "q" \\u00a0' },
  { name: '长文超限', md: '甲'.repeat(40001) },
  { name: 'CRLF', md: '甲\r\n\r\n乙' },
]

/* 二 · 反控之料（check 返 null ＝ 过 ∨ 返「因」＝ 失） */
var CTRL = [
  { name: '① 属性注入（href 之 "）',
    md: '[x](https://a.com/"onmouseover="alert(1))',
    check: function (o) {
      if (o.indexOf('"onmouseover="') >= 0) return '属性被注入（出 raw onmouseover=）'
      if (o.indexOf('<a href="https://a.com/&quot;') < 0) return '唯须仍成链（且 " 已转 &quot;）'
      return null
    } },
  { name: '② javascript: URL',
    md: '[x](javascript:alert(1))',
    check: function (o) {
      if (o.indexOf('javascript:') >= 0) return '出 javascript: 之字'
      if (o.indexOf('<a ') >= 0) return '仍是链接（须降级为纯文本）'
      return null
    } },
  { name: '③ data: URL',
    md: '[x](data:text/html,<script>alert(1)</script>)',
    check: function (o) {
      if (o.indexOf('<a ') >= 0) return '仍是链接（须降级为纯文本）'
      if (o.indexOf('<script') >= 0) return '出 <script'
      return null
    } },
  { name: '④ iframe',
    md: '<iframe src="javascript:alert(1)"></iframe>',
    check: function (o) {
      if (o.indexOf('<iframe') >= 0) return '出 <iframe'
      return null
    } },
  { name: '⑤ script',
    md: '<script>alert(1)</script>',
    check: function (o) {
      if (o.indexOf('<script') >= 0) return '出 <script'
      return null
    } },
  { name: '⑥ 通配 *.py（词界）',
    md: '见 *.py 与 *.js 之别',
    check: function (o) {
      if (o.indexOf('<em>') >= 0) return '*.py 被判强调'
      if (o.indexOf('*.py') < 0) return '字面 *.py 丢失'
      return null
    } },
  { name: '⑦ 乘法 2*3*4（词界）',
    md: '2*3*4=24',
    check: function (o) {
      if (o.indexOf('<em>') >= 0) return '2*3*4 被判强调'
      if (o.indexOf('2*3*4') < 0) return '字面 2*3*4 丢失'
      return null
    } },
  { name: '⑧ 真强调 *很*',
    md: '这*很*重要',
    check: function (o) {
      if (o.indexOf('<em>很</em>') < 0) return '真强调 ⛔ 渲'
      return null
    } },
  { name: '⑨ 强强调 **很**',
    md: '这**很**重要',
    check: function (o) {
      if (o.indexOf('<strong>很</strong>') < 0) return '强强调 ⛔ 渲'
      return null
    } },
]

function main() {
  var mdHtml, paHtml
  try {
    mdHtml = loadMdToHtml()
    paHtml = loadPaMdToHtml()
  } catch (e) {
    console.log('[闸·载入败] ' + e.message)
    return 1
  }
  var bad = 0, n = 0

  DRIFT.forEach(function (c) {
    n++
    var a = mdHtml(c.md), b = paHtml(c.md)
    if (a !== b) {
      bad++
      console.log('[漂] ' + c.name + '\n  md=' + a.slice(0, 300) + '\n  pa=' + b.slice(0, 300))
    }
  })

  CTRL.forEach(function (c) {
    n++
    var a = mdHtml(c.md), b = paHtml(c.md)
    if (a !== b) {
      bad++
      console.log('[漂·反控料] ' + c.name + '\n  md=' + a.slice(0, 300) + '\n  pa=' + b.slice(0, 300))
    }
    var why = c.check(a)
    if (why) {
      bad++
      console.log('[反控失] ' + c.name + ' —— ' + why + '\n  out=' + a.slice(0, 300))
    }
  })

  if (bad) {
    console.log('判红：' + bad + ' ／ ' + n + ' ⇒ ⛔ 过（漂 或 反控失）')
    return 1
  }
  console.log('过：漂移 ' + DRIFT.length + ' ＋ 反控 ' + CTRL.length + ' ＝ ' + n + ' 皆 ✔')
  return 0
}

if (require.main === module) { process.exit(main()) }
module.exports = { main: main, loadMdToHtml: loadMdToHtml, loadPaMdToHtml: loadPaMdToHtml }
