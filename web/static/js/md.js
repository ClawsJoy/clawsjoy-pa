/**
 * 批190 · 共享 Markdown 智能渲染（纯函数 + 样式注入；单源）
 *
 * 来源：批187 web/pa.html 的 paMdToHtml 纯函数块（算法逐行搬运，函数名 pa* → md*）。
 * 为什么单独成文件：工作台页(web/dashboard/workbench.html)也要同一套渲染效果；
 *   两页各抄一份必然漂移 ⇒ 抽出单源 + tests/js/md.test.js 里做「与 pa 版输出逐字相等」漂移闸。
 * 用法：叶子页 <script src="/web/static/js/md.js"></script> 之后调 mdToHtml(text)。
 * 安全：先整体转义 & < >，行内再按白名单生成标签；输出标签白名单与 pa 版一致。
 * 依赖：无（样式由本文件注入一次；代码块「复制」按钮走全局事件委托）。
 * 降级：md.js 未加载时调用方必须回退纯文本（agent-terminal.js 已按此判据写）。
 */
(function (global) {
  'use strict'

  var MD_MAX = 40000

  function mdEsc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  }

  function mdInline(t) {
    var x = String(t == null ? '' : t)
    x = x.replace(/\x60([^\x60]+)\x60/g, function (_, c) { return '<code>' + c + '</code>' })
    x = x.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    x = x.replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>')
    x = x.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+|mailto:[^)\s]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
    x = x.replace(/\[([^\]]+)\]\(([^)]*)\)/g, '$1')
    return x
  }

  function mdTable(rows) {
    var head = rows[0], body = rows.slice(1)
    var h = '<div class="mdtable"><table><thead><tr>'
    head.forEach(function (c) { h += '<th>' + mdInline(c) + '</th>' })
    h += '</tr></thead><tbody>'
    body.forEach(function (r) {
      h += '<tr>'
      for (var i = 0; i < head.length; i++) { h += '<td>' + mdInline(r[i] === undefined ? '' : r[i]) + '</td>' }
      h += '</tr>'
    })
    return h + '</tbody></table></div>'
  }

  function mdToHtml(text) {
    var raw = String(text == null ? '' : text)
    if (!raw.trim()) return ''
    if (raw.length > MD_MAX) return '<p>' + mdEsc(raw) + '</p>'
    var src = mdEsc(raw).replace(/\r\n/g, '\n')
    var lines = src.split('\n')
    var out = []
    var i = 0, list = null, para = []
    var flushPara = function () { if (para.length) { out.push('<p>' + mdInline(para.join('<br>')) + '</p>'); para = [] } }
    var closeList = function () { if (list) { out.push(list === 'ul' ? '</ul>' : '</ol>'); list = null } }
    while (i < lines.length) {
      var ln = lines[i]
      if (/^\s*\x60\x60\x60/.test(ln)) {
        flushPara(); closeList()
        var lang = ln.replace(/^\s*\x60\x60\x60/, '').trim()
        var buf = []
        i++
        while (i < lines.length && !/^\s*\x60\x60\x60/.test(lines[i])) { buf.push(lines[i]); i++ }
        i++
        out.push('<div class="mdcode"><div class="mdcodebar"><span>' + mdEsc(lang || 'code') +
          '</span><button class="mdcopy" type="button">⧉ 复制</button></div><pre>' + buf.join('\n') + '</pre></div>')
        continue
      }
      var h = ln.match(/^(#{1,4})\s+(.*)$/)
      if (h) { flushPara(); closeList(); out.push('<h' + h[1].length + '>' + mdInline(h[2]) + '</h' + h[1].length + '>'); i++; continue }
      if (/^\s*(---+|\*\*\*+)\s*$/.test(ln)) { flushPara(); closeList(); out.push('<hr>'); i++; continue }
      if (/^\s*(?:>|&gt;)\s?/.test(ln)) { flushPara(); closeList(); out.push('<blockquote>' + mdInline(ln.replace(/^\s*(?:>|&gt;)\s?/, '')) + '</blockquote>'); i++; continue }
      if (/^\s*\|.*\|\s*$/.test(ln) && i + 1 < lines.length && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i + 1])) {
        flushPara(); closeList()
        var rows = []
        while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) {
          var cells = lines[i].trim().replace(/^\||\|$/g, '').split('|').map(function (c) { return c.trim() })
          if (!/^[\s:|-]+$/.test(lines[i].trim().replace(/^\||\|$/g, ''))) rows.push(cells)
          i++
        }
        if (rows.length) out.push(mdTable(rows))
        continue
      }
      var ul = ln.match(/^\s*[-*+]\s+(.*)$/)
      var ol = ln.match(/^\s*\d+[.)]\s+(.*)$/)
      if (ul || ol) {
        flushPara()
        var kind = ul ? 'ul' : 'ol'
        if (list !== kind) { closeList(); out.push(kind === 'ul' ? '<ul>' : '<ol>'); list = kind }
        out.push('<li>' + mdInline((ul || ol)[1]) + '</li>')
        i++; continue
      }
      if (!ln.trim()) { flushPara(); closeList(); i++; continue }
      para.push(ln)
      i++
    }
    flushPara(); closeList()
    return out.join('')
  }

  var MD_CSS = '.mdbody{white-space:normal}'
    + '.mdbody h1,.mdbody h2,.mdbody h3,.mdbody h4{margin:8px 0 4px;line-height:1.3}'
    + '.mdbody h1{font-size:17px}.mdbody h2{font-size:16px}.mdbody h3{font-size:15px}.mdbody h4{font-size:14px}'
    + '.mdbody p{margin:4px 0}'
    + '.mdbody ul,.mdbody ol{margin:4px 0 4px 20px;padding:0}'
    + '.mdbody blockquote{border-left:3px solid var(--border,#30363d);margin:4px 0;padding:2px 8px;color:var(--sub,#8b949e)}'
    + '.mdbody code{background:rgba(255,255,255,.08);border-radius:3px;padding:0 3px;font-size:12px}'
    + '.mdbody pre code{background:transparent;padding:0}'
    + '.mdbody hr{border:none;border-top:1px solid var(--border,#30363d);margin:8px 0}'
    + '.mdbody a{color:#58a6ff;text-decoration:underline}'
    + '.mdbody .mdtable{overflow-x:auto;margin:6px 0}'
    + '.mdbody .mdtable table{border-collapse:collapse;font-size:12px}'
    + '.mdbody .mdtable th,.mdbody .mdtable td{border:1px solid var(--border,#30363d);padding:3px 8px;text-align:left}'
    + '.mdbody .mdcode{border:1px solid var(--border,#30363d);border-radius:6px;margin:6px 0;overflow:hidden}'
    + '.mdbody .mdcodebar{display:flex;justify-content:space-between;align-items:center;padding:2px 8px;'
    + 'background:rgba(255,255,255,.05);font-size:11px;color:var(--sub,#8b949e)}'
    + '.mdbody .mdcode pre{margin:0;padding:8px 10px;overflow-x:auto;font-size:12px;line-height:1.45}'
    + '.mdbody .mdcopy{background:transparent;border:1px solid var(--border,#30363d);border-radius:4px;'
    + 'color:var(--sub,#8b949e);font-size:11px;cursor:pointer}'

  function mdStyleEnsure() {
    if (!global.document || !global.document.head) return
    if (global.document.getElementById('mdStyle')) return
    var st = global.document.createElement('style')
    st.id = 'mdStyle'
    st.textContent = MD_CSS
    global.document.head.appendChild(st)
  }

  function mdCopyBind() {
    if (!global.document || !global.document.addEventListener) return
    global.document.addEventListener('click', function (e) {
      var t = e && e.target
      var b = (t && t.closest) ? t.closest('.mdcopy') : null
      if (!b) return
      var pre = b.parentElement ? b.parentElement.nextElementSibling : null
      var txt = pre ? pre.textContent : ''
      var done = function () { var o = b.textContent; b.textContent = '✓ 已复制'; setTimeout(function () { b.textContent = o }, 1200) }
      if (global.navigator && global.navigator.clipboard) { global.navigator.clipboard.writeText(txt).then(done, done) } else { done() }
    })
  }

  mdStyleEnsure()
  mdCopyBind()

  global.mdEsc = mdEsc
  global.mdInline = mdInline
  global.mdTable = mdTable
  global.mdToHtml = mdToHtml
})(typeof window !== 'undefined' ? window : this)
