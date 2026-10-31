/* 第二大脑 · 笔记本（P1，对标 NotebookLM）：
   三栏＝笔记本/来源 ｜ 对话（限定本笔记本） ｜ Studio（摘要/FAQ/学习指南/思维导图）。
   真源：/v9/pa/notebooks* ／ /v9/pa/notes*；模型不可用时照实回落为摘录，不假装。 */
(function(){
  'use strict';
  var API_BASE = (typeof API !== 'undefined') ? API : '';
  var NB = window.PA_NB = {
    notebooks: [], cur: '', total: 0, sources: [], sel: {}, chat: {}, studio: {},
    labels: [], view: 'label', studioKind: 'summary', studioOpts: {}, busy: false
  };
  try{ var _v = localStorage.getItem('pa_nb_src_view_v1'); if(_v === 'list' || _v === 'label') NB.view = _v; }catch(e){}

  function $(id){ return document.getElementById(id); }
  function esc(s){
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }
  function api(p){ return API_BASE + p; }
  function msg(t){ var e = $('paBrainStatus'); if(e) e.textContent = String(t == null ? '' : t); }
  function fmtDate(s){ return String(s || '').replace('T', ' ').slice(0, 16); }

  async function req(path, opt){
    opt = opt || {};
    var init = {cache: 'no-store', method: opt.method || 'GET', headers: opt.headers || {}};
    if(opt.body !== undefined){
      if(opt.form){ init.body = opt.body; }
      else { init.headers['Content-Type'] = 'application/json'; init.body = JSON.stringify(opt.body); }
    }
    var r, d;
    try{
      r = await fetch(api(path), init);
    }catch(e){
      throw new Error('连不上本机服务（' + ((e && e.message) || e) + '）');
    }
    try{ d = await r.json(); }catch(e){ d = null; }
    if(!r.ok || !d || d.ok !== true){
      throw new Error('HTTP ' + r.status + '：' + ((d && (d.error || d.message)) || '后端未给因'));
    }
    return d;
  }

  function iconOf(src){
    var s = String(src || '').toLowerCase();
    if(s === 'pdf') return '📄';
    if(s === 'url') return '🔗';
    if(s === 'voice') return '🎤';
    if(s === 'screen') return '🎬';
    if(s === 'import') return '📚';
    if(s === 'ai') return '✨';
    return '📝';
  }

  /* ---------- 渲染骨架 ---------- */
  window.paBrainHtml = function(){
    return '<div class="pa-nb">'
      + '<aside class="pa-nb-col pa-nb-left">'
      +   '<div class="pa-nb-h"><b>笔记本</b><button class="pa-btn pa-btn-mini pa-btn-ghost" type="button" onclick="paNbCreateOpen()" title="新建笔记本">＋</button></div>'
      +   '<div id="paNbCreate" class="pa-nb-new" hidden>'
      +     '<input id="paNbCreateEmoji" type="text" maxlength="4" value="📘" aria-label="图标">'
      +     '<input id="paNbCreateTitle" type="text" placeholder="笔记本名称：客户 / 学习 / 项目…" aria-label="笔记本名称">'
      +     '<div class="pa-nb-row"><button class="pa-btn pa-btn-mini pa-btn-main" type="button" onclick="paNbCreateSave()">建</button>'
      +     '<button class="pa-btn pa-btn-mini pa-btn-ghost" type="button" onclick="paNbCreateCancel()">取消</button></div>'
      +   '</div>'
      +   '<div id="paNbList" class="pa-nb-list"></div>'
      +   '<div class="pa-nb-src-h"><b>来源</b><span id="paNbSrcCount"></span>'
      +     '<button id="paNbSelAllBtn" class="pa-btn pa-btn-mini pa-btn-ghost" type="button" onclick="paNbSelAll()" title="全选/取消全选">全选</button>'
      +     '<button class="pa-btn pa-btn-mini pa-btn-ghost" type="button" onclick="paNbLabelMenuOpen()" title="标签视图 / 自动整理 / 添加标签">整理</button>'
      +     '<button class="pa-btn pa-btn-mini pa-btn-ghost" type="button" onclick="paNbAddOpen()" title="添加来源">＋</button></div>'
      +   '<div class="pa-nb-src-actions">'
      +     '<button class="pa-btn pa-btn-mini" type="button" onclick="paNbAddOpen()">＋ 添加来源</button>'
      +     '<button class="pa-btn pa-btn-mini" type="button" onclick="paNbNewNoteOpen()">＋ 创建笔记</button>'
      +   '</div>'
      +   '<div id="paNbAddMenu" class="pa-nb-add" hidden>'
      +     '<button class="pa-btn pa-btn-mini" type="button" onclick="paNbAddTextOpen()">📝 文本</button>'
      +     '<button class="pa-btn pa-btn-mini" type="button" onclick="paNbAddUrlOpen()">🔗 网址</button>'
      +     '<button class="pa-btn pa-btn-mini" type="button" onclick="paNbAddPdfPick()">📄 PDF</button>'
      +     '<button class="pa-btn pa-btn-mini" type="button" onclick="paNbVoice()">🎤 语音</button>'
      +     '<button class="pa-btn pa-btn-mini" type="button" onclick="paNbScreen()">🎬 录屏</button>'
      +     '<button class="pa-btn pa-btn-mini" type="button" onclick="paNbImport()">📚 导入 md</button>'
      +   '</div>'
      +   '<input id="paNbPdf" type="file" accept="application/pdf,.pdf" hidden onchange="paNbAddPdf(event)">'
      +   '<div class="pa-nb-scroll"><div id="paNbSources" class="pa-nb-sources"></div></div>'
      +   '<div id="paBrainStatus" class="pa-nb-msg">正在读笔记本…</div>'
      + '</aside>'
      + '<main class="pa-nb-main">'
      +   '<div class="pa-nb-main-h"><span id="paNbEmoji" class="em">📘</span>'
      +     '<div class="tt"><div id="paNbTitle" class="nm">第二大脑</div><div id="paNbSub" class="sb">—</div></div>'
      +     '<button id="paNbEditBtn" class="pa-btn pa-btn-mini pa-btn-ghost" type="button" onclick="paNbEditOpen()" title="笔记本设置">⚙</button></div>'
      +   '<div id="paNbChat" class="pa-nb-chat"></div>'
      +   '<div class="pa-nb-composer"><textarea id="paNbQ" placeholder="问本笔记本：核心结论？有哪些数字和日期？有哪些风险？" aria-label="问本笔记本"></textarea>'
      +     '<button id="paNbAskBtn" class="pa-btn pa-btn-main" type="button" onclick="paNbAsk()">问</button></div>'
      +   '<div class="pa-nb-foot"><span id="paNbQCount">0 个来源</span> · 答案只引用勾选来源；[n] 点开原文。模型不可用时会照实说。</div>'
      + '</main>'
      + '<aside class="pa-nb-col pa-nb-right">'
      +   '<div class="pa-nb-h"><b>Studio</b><span style="font-size:10.5px">由本笔记本生成</span></div>'
      +   '<div id="paNbTabs" class="pa-nb-grid">'
      +     '<button class="pa-nb-tile on" type="button" data-kind="summary" onclick="paNbStudioTab(\'summary\')"><span>📝</span>摘要</button>'
      +     '<button class="pa-nb-tile" type="button" data-kind="report" onclick="paNbStudioTab(\'report\')"><span>📊</span>报告</button>'
      +     '<button class="pa-nb-tile" type="button" data-kind="flashcards" onclick="paNbStudioTab(\'flashcards\')"><span>🃏</span>闪卡</button>'
      +     '<button class="pa-nb-tile" type="button" data-kind="quiz" onclick="paNbStudioTab(\'quiz\')"><span>❓</span>测验</button>'
      +     '<button class="pa-nb-tile" type="button" data-kind="mindmap" onclick="paNbStudioTab(\'mindmap\')"><span>🧠</span>思维导图</button>'
      +     '<button class="pa-nb-tile" type="button" data-kind="slides" onclick="paNbStudioTab(\'slides\')"><span>📑</span>演示文稿</button>'
      +     '<button class="pa-nb-tile" type="button" data-kind="datatable" onclick="paNbStudioTab(\'datatable\')"><span>📋</span>数据表格</button>'
      +     '<button class="pa-nb-tile off" type="button" disabled title="未实现：需要本机 TTS"><span>🎧</span>音频概览</button>'
      +     '<button class="pa-nb-tile off" type="button" disabled title="未实现：需要视频渲染"><span>🎬</span>视频概览</button>'
      +     '<button class="pa-nb-tile off" type="button" disabled title="未实现：需要图形生成"><span>📈</span>信息图</button>'
      +   '</div>'
      +   '<div class="pa-nb-gen"><button id="paNbGenBtn" class="pa-btn pa-btn-main" type="button" onclick="paNbStudioGen()">生成摘要</button></div>'
      +   '<div id="paNbOut" class="pa-nb-out"><div class="pa-nb-empty">选一个类型，点「生成」。产出可存回本笔记本。</div></div>'
      +   '<div class="pa-nb-msg" style="border-top:1px solid var(--border)"><button id="paNbSaveOut" class="pa-btn pa-btn-mini" type="button" onclick="paNbSaveStudio()" hidden>存为笔记</button></div>'
      +   '<div class="pa-nb-recent"><div class="pa-nb-h" style="padding:7px 10px"><b>最近产出</b></div><div id="paNbOutputs"></div></div>'
      + '</aside>'
      + '</div>';
  };

  window.paBrainMount = function(){ return paNbRefresh(); };

  /* ---------- 数据 ---------- */
  async function paNbLoadNotebooks(){
    var d = await req('/v9/pa/notebooks');
    NB.notebooks = Array.isArray(d.notebooks) ? d.notebooks : [];
    if(NB.cur && !NB.notebooks.some(function(x){ return x.id === NB.cur; })) NB.cur = '';
    if(!NB.cur && NB.notebooks.length) NB.cur = NB.notebooks[0].id;
  }
  async function paNbLoadAllCount(){
    var d = await req('/v9/pa/notes?limit=200');
    NB.total = (d.notes || []).length;
  }
  async function paNbLoadLabels(){
    try{
      var d = await req('/v9/pa/labels');
      NB.labels = d.labels || [];
    }catch(e){ NB.labels = []; }
  }
  async function paNbLoadSources(){
    if(!NB.cur){
      var a = await req('/v9/pa/notes?limit=200');
      NB.sources = a.notes || [];
    }else{
      var d = await req('/v9/pa/notebooks/' + encodeURIComponent(NB.cur) + '/sources');
      NB.sources = d.sources || [];
    }
    var ids = NB.sources.map(function(x){ return x.id; });
    var sel = NB.sel[NB.cur];
    NB.sel[NB.cur] = Array.isArray(sel) ? sel.filter(function(id){ return ids.indexOf(id) >= 0; }) : ids.slice();
  }
  function paNbSelectedIds(){
    var ids = NB.sources.map(function(x){ return x.id; });
    var sel = NB.sel[NB.cur] || [];
    return sel.filter(function(id){ return ids.indexOf(id) >= 0; });
  }
  window.paNbToggleSel = function(id){
    var sel = (NB.sel[NB.cur] || []).slice();
    var i = sel.indexOf(id);
    if(i >= 0) sel.splice(i, 1); else sel.push(id);
    NB.sel[NB.cur] = sel;
    paNbRenderSources(); paNbRenderHeader();
  };
  window.paNbSelAll = function(){
    var ids = NB.sources.map(function(x){ return x.id; });
    var sel = paNbSelectedIds();
    NB.sel[NB.cur] = (ids.length && sel.length === ids.length) ? [] : ids.slice();
    paNbRenderSources(); paNbRenderHeader();
  };

  /* ---------- 标签视图 / 管理（对标 Gemini Notebook 的 label 菜单） ---------- */
  window.paNbLabelMenuOpen = function(){
    paNbModal('来源标签',
      '<div class="pa-hint">标签是来源的分组；一个来源一个标签。可自动整理，也可手动建标签、把来源移到别的标签。</div>'
      + '<div class="pa-nb-row" style="margin:10px 0;flex-direction:column">'
      + '<button class="pa-btn pa-btn-main" type="button" onclick="paNbReorganizeNow()">一键整理全部（自动标签）</button>'
      + '<button class="pa-btn" type="button" onclick="paNbAddLabelDialog()">添加新标签</button>'
      + '<button class="pa-btn" type="button" onclick="paNbUnlabelAuto()">撤销自动标签</button>'
      + '<button class="pa-btn" type="button" onclick="paNbToggleView()">' + (NB.view === 'list' ? '返回到标签视图' : '返回到列表视图') + '</button>'
      + '</div>',
      '<button class="pa-btn" type="button" onclick="paNbModalClose()">关闭</button>');
  };
  window.paNbReorganizeNow = function(){
    paNbModalClose();
    paNbModal('整理全部（自动分类归档）',
      '<div class="pa-hint">正在后台整理全部笔记；可关窗口，完成后标签自动刷新。全部来源视图里能看到所有标签。</div>'
      + '<div id="paNbOrgProg"><div class="pa-nb-bar"><i id="paNbOrgBar"></i></div>'
      + '<div id="paNbOrgMsg" class="pa-hint">启动中…</div></div>'
      + '<div id="paNbOrgCats"></div>',
      '<button class="pa-btn" type="button" onclick="paNbModalClose()">关闭</button>');
    paNbOrganizeAll(false);
  };
  window.paNbShowAllSources = function(){
    paNbModalClose();
    paNbSelect('', true);
  };
  window.paNbToggleView = function(){
    NB.view = NB.view === 'list' ? 'label' : 'list';
    try{ localStorage.setItem('pa_nb_src_view_v1', NB.view); }catch(e){}
    paNbModalClose(); paNbRenderSources();
    msg(NB.view === 'list' ? '列表视图' : '标签视图');
  };
  window.paNbAddLabelDialog = function(){
    paNbModalClose();
    paNbModal('添加新标签',
      '<div class="pa-hint">空标签也可以先建；之后把来源「移至」它。</div>'
      + '<input id="paNbNewLabel" placeholder="标签名：合规与认证标准 / 渠道打法…">',
      '<button class="pa-btn" type="button" onclick="paNbModalClose()">取消</button>'
      + '<button class="pa-btn pa-btn-main" type="button" onclick="paNbAddLabelSave()">建立</button>');
    setTimeout(function(){ var e=$('paNbNewLabel'); if(e) e.focus(); }, 50);
  };
  window.paNbAddLabelSave = async function(){
    var e = $('paNbNewLabel'), name = e ? e.value.trim() : '';
    if(!name){ msg('先填标签名'); return; }
    try{
      await req('/v9/pa/labels', {method:'POST', body:{name:name}});
      paNbModalClose(); await paNbLoadLabels(); paNbRenderSources();
      msg('已建标签「' + name + '」');
    }catch(err){ msg('建不了：' + ((err && err.message) || err)); }
  };
  window.paNbUnlabelAuto = async function(){
    if(!window.confirm('撤销所有「自动整理」打上的标签？手动指定的标签会保留。')) return;
    try{
      var d = await req('/v9/pa/notes/unlabel_auto', {method:'POST'});
      paNbModalClose(); await paNbOrgRefresh();
      msg('已撤销自动标签（' + (d.cleared || 0) + ' 条）');
    }catch(e){ msg('撤销失败：' + ((e && e.message) || e)); }
  };
  window.paNbMoveLabel = function(id){
    paNbModalClose();
    var names = {};
    (NB.labels || []).forEach(function(l){ if(l.name) names[l.name] = 1; });
    (NB.sources || []).forEach(function(n){ if(n.category) names[n.category] = 1; });
    var options = [{v:'', t:'未分类'}].concat(Object.keys(names).map(function(k){ return {v:k, t:k}; }));
    var seen = {};
    options = options.filter(function(o){ if(seen[o.v]) return false; seen[o.v]=1; return true; });
    var btns = options.map(function(o){
      return '<button class="pa-btn" type="button" style="width:100%;justify-content:flex-start" onclick="paNbMoveLabelSave(\'' + esc(id) + '\',\'' + esc(o.v) + '\')">' + esc(o.t) + '</button>';
    }).join('');
    paNbModal('移至标签',
      '<div class="pa-hint">把这条来源移到哪个标签？</div><div class="pa-nb-row" style="flex-direction:column;margin-top:8px">' + btns + '</div>'
      + '<button class="pa-btn pa-btn-mini" type="button" onclick="paNbAddLabelDialog()" style="margin-top:8px">＋ 新建标签</button>',
      '<button class="pa-btn" type="button" onclick="paNbModalClose()">取消</button>');
  };
  window.paNbMoveLabelSave = async function(id, label){
    try{
      await req('/v9/pa/notes/' + encodeURIComponent(id) + '/label', {method:'POST', body:{category:label || ''}});
      paNbModalClose(); await paNbOrgRefresh();
      msg(label ? ('已移到「' + label + '」') : '已移到未分类');
    }catch(e){ msg('移动失败：' + ((e && e.message) || e)); }
  };

  /* ---------- 整理：一键自动分类归档（标签下多篇关联） ---------- */
  window.paNbOrganizeOpen = function(){
    paNbModalClose();
    paNbModal('整理笔记（自动分类归档）',
      '<div class="pa-hint">一键分析全部笔记：生成摘要 → 抽关键词 → 自动归到标签；同一标签下会关联多篇来源。可重复运行，重新关联归档。</div>'
      + '<div class="pa-nb-cfg-grid"><div><div class="pa-nb-cfg-l">全部</div><div class="pa-nb-chip">' + NB.sources.length + ' 条</div></div>'
      + '<div><div class="pa-nb-cfg-l">进度</div><div class="pa-nb-chip" id="paNbOrgCount">未开始</div></div></div>'
      + '<div class="pa-nb-row" style="margin:10px 0">'
      + '<button class="pa-btn pa-btn-main" type="button" id="paNbOrgStart" onclick="paNbOrganizeAll(false)">一键整理全部</button>'
      + '<button class="pa-btn" type="button" onclick="paNbOrganizeAll(true)">只补未分类</button></div>'
      + '<div id="paNbOrgProg" hidden><div class="pa-nb-bar"><i id="paNbOrgBar"></i></div>'
      + '<div id="paNbOrgMsg" class="pa-hint"></div></div>'
      + '<div id="paNbOrgCats"></div>',
      '<button class="pa-btn" type="button" onclick="paNbModalClose()">关闭</button>');
    paNbOrganizePoll(true);
  };
  window.paNbOrganizeAll = async function(only){
    try{
      var d = await req('/v9/pa/notes/organize_all', {method:'POST', body:{only_uncategorized:!!only}});
      if(!d.running && !d.total){ msg('没有可整理的笔记'); return; }
      var p = $('paNbOrgProg'); if(p) p.hidden = false;
      paNbOrganizePoll();
    }catch(e){ msg('启动整理失败：' + ((e && e.message) || e)); }
  };
  window.paNbOrganizeRun = function(scope){ return paNbOrganizeAll(scope === 'uncat'); };
  window.paNbOrganizePoll = async function(silent){
    try{
      var rr = await fetch(api('/v9/pa/notes/organize_status?ts=' + Date.now()), {cache:'no-store'});
      var d = await rr.json();
      var total = Number(d.total) || 0, done = Number(d.done) || 0;
      var running = !!d.running;
      var p = $('paNbOrgProg'); if(p && total) p.hidden = false;
      var bar = $('paNbOrgBar'); if(bar && total) bar.style.width = Math.min(100, Math.round(done * 100 / total)) + '%';
      var m = $('paNbOrgMsg');
      if(m){
        if(running) m.textContent = '正在整理 ' + done + '/' + total + '…（后台本地模型）';
        else if(d.error) m.textContent = '出错：' + d.error;
        else if(total){
          m.innerHTML = '已完成 ' + done + '/' + total + '；标签已自动重新关联。'
            + (NB.cur ? ' <button class="pa-btn pa-btn-mini" type="button" onclick="paNbShowAllSources()">查看全部来源</button>' : '');
        }
        else if(!silent) m.textContent = '还没有开始整理。';
      }
      var c = $('paNbOrgCount');
      if(c) c.textContent = total ? (done + '/' + total) : '未开始';
      paNbOrgCats(d.categories || {});
      if(running){
        setTimeout(function(){ paNbOrganizePoll(true); }, 1500);
      }else if(total && done){
        await paNbOrgRefresh();
      }
    }catch(e){
      if(!silent) msg('读不到整理进度：' + ((e && e.message) || e));
    }
  };
  function paNbOrgRender(){}
  function paNbOrgCats(counts){
    var box = $('paNbOrgCats'); if(!box) return;
    var names = Object.keys(counts || {});
    if(!names.length){ box.innerHTML = ''; return; }
    box.innerHTML = '<div class="pa-nb-cfg-l">自动标签（多篇关联）</div><div>'
      + names.map(function(k){ return '<span class="pa-nb-chip">' + esc(k) + ' ×' + counts[k] + '</span>'; }).join(' ')
      + '</div>';
  }
  window.paNbOrgApply = async function(id, nbId){
    try{
      await req('/v9/pa/notes/' + encodeURIComponent(id), {method:'PATCH', body:{notebook_id:nbId}});
      (NB.org || []).forEach(function(x){ if(x.id === id) x.applied = true; });
      paNbOrgRender();
      await paNbOrgRefresh();
    }catch(e){ msg('加入失败：' + ((e && e.message) || e)); }
  };
  window.paNbOrgNew = async function(id, title){
    try{
      var d = await req('/v9/pa/notebooks', {method:'POST', body:{title:title || '未分类', emoji:'📘'}});
      await req('/v9/pa/notes/' + encodeURIComponent(id), {method:'PATCH', body:{notebook_id:d.notebook.id}});
      (NB.org || []).forEach(function(x){ if(x.id === id) x.applied = true; });
      paNbOrgRender();
      await paNbOrgRefresh();
    }catch(e){ msg('建本/加入失败：' + ((e && e.message) || e)); }
  };
  async function paNbOrgRefresh(){
    await paNbLoadNotebooks(); await paNbLoadAllCount(); await paNbLoadLabels(); paNbRenderList();
    await paNbSelect(NB.cur, true);
  }
  function paNbCurrent(){
    for(var i=0;i<NB.notebooks.length;i++) if(NB.notebooks[i].id === NB.cur) return NB.notebooks[i];
    return null;
  }

  async function paNbRefresh(){
    try{
      await paNbLoadNotebooks();
      await paNbLoadAllCount();
      paNbRenderList();
      await paNbSelect(NB.cur, true);
      msg(NB.cur ? '' : '这是「全部来源」视图；新建一个笔记本，把资料收进去后即可限定问答。');
    }catch(e){ msg('读不到：' + ((e && e.message) || e)); }
  }

  /* ---------- 左栏 ---------- */
  function paNbRenderList(){
    var box = $('paNbList'); if(!box) return;
    var items = [{id:'', emoji:'🗂', title:'全部来源', source_count:NB.total}].concat(NB.notebooks);
    box.innerHTML = items.map(function(n){
      var on = (String(n.id || '') === NB.cur) ? ' on' : '';
      return '<div class="pa-nb-item' + on + '" onclick="paNbSelect(\'' + esc(n.id || '') + '\')" title="' + esc(n.title) + '">'
        + '<span class="em">' + esc(n.emoji || '📘') + '</span>'
        + '<span class="tt"><span class="nm">' + esc(n.title || '未命名') + '</span>'
        + '<span class="ct">' + (Number(n.source_count) || 0) + ' 个来源</span></span></div>';
    }).join('');
  }

  function paNbRenderHeader(){
    var nb = paNbCurrent(), seln = paNbSelectedIds().length, total = NB.sources.length;
    if($('paNbEmoji')) $('paNbEmoji').textContent = NB.cur ? (nb && nb.emoji || '📘') : '🗂';
    if($('paNbTitle')) $('paNbTitle').textContent = NB.cur ? ((nb && nb.title) || '未命名') : '全部来源';
    if($('paNbSub')) $('paNbSub').textContent = NB.cur
      ? (seln + '/' + total + ' 个来源 · 问答只引勾选')
      : (NB.total + ' 条笔记 · 跨全部笔记');
    if($('paNbQCount')) $('paNbQCount').textContent = seln + ' 个来源';
    if($('paNbEditBtn')) $('paNbEditBtn').hidden = !NB.cur;
    if($('paNbSelAllBtn')) $('paNbSelAllBtn').textContent = (total && seln === total) ? '取消全选' : '全选';
    if($('paNbAskBtn')) $('paNbAskBtn').disabled = (!seln || NB.busy);
  }

  function paNbGroupSources(){
    var map = {}, order = [];
    function ensure(name){
      if(!map[name]){ map[name] = {name:name, items:[]}; order.push(name); }
    }
    (NB.labels || []).forEach(function(l){ ensure(String(l.name || '').trim()); });
    NB.sources.forEach(function(n){
      var cat = String(n.category || '').trim() || '未分类';
      ensure(cat);
      map[cat].items.push(n);
    });
    order.sort(function(a, b){
      if(a === '未分类') return 1;
      if(b === '未分类') return -1;
      return (map[b].items.length - map[a].items.length) || a.localeCompare(b, 'zh');
    });
    return order.filter(function(k){ return k; }).map(function(k){ return map[k]; });
  }
  function paNbSourceRow(n, sel, child){
    var on = sel.indexOf(n.id) >= 0;
    return '<div class="pa-nb-src' + (child ? ' child' : '') + (on ? '' : ' off') + '" onclick="paNbOpenSource(\'' + esc(n.id) + '\')" title="' + esc(n.title) + '">'
      + '<input class="ck" type="checkbox" ' + (on ? 'checked' : '') + ' aria-label="选中来源" onclick="event.stopPropagation();paNbToggleSel(\'' + esc(n.id) + '\')">'
      + '<span class="ic">' + iconOf(n.source) + '</span>'
      + '<span class="bd"><span class="nm">' + esc(n.title || '未命名') + '</span>'
      + '<span class="mt">' + esc(fmtDate(n.updated)) + '</span></span>'
      + '<button class="x" type="button" title="删除来源" onclick="event.stopPropagation();paNbDeleteSource(\'' + esc(n.id) + '\')">×</button>'
      + '</div>';
  }
  function paNbRenderSources(){
    var box = $('paNbSources'); if(!box) return;
    if($('paNbSrcCount')) $('paNbSrcCount').textContent = '· ' + NB.sources.length;
    if(!NB.sources.length){
      box.innerHTML = '<div class="pa-nb-empty">' + (NB.cur
        ? '还没有来源。点上方「＋」加文本／网址／PDF，或语音、录屏。'
        : '还没有笔记。新建一个笔记本，再添加来源。') + '</div>';
      return;
    }
    var sel = NB.sel[NB.cur] || [];
    if(NB.view === 'list'){
      box.innerHTML = NB.sources.map(function(n){ return paNbSourceRow(n, sel, false); }).join('');
      return;
    }
    var groups = paNbGroupSources();
    NB.groups = groups;
    box.innerHTML = groups.map(function(g, gi){
      var on = g.items.length > 0 && g.items.every(function(n){ return sel.indexOf(n.id) >= 0; });
      var closed = !!(NB.closedCats && NB.closedCats[g.name]);
      var rows = g.items.map(function(n){ return paNbSourceRow(n, sel, true); }).join('');
      return '<div class="pa-nb-cat">'
        + '<button class="ar" type="button" onclick="paNbToggleCatOpen(' + gi + ')">' + (closed ? '▶' : '▼') + '</button>'
        + '<input class="ck" type="checkbox" ' + (on ? 'checked' : '') + ' title="选中整个标签" onclick="event.stopPropagation();paNbToggleCat(' + gi + ')">'
        + '<span class="nm" onclick="paNbToggleCatOpen(' + gi + ')">' + esc(g.name) + '</span>'
        + '<span class="ct">' + g.items.length + '</span></div>'
        + '<div class="pa-nb-cat-items"' + (closed ? ' hidden' : '') + '>' + rows + '</div>';
    }).join('');
  }
  window.paNbToggleCatOpen = function(gi){
    var g = (NB.groups || [])[gi]; if(!g) return;
    NB.closedCats = NB.closedCats || {};
    NB.closedCats[g.name] = !NB.closedCats[g.name];
    paNbRenderSources();
  };
  window.paNbToggleCat = function(gi){
    var g = (NB.groups || [])[gi]; if(!g) return;
    var sel = (NB.sel[NB.cur] || []).slice();
    var all = g.items.every(function(n){ return sel.indexOf(n.id) >= 0; });
    g.items.forEach(function(n){
      var i = sel.indexOf(n.id);
      if(all && i >= 0) sel.splice(i, 1);
      else if(!all && i < 0) sel.push(n.id);
    });
    NB.sel[NB.cur] = sel;
    paNbRenderSources(); paNbRenderHeader();
  };

  /* ---------- 选笔记本 / 加载 ---------- */
  window.paNbSelect = async function(id, keep){
    id = String(id == null ? '' : id);
    if(id === NB.cur && !keep) return;
    NB.cur = id;
    paNbRenderList();
    try{
      await paNbLoadSources();
      await paNbLoadLabels();
      paNbRenderHeader();
      paNbRenderSources();
      paNbRenderChat();
      paNbRenderStudio();
      paNbLoadOutputs();
      msg(NB.cur ? ('已选「' + ((paNbCurrent() || {}).title || '') + '」') : '全部来源视图');
    }catch(e){ msg('读不到来源：' + ((e && e.message) || e)); }
  };

  window.paNbCreateOpen = function(){
    var f = $('paNbCreate'); if(f) f.hidden = false;
    var t = $('paNbCreateTitle'); if(t){ t.value = ''; t.focus(); }
  };
  window.paNbCreateCancel = function(){ var f = $('paNbCreate'); if(f) f.hidden = true; };
  window.paNbCreateSave = async function(){
    var t = $('paNbCreateTitle'), e = $('paNbCreateEmoji');
    var title = t ? t.value.trim() : '';
    if(!title){ msg('先填笔记本名称'); if(t) t.focus(); return; }
    try{
      var d = await req('/v9/pa/notebooks', {method:'POST', body:{title:title, emoji:(e && e.value.trim()) || '📘'}});
      paNbCreateCancel();
      await paNbLoadNotebooks();
      paNbRenderList();
      await paNbSelect(d.notebook.id, true);
      msg('已建「' + d.notebook.title + '」');
    }catch(err){ msg('建不了：' + ((err && err.message) || err)); }
  };

  /* ---------- 模态框 ---------- */
  window.paNbModalClose = function(){ var m = document.querySelector('.pa-nb-modal'); if(m) m.remove(); };
  function paNbModal(title, body, foot){
    var ov = document.createElement('div'); ov.className = 'pa-nb-modal';
    ov.innerHTML = '<div class="pa-nb-mcard" role="dialog" aria-modal="true">'
      + '<div class="pa-nb-mh">' + esc(title) + '<button class="pa-btn pa-btn-mini pa-btn-ghost" type="button" onclick="paNbModalClose()">关闭</button></div>'
      + '<div class="pa-nb-mb">' + body + '</div><div class="pa-nb-mf">' + (foot || '') + '</div></div>';
    document.body.appendChild(ov); return ov;
  }
  window.paNbEditOpen = function(){
    var nb = paNbCurrent(); if(!nb){ msg('先选一个笔记本'); return; }
    paNbModal('笔记本设置',
      '<div style="font-size:11px;color:var(--sub)">图标</div><input id="paNbEditEmoji" maxlength="4" value="' + esc(nb.emoji || '📘') + '">'
      + '<div style="font-size:11px;color:var(--sub)">名称</div><input id="paNbEditTitle" value="' + esc(nb.title || '') + '">'
      + '<div style="font-size:11px;color:var(--sub)">说明</div><textarea id="paNbEditDesc" style="min-height:80px">' + esc(nb.description || '') + '</textarea>'
      + '<div style="font-size:11px;color:var(--sub)">删笔记本不删来源：来源会退回「未归档」。</div>',
      '<button class="pa-btn pa-btn-stop" type="button" onclick="paNbDeleteNotebook()">删除笔记本</button>'
      + '<button class="pa-btn" type="button" onclick="paNbModalClose()">取消</button>'
      + '<button class="pa-btn pa-btn-main" type="button" onclick="paNbEditSave()">保存</button>');
  };
  window.paNbEditSave = async function(){
    if(!NB.cur) return;
    try{
      var d = await req('/v9/pa/notebooks/' + encodeURIComponent(NB.cur), {method:'PATCH', body:{
        title: ($('paNbEditTitle') || {}).value || '', emoji: ($('paNbEditEmoji') || {}).value || '📘',
        description: ($('paNbEditDesc') || {}).value || ''}});
      paNbModalClose(); await paNbLoadNotebooks(); paNbRenderList(); paNbRenderHeader();
      msg('已保存「' + d.notebook.title + '」');
    }catch(e){ msg('保存失败：' + ((e && e.message) || e)); }
  };
  window.paNbDeleteNotebook = async function(){
    if(!NB.cur) return;
    if(!window.confirm('删除这个笔记本？来源会退回未归档，不会删笔记。')) return;
    try{
      var cur = NB.cur;
      var d = await req('/v9/pa/notebooks/' + encodeURIComponent(cur), {method:'DELETE'});
      paNbModalClose(); NB.cur = '';
      await paNbLoadNotebooks(); await paNbLoadAllCount(); paNbRenderList();
      await paNbSelect(NB.cur, true);
      msg('已删；' + (d.moved_sources || 0) + ' 个来源退回未归档');
    }catch(e){ msg('删不了：' + ((e && e.message) || e)); }
  };
  async function paNbEnsureNotebooks(){
    if(NB.notebooks.length) return;
    try{ await paNbLoadNotebooks(); paNbRenderList(); }catch(e){}
  }
  async function paNbEnsureSink(){
    if(NB.notebooks.length) return false;
    try{
      var d = await req('/v9/pa/notebooks', {method:'POST', body:{title:'未归档', emoji:'📥'}});
      await paNbLoadNotebooks(); paNbRenderList();
      await paNbSelect(d.notebook.id, true);
      return true;
    }catch(e){ return false; }
  }
  window.paNbAddOpen = async function(){
    var wasAll = !NB.cur;
    await paNbEnsureNotebooks();
    var sink = await paNbEnsureSink();
    if((wasAll && !sink) || !NB.cur){ paNbPickNotebook('add'); return; }
    paNbSourceDialog();
  };
  function paNbPickNotebook(mode){
    NB.pickMode = mode || 'add';
    if(!NB.notebooks.length){ paNbNeedNotebookDialog(); return; }
    var items = NB.notebooks.map(function(n){
      return '<div class="pa-nb-item" onclick="paNbPickForSource(\'' + esc(n.id) + '\')">'
        + '<span class="em">' + esc(n.emoji || '📘') + '</span><span class="tt"><span class="nm">'
        + esc(n.title || '未命名') + '</span><span class="ct">' + (Number(n.source_count) || 0) + ' 个来源</span></span></div>';
    }).join('');
    paNbModal('先选一个笔记本',
      '<div class="pa-hint">要加到哪一本？选完就打开添加来源。</div><div class="pa-nb-list" style="padding:0">' + items + '</div>',
      '<button class="pa-btn" type="button" onclick="paNbModalClose()">取消</button>'
      + '<button class="pa-btn pa-btn-main" type="button" onclick="paNbNeedNotebookDialog()">新建笔记本</button>');
  }
  function paNbNeedNotebookDialog(){
    paNbModal('先建一个笔记本',
      '<div class="pa-hint">还没有笔记本。建一个，再把它当作资料的容器。</div>'
      + '<input id="paNbQuickTitle" placeholder="笔记本名称：客户 / 学习 / 项目…">',
      '<button class="pa-btn" type="button" onclick="paNbModalClose()">取消</button>'
      + '<button class="pa-btn pa-btn-main" type="button" onclick="paNbQuickCreate()">建立并继续</button>');
    setTimeout(function(){ var i=$('paNbQuickTitle'); if(i) i.focus(); }, 50);
  }
  window.paNbPickForSource = async function(id){
    paNbModalClose();
    await paNbSelect(String(id), true);
    if(NB.pickMode === 'note') paNbNewNoteOpen(); else paNbSourceDialog();
  };
  window.paNbQuickCreate = async function(){
    var i = $('paNbQuickTitle');
    var title = i ? i.value.trim() : '';
    if(!title){ msg('先填笔记本名称'); if(i) i.focus(); return; }
    try{
      var d = await req('/v9/pa/notebooks', {method:'POST', body:{title:title, emoji:'📘'}});
      paNbModalClose();
      await paNbLoadNotebooks(); paNbRenderList();
      await paNbSelect(d.notebook.id, true);
      if(NB.pickMode === 'note') paNbNewNoteOpen(); else paNbSourceDialog();
    }catch(e){ msg('建不了：' + ((e && e.message) || e)); }
  };
  var SRC_TAB = 'file';
  function paNbSourceDialog(){
    var foot = '<button class="pa-btn" type="button" onclick="paNbModalClose()">完成</button>';
    paNbModal('添加来源',
      '<div class="pa-nb-src-tabs">'
      + '<button class="pa-nb-tab" data-t="file" type="button" onclick="paNbSrcTab(\'file\')">上传文件</button>'
      + '<button class="pa-nb-tab" data-t="url" type="button" onclick="paNbSrcTab(\'url\')">网站</button>'
      + '<button class="pa-nb-tab" data-t="text" type="button" onclick="paNbSrcTab(\'text\')">复制的文字</button>'
      + '<button class="pa-nb-tab" data-t="voice" type="button" onclick="paNbSrcTab(\'voice\')">语音</button>'
      + '<button class="pa-nb-tab" data-t="screen" type="button" onclick="paNbSrcTab(\'screen\')">录屏</button>'
      + '</div><div id="paNbSrcBody"></div>'
      + '<div class="pa-nb-src-foot" id="paNbSrcFoot">共 ' + NB.sources.length + ' 个来源（上限 200）</div>',
      foot);
    paNbSrcTab(SRC_TAB);
  }
  window.paNbSrcTab = function(tab){
    SRC_TAB = tab || 'file';
    document.querySelectorAll('.pa-nb-src-tabs .pa-nb-tab').forEach(function(b){
      b.classList.toggle('on', b.getAttribute('data-t') === SRC_TAB);
    });
    var box = $('paNbSrcBody'); if(!box) return;
    if(SRC_TAB === 'file'){
      box.innerHTML = '<label class="pa-nb-drop" id="paNbDrop" ondragover="event.preventDefault();this.classList.add(\'on\')"'
        + ' ondragleave="this.classList.remove(\'on\')" ondrop="paNbSrcDrop(event)">'
        + '<div style="font-size:22px">⇪</div><div>拖放文件到这里，或点此选择</div>'
        + '<div class="pa-hint">支持 PDF / Markdown / TXT；PDF 在本机抽文字，单文件 ≤ 50 MB</div>'
        + '<input id="paNbSrcFile" type="file" accept=".pdf,.md,.markdown,.txt,application/pdf,text/plain,text/markdown" hidden onchange="paNbSrcFile(this)"></label>'
        + '<div id="paNbSrcMsg" class="pa-hint"></div>';
      var d = $('paNbDrop'); if(d) d.onclick = function(){ var f=$('paNbSrcFile'); if(f) f.click(); };
    }else if(SRC_TAB === 'url'){
      box.innerHTML = '<div class="pa-hint">公开 http/https 网址（不收本机/内网地址）</div>'
        + '<input id="paNbUrlIn" placeholder="https://…" autocomplete="off">'
        + '<button class="pa-btn pa-btn-main" type="button" onclick="paNbAddUrlSave()">抓取并添加</button>'
        + '<div id="paNbSrcMsg" class="pa-hint"></div>';
    }else if(SRC_TAB === 'text'){
      box.innerHTML = '<div class="pa-hint">标题</div><input id="paNbTextTitle" placeholder="例如：客户会议纪要">'
        + '<div class="pa-hint">正文</div><textarea id="paNbTextBody" placeholder="粘贴资料正文…"></textarea>'
        + '<button class="pa-btn pa-btn-main" type="button" onclick="paNbAddTextSave()">添加</button>'
        + '<div id="paNbSrcMsg" class="pa-hint"></div>';
    }else if(SRC_TAB === 'voice'){
      box.innerHTML = '<div class="pa-hint">本机录音 → 本地转写 → 存入本笔记本。不联网、不上传。</div>'
        + '<button class="pa-btn pa-btn-main" type="button" onclick="paNbVoice()">开始录音</button>';
    }else{
      box.innerHTML = '<div class="pa-hint">本机录屏 → 本地转写/关键帧 → 存入本笔记本。只录你选的窗口。</div>'
        + '<button class="pa-btn pa-btn-main" type="button" onclick="paNbScreen()">选择窗口/屏幕</button>';
    }
  };
  function paNbSrcdlgMsg(t){ var e=$('paNbSrcMsg'); if(e) e.textContent = String(t == null ? '' : t); }
  window.paNbSrcFile = function(inp){
    var f = inp && inp.files && inp.files[0];
    if(f) paNbSrcOneFile(f);
  };
  window.paNbSrcDrop = function(ev){
    ev.preventDefault();
    var d = $('paNbDrop'); if(d) d.classList.remove('on');
    var f = ev.dataTransfer && ev.dataTransfer.files && ev.dataTransfer.files[0];
    if(f) paNbSrcOneFile(f);
  };
  async function paNbSrcOneFile(f){
    if(!NB.cur){ paNbSrcdlgMsg('先选一个笔记本'); return; }
    var name = String(f.name || '');
    var low = name.toLowerCase();
    if(f.size > 50 * 1024 * 1024){ paNbSrcdlgMsg('文件太大（上限 50 MB）'); return; }
    paNbSrcdlgMsg('读取中…');
    try{
      if(low.endsWith('.pdf') || f.type === 'application/pdf'){
        var fd = new FormData(); fd.append('file', f, name);
        var d = await req('/v9/pa/notebooks/' + encodeURIComponent(NB.cur) + '/sources/pdf', {method:'POST', body:fd, form:true});
        paNbModalClose(); await paNbAfterAdd('已加 PDF（' + (d.chars || 0) + ' 字）', paNbSourceId(d));
      }else if(low.endsWith('.md') || low.endsWith('.markdown') || low.endsWith('.txt') || f.type.indexOf('text') === 0){
        var text = await f.text();
        if(!text.trim()){ paNbSrcdlgMsg('文件是空的'); return; }
        var df = await req('/v9/pa/notebooks/' + encodeURIComponent(NB.cur) + '/sources/text', {method:'POST', body:{
          title: name.replace(/\.[^.]+$/, ''), body: text, tags:['文件']}});
        paNbModalClose(); await paNbAfterAdd('已加文件来源：' + name, paNbSourceId(df));
      }else{
        paNbSrcdlgMsg('暂支持 PDF / MD / TXT；其它格式先转文本');
      }
    }catch(e){ paNbSrcdlgMsg('加不了：' + ((e && e.message) || e)); }
  }
  function paNbCloseAdd(){ var m = $('paNbAddMenu'); if(m) m.hidden = true; }
  window.paNbAddTextOpen = function(){
    if(!NB.cur) return; paNbCloseAdd();
    paNbModal('添加文本来源',
      '<div style="font-size:11px;color:var(--sub)">标题</div><input id="paNbTextTitle" placeholder="例如：客户会议纪要">'
      + '<div style="font-size:11px;color:var(--sub)">正文</div><textarea id="paNbTextBody" placeholder="粘贴资料正文…"></textarea>',
      '<button class="pa-btn" type="button" onclick="paNbModalClose()">取消</button>'
      + '<button class="pa-btn pa-btn-main" type="button" onclick="paNbAddTextSave()">添加</button>');
  };
  window.paNbAddTextSave = async function(){
    var t = $('paNbTextTitle'), b = $('paNbTextBody');
    var body = b ? b.value.trim() : '';
    if(!body){ msg('正文为空'); return; }
    try{
      var dt = await req('/v9/pa/notebooks/' + encodeURIComponent(NB.cur) + '/sources/text', {method:'POST', body:{
        title: (t && t.value.trim()) || body.slice(0, 30), body: body, tags:['手动']}});
      paNbModalClose(); await paNbAfterAdd('已加文本来源', paNbSourceId(dt));
    }catch(e){ msg('加不了：' + ((e && e.message) || e)); }
  };
  window.paNbAddUrlOpen = function(){
    if(!NB.cur) return; paNbCloseAdd();
    paNbModal('添加网址来源',
      '<div style="font-size:11px;color:var(--sub)">公开 http/https 网址（不收本机/内网地址）</div>'
      + '<input id="paNbUrlIn" placeholder="https://…" autocomplete="off">',
      '<button class="pa-btn" type="button" onclick="paNbModalClose()">取消</button>'
      + '<button class="pa-btn pa-btn-main" type="button" onclick="paNbAddUrlSave()">抓取并添加</button>');
  };
  window.paNbAddUrlSave = async function(){
    var u = String((($('paNbUrlIn') || {}).value) || '').trim();
    if(!u){ msg('先填网址'); return; } msg('抓取网页…');
    try{
      var d = await req('/v9/pa/notebooks/' + encodeURIComponent(NB.cur) + '/sources/url', {method:'POST', body:{url:u}});
      paNbModalClose(); await paNbAfterAdd('已加网址（' + (d.chars || 0) + ' 字）', paNbSourceId(d));
    }catch(e){ msg('抓不了：' + ((e && e.message) || e)); }
  };
  window.paNbAddPdfPick = function(){
    if(!NB.cur) return; paNbCloseAdd();
    var f = $('paNbPdf'); if(f) f.click();
  };
  window.paNbAddPdf = async function(ev){
    var f = ev && ev.target, file = f && f.files && f.files[0];
    if(!file) return;
    if(!NB.cur){ msg('先选/新建一个笔记本'); return; }
    msg('读 PDF（本地抽文字）…');
    try{
      var fd = new FormData(); fd.append('file', file, file.name);
      var d = await req('/v9/pa/notebooks/' + encodeURIComponent(NB.cur) + '/sources/pdf', {method:'POST', body:fd, form:true});
      f.value = ''; await paNbAfterAdd('已加 PDF（' + (d.chars || 0) + ' 字）', paNbSourceId(d));
    }catch(e){ msg('PDF 读不了：' + ((e && e.message) || e)); }
  };
  window.paNbNewNoteOpen = async function(){
    var wasAll = !NB.cur;
    await paNbEnsureNotebooks();
    var sink = await paNbEnsureSink();
    if((wasAll && !sink) || !NB.cur){ paNbPickNotebook('note'); return; }
    paNbCloseAdd();
    paNbModal('创建笔记',
      '<div style="font-size:11px;color:var(--sub)">标题</div><input id="paNbNoteTitle" placeholder="笔记标题">'
      + '<div style="font-size:11px;color:var(--sub)">正文</div><textarea id="paNbNoteBody" placeholder="写点什么…"></textarea>',
      '<button class="pa-btn" type="button" onclick="paNbModalClose()">取消</button>'
      + '<button class="pa-btn pa-btn-main" type="button" onclick="paNbNewNoteSave()">创建</button>');
  };
  window.paNbNewNoteSave = async function(){
    var t = $('paNbNoteTitle'), b = $('paNbNoteBody');
    var body = b ? b.value.trim() : '';
    if(!body){ msg('正文为空'); return; }
    try{
      var dn = await req('/v9/pa/notebooks/' + encodeURIComponent(NB.cur) + '/sources/text', {method:'POST', body:{
        title: (t && t.value.trim()) || body.slice(0, 30), body: body, tags:['笔记']}});
      paNbModalClose(); await paNbAfterAdd('已创建笔记', paNbSourceId(dn));
    }catch(e){ msg('建不了：' + ((e && e.message) || e)); }
  };
  window.paNbVoice = function(){ paNbCloseAdd(); if(window.paBrainVoiceToggle) window.paBrainVoiceToggle(); };
  window.paNbScreen = function(){ paNbCloseAdd(); if(window.paScreenPick) window.paScreenPick(); };
  window.paNbImport = function(){ paNbCloseAdd(); if(window.paBrainImport) window.paBrainImport(); };
  async function paNbLoadOutputs(){
    var box = $('paNbOutputs'); if(!box) return;
    if(!NB.cur){ box.innerHTML = '<div class="pa-nb-empty" style="padding:8px 10px">选一个笔记本</div>'; return; }
    try{
      var d = await req('/v9/pa/notebooks/' + encodeURIComponent(NB.cur) + '/outputs');
      var arr = d.outputs || [];
      box.innerHTML = arr.length ? arr.map(function(o){
        return '<div class="pa-nb-out-item" onclick="paNbOpenSource(\'' + esc(o.id) + '\')">'
          + '<div class="nm">' + esc(o.title || '未命名') + '</div>'
          + '<div class="mt">' + esc(o.kind || 'Studio') + ' · ' + esc(fmtDate(o.updated)) + '</div></div>';
      }).join('') : '<div class="pa-nb-empty" style="padding:8px 10px">还没有产出</div>';
    }catch(e){ box.innerHTML = '<div class="pa-nb-empty" style="padding:8px 10px">读不到产出</div>'; }
  }
  function paNbSourceId(d){
    if(!d) return '';
    if(d.source && d.source.id) return d.source.id;
    if(d.note && d.note.id) return d.note.id;
    return d.id || '';
  }
  async function paNbAutoLabel(id){
    if(!id) return;
    try{
      await req('/v9/pa/notes/' + encodeURIComponent(id) + '/classify', {method:'POST'});
      await paNbLoadLabels();
      await paNbLoadSources();
      paNbRenderSources(); paNbRenderHeader();
    }catch(e){ /* 模型不可用时静默，用户可手动整理 */ }
  }
  async function paNbAfterAdd(text, nid){
    await paNbLoadNotebooks(); await paNbLoadAllCount(); await paNbLoadLabels(); paNbRenderList();
    NB.sel[NB.cur] = null;
    await paNbSelect(NB.cur, true); msg(text);
    if(nid) paNbAutoLabel(nid);
  }
  window.paBrainLoad = function(){ return paNbRefresh(); };
  window.paNbOpenSource = async function(id){
    try{
      var d = await req('/v9/pa/notes/' + encodeURIComponent(id)), n = d.note || {};
      var foot = '<button class="pa-btn" type="button" onclick="paNbMoveLabel(\'' + esc(id) + '\')">移至标签</button>'
        + '<button class="pa-btn" type="button" onclick="paNbEditSource(\'' + esc(id) + '\')">编辑</button>'
        + '<button class="pa-btn" type="button" onclick="paNbModalClose()">关闭</button>';
      if(NB.cur && n.notebook_id === NB.cur)
        foot = '<button class="pa-btn pa-btn-ghost" type="button" onclick="paNbMoveOut(\'' + esc(id) + '\')">移出</button>' + foot;
      else if(!NB.cur)
        foot = '<button class="pa-btn pa-btn-ghost" type="button" onclick="paNbAddToNotebook(\'' + esc(id) + '\')">加入笔记本</button>' + foot;
      var enrich = '';
      if(n.category){
        enrich += '<div class="pa-nb-cfg-l">标签</div><div style="margin-bottom:8px"><span class="pa-nb-chip">' + esc(n.category) + '</span></div>';
      }
      if(n.summary){
        enrich += '<div class="pa-nb-enrich"><div class="pa-nb-cfg-l">摘要</div><div>' + esc(n.summary) + '</div></div>';
      }
      if(n.keywords && n.keywords.length){
        enrich += '<div class="pa-nb-cfg-l">关键词</div><div style="margin-bottom:8px">'
          + n.keywords.map(function(k){ return '<span class="pa-nb-chip">' + esc(k) + '</span>'; }).join(' ') + '</div>';
      }
      enrich += '<div style="margin-bottom:10px"><button class="pa-btn pa-btn-mini" type="button" onclick="paNbClassifyOne(\'' + esc(id) + '\')">'
        + (n.summary ? '重新整理摘要/关键词' : '整理：生成摘要与关键词') + '</button></div>';
      paNbModal(n.title || '来源',
        '<div style="font-size:11px;color:var(--sub);margin-bottom:8px">' + iconOf(n.source) + ' ' + esc(n.source || 'note')
        + ' · ' + esc(fmtDate(n.updated)) + (n.source_path ? ' · ' + esc(n.source_path) : '') + '</div>'
        + enrich
        + '<div style="white-space:pre-wrap">' + esc(n.body || '') + '</div>', foot);
    }catch(e){ msg('打不开：' + ((e && e.message) || e)); }
  };
  window.paNbClassifyOne = async function(id){
    msg('整理中…（本地模型）');
    try{
      var r = await req('/v9/pa/notes/' + encodeURIComponent(id) + '/classify', {method:'POST'});
      paNbModalClose();
      msg(r.model_ok ? '已生成摘要与关键词' : '模型不可用，已用抽取式摘要');
      await paNbOrgRefresh();
      await paNbOpenSource(id);
    }catch(e){ msg('整理失败：' + ((e && e.message) || e)); }
  };
  window.paNbEditSource = async function(id){
    try{
      var d = await req('/v9/pa/notes/' + encodeURIComponent(id)), n = d.note || {};
      paNbModal('编辑笔记',
        '<div class="pa-nb-cfg-l">标题</div><input id="paNbEditSrcTitle" value="' + esc(n.title || '') + '">'
        + '<div class="pa-nb-cfg-l">正文</div><textarea id="paNbEditSrcBody" style="min-height:240px">' + esc(n.body || '') + '</textarea>',
        '<button class="pa-btn" type="button" onclick="paNbModalClose()">取消</button>'
        + '<button class="pa-btn pa-btn-main" type="button" onclick="paNbEditSourceSave(\'' + esc(id) + '\')">保存</button>');
    }catch(e){ msg('打不开：' + ((e && e.message) || e)); }
  };
  window.paNbEditSourceSave = async function(id){
    var t = $('paNbEditSrcTitle'), b = $('paNbEditSrcBody');
    try{
      await req('/v9/pa/notes/' + encodeURIComponent(id), {method:'PATCH', body:{
        title: (t && t.value) || '', body: (b && b.value) || ''}});
      paNbModalClose(); await paNbAfterAdd('已保存笔记');
    }catch(e){ msg('保存失败：' + ((e && e.message) || e)); }
  };
  window.paNbMoveOut = async function(id){
    try{
      await req('/v9/pa/notes/' + encodeURIComponent(id), {method:'PATCH', body:{notebook_id:''}});
      paNbModalClose(); await paNbAfterAdd('已移出本笔记本');
    }catch(e){ msg('移不动：' + ((e && e.message) || e)); }
  };
  window.paNbAddToNotebook = function(id){
    if(!NB.notebooks.length){ msg('先建一个笔记本，再把这条笔记放进去'); return; }
    var opts = NB.notebooks.map(function(n){
      return '<option value="' + esc(n.id) + '">' + esc(n.emoji || '📘') + ' ' + esc(n.title || '未命名') + '</option>';
    }).join('');
    paNbModal('加入笔记本',
      '<div style="font-size:11px;color:var(--sub)">选一个笔记本；放进去后问答就只引该本来源。</div>'
      + '<select id="paNbMoveTo">' + opts + '</select>',
      '<button class="pa-btn" type="button" onclick="paNbModalClose()">取消</button>'
      + '<button class="pa-btn pa-btn-main" type="button" onclick="paNbMoveTo(\'' + esc(id) + '\')">加入</button>');
  };
  window.paNbMoveTo = async function(id){
    var sel = $('paNbMoveTo'); if(!sel || !sel.value) return;
    try{
      await req('/v9/pa/notes/' + encodeURIComponent(id), {method:'PATCH', body:{notebook_id:sel.value}});
      paNbModalClose();
      var target = sel.value;
      await paNbLoadNotebooks(); await paNbLoadAllCount(); paNbRenderList();
      NB.cur = target; await paNbSelect(target, true);
      msg('已加入笔记本');
    }catch(e){ msg('加不了：' + ((e && e.message) || e)); }
  };
  window.paNbDeleteSource = async function(id){
    if(!window.confirm('删除这个来源？对应笔记也会删。')) return;
    try{ await req('/v9/pa/notes/' + encodeURIComponent(id), {method:'DELETE'}); await paNbAfterAdd('已删来源'); }
    catch(e){ msg('删不了：' + ((e && e.message) || e)); }
  };
  function paNbChatKey(){ return 'pa_nb_chat_v1_' + (NB.cur || 'all'); }
  function paNbChatOf(){
    if(!NB.chat[NB.cur]){
      try{ var raw = localStorage.getItem(paNbChatKey()); NB.chat[NB.cur] = raw ? (JSON.parse(raw) || []) : []; }
      catch(e){ NB.chat[NB.cur] = []; }
    }
    return NB.chat[NB.cur];
  }
  function paNbSaveChat(){
    try{ localStorage.setItem(paNbChatKey(), JSON.stringify((NB.chat[NB.cur] || []).slice(-100))); }catch(e){}
  }
  function paNbCiteChips(cits){
    if(!cits || !cits.length) return '';
    return '<div class="pa-nb-cites">' + cits.map(function(c, i){
      return '<button class="pa-nb-chip" type="button" onclick="paNbOpenSource(\'' + esc(c.id) + '\')" title="' + esc(c.title) + '">['
        + (c.n || (i + 1)) + '] ' + esc(c.title || c.id) + '</button>';
    }).join('') + '</div>';
  }
  function paNbCiteMap(cits){
    var map = {}; (cits || []).forEach(function(c, i){ map[c.id] = c.n || (i + 1); }); return map;
  }
  function paNbInline(s, cits){
    var map = paNbCiteMap(cits);
    function cite(id, n){
      return '<button class="pa-nb-cite" type="button" onclick="paNbOpenSource(\'' + esc(id) + '\')" title="出处">[' + (n || '?') + ']</button>';
    }
    s = s.replace(/\[(\d{1,2})\]/g, function(_, n){
      var c = (cits || [])[Number(n) - 1];
      return c ? cite(c.id, n) : _;
    });
    s = s.replace(/\[note:([0-9a-zA-Z\-]+)\]/g, function(_, id){ return cite(id, map[id]); });
    s = s.replace(/\[([0-9]{8}-[0-9]{6}-[0-9a-f]{6})\]/g, function(_, id){ return cite(id, map[id]); });
    s = s.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
    var BT = String.fromCharCode(96);
    s = s.replace(new RegExp(BT + '([^' + BT + ']+)' + BT, 'g'), '<code>$1</code>');
    return s;
  }
  function paNbMd(text, cits){
    var raw = esc(text == null ? '' : text), lines = raw.split(/\r?\n/), out = [];
    lines.forEach(function(line){
      if(/^\s*$/.test(line)){ out.push('<div style="height:6px"></div>'); return; }
      var m;
      if((m = line.match(/^(#{1,4})\s+(.+)$/))){ out.push('<div class="md-h">' + paNbInline(m[2], cits) + '</div>'); return; }
      if((m = line.match(/^\s*[-*]\s+(.+)$/))){ out.push('<div class="md-li">• ' + paNbInline(m[1], cits) + '</div>'); return; }
      if((m = line.match(/^\s*\d+\.\s+(.+)$/))){ out.push('<div class="md-li">' + paNbInline(m[1], cits) + '</div>'); return; }
      out.push('<p>' + paNbInline(line, cits) + '</p>');
    });
    return out.join('');
  }
  function paNbRenderChat(){
    var box = $('paNbChat'); if(!box) return;
    var list = paNbChatOf();
    if(!list.length){
      box.innerHTML = '<div class="pa-nb-empty" style="padding:4px 2px">'
        + (NB.sources.length ? '问本笔记本里的资料；答案会带 [n] 出处。' : '先加来源，再问。')
        + '</div><div class="pa-nb-sugg">'
        + '<button type="button" onclick="paNbPickQ(this)">这些资料的核心结论是什么？</button>'
        + '<button type="button" onclick="paNbPickQ(this)">列出关键数字、日期与承诺。</button>'
        + '<button type="button" onclick="paNbPickQ(this)">有哪些风险、待办和未决问题？</button></div>';
      return;
    }
    box.innerHTML = list.map(function(m, i){
      if(m.role === 'u') return '<div class="pa-nb-turn u">' + esc(m.text) + '</div>';
      if(m.pending) return '<div class="pa-nb-turn a" style="color:var(--sub)">' + esc(m.text) + '</div>';
      if(m.role === 'e') return '<div class="pa-nb-turn e">' + esc(m.text) + '</div>';
      return '<div class="pa-nb-turn a">' + paNbMd(m.text, m.citations) + paNbCiteChips(m.citations)
        + '<div class="pa-nb-actions"><button class="pa-btn" type="button" onclick="paNbSaveAnswer(' + i + ')">存为笔记</button>'
        + '<button class="pa-btn" type="button" onclick="paNbCopy(' + i + ')">复制</button></div></div>';
    }).join('');
    box.scrollTop = box.scrollHeight;
    paNbSaveChat();
  }
  window.paNbPickQ = function(btn){ var q = $('paNbQ'); if(q){ q.value = btn.textContent; q.focus(); } };
  window.paNbCopy = function(i){
    var m = (NB.chat[NB.cur] || [])[i]; if(!m) return;
    try{ navigator.clipboard.writeText(m.text || ''); msg('已复制'); }catch(e){ msg('复制失败'); }
  };
  window.paNbSaveAnswer = async function(i){
    var m = (NB.chat[NB.cur] || [])[i]; if(!m) return;
    var cits = (m.citations || []).map(function(c, j){ return '[' + (c.n || (j + 1)) + '] ' + (c.title || c.id); }).join('\n');
    var body = (m.text || '') + (cits ? '\n\n出处：\n' + cits : '');
    var title = String(m.text || '').replace(/[#*>\u005b\u005d]/g, '').split('\n')[0].slice(0, 40) || '问答笔记';
    try{
      if(NB.cur) await req('/v9/pa/notebooks/' + encodeURIComponent(NB.cur) + '/notes', {method:'POST', body:{title:title, body:body, kind:'summary'}});
      else await req('/v9/pa/notes', {method:'POST', body:{title:title, body:body, tags:['问答']}});
      await paNbAfterAdd('已存为笔记');
    }catch(e){ msg('存不了：' + ((e && e.message) || e)); }
  };
  window.paNbAsk = async function(){
    if(NB.busy) return;
    var q = String((($('paNbQ') || {}).value) || '').trim();
    if(!q){ if($('paNbQ')) $('paNbQ').focus(); return; }
    var selIds = paNbSelectedIds();
    if(!selIds.length){ msg('先勾选至少一个来源'); return; }
    var list = paNbChatOf(), ph = {role:'a', text:'检索本笔记本…', pending:true};
    list.push({role:'u', text:q}); list.push(ph);
    if($('paNbQ')) $('paNbQ').value = '';
    paNbRenderChat(); NB.busy = true; if($('paNbAskBtn')) $('paNbAskBtn').disabled = true;
    try{
      var path = NB.cur ? ('/v9/pa/notebooks/' + encodeURIComponent(NB.cur) + '/ask') : '/v9/pa/notes/ask';
      var d = await req(path, {method:'POST', body:{q:q, limit:6, note_ids:selIds}});
      list.splice(list.indexOf(ph), 1, {role:'a', text:d.answer || '（无回答）', citations:d.citations || []});
      msg('已答 · 引用 ' + ((d.citations || []).length) + ' 条');
    }catch(e){
      list.splice(list.indexOf(ph), 1, {role:'e', text:'问不到：' + ((e && e.message) || e)});
      msg('问不到：' + ((e && e.message) || e));
    }finally{
      NB.busy = false; if($('paNbAskBtn')) $('paNbAskBtn').disabled = false; paNbRenderChat();
    }
  };
  var KIND_LABEL = {summary:'摘要', report:'报告', flashcards:'闪卡', quiz:'测验',
    mindmap:'思维导图', slides:'演示文稿', datatable:'数据表格', faq:'常见问题', study:'学习指南'};
  function paNbRenderStudio(){
    var tabs = document.querySelectorAll('#paNbTabs .pa-nb-tile');
    for(var i=0;i<tabs.length;i++){
      if(tabs[i].disabled) continue;
      tabs[i].classList.toggle('on', tabs[i].getAttribute('data-kind') === NB.studioKind);
    }
    var b = $('paNbGenBtn');
    if(b){ b.textContent = '生成' + (KIND_LABEL[NB.studioKind] || ''); b.disabled = (!NB.cur || !paNbSelectedIds().length); }
    var box = $('paNbOut'); if(!box) return;
    var s = (NB.studio[NB.cur] || {})[NB.studioKind];
    if(!s){
      box.innerHTML = '<div class="pa-nb-empty">选一个类型，点「生成」。产出可存回本笔记本。</div>';
      if($('paNbSaveOut')) $('paNbSaveOut').hidden = true; return;
    }
    box.innerHTML = paNbMd(s.markdown || '', s.citations || [])
      + (s.model_ok === false ? '<div class="pa-hint" style="color:var(--amber)">模型暂不可用：以上为摘录，不是模型生成。</div>' : '');
    if($('paNbSaveOut')) $('paNbSaveOut').hidden = false;
  }
  var FORMAT_OPTS = {
    summary: [['brief','简洁摘要'],['detailed','详细摘要']],
    report: [['standard','标准报告'],['executive','一页高管摘要']],
    flashcards: [['12','12 张'],['24','24 张']],
    quiz: [['8','8 题'],['12','12 题']],
    slides: [['detailed','详细演示文稿'],['presenter','演示用幻灯片']],
    mindmap: [['tree','层级树']],
    datatable: [['table','事实表']],
    faq: [['8','8 组问答']],
    study: [['standard','标准学习指南']]
  };
  window.paNbStudioTab = function(kind){
    if(!KIND_LABEL[kind]) return;
    NB.studioKind = kind;
    paNbStudioConfig(kind);
  };
  function paNbStudioConfig(kind){
    var formats = FORMAT_OPTS[kind] || [['standard','标准']];
    var cards = formats.map(function(x, i){
      return '<button class="pa-nb-fmt' + (i === 0 ? ' on' : '') + '" type="button" data-v="' + esc(x[0]) + '"'
        + ' onclick="paNbCfgFmt(this)"><b>' + esc(x[1]) + '</b></button>';
    }).join('');
    var opts = NB.studioOpts[kind] || {};
    paNbModal('自定义' + (KIND_LABEL[kind] || '产出'),
      '<div class="pa-nb-cfg"><div class="pa-nb-cfg-l">格式</div><div class="pa-nb-fmts">' + cards + '</div>'
      + '<div class="pa-nb-cfg-grid"><div><div class="pa-nb-cfg-l">语言</div>'
      + '<select id="paNbCfgLang"><option>中文（简体）</option><option>English</option></select></div>'
      + '<div><div class="pa-nb-cfg-l">来源</div><div class="pa-nb-chip">' + paNbSelectedIds().length + ' 个已勾选</div></div></div>'
      + '<div class="pa-nb-cfg-l">重点／自定义要求</div>'
      + '<textarea id="paNbCfgFocus" placeholder="例如：面向新手、突出风险与数字…">' + esc(opts.focus || '') + '</textarea>'
      + '<div class="pa-hint">只使用已勾选来源；模型不可用会照实回落为摘录。</div></div>',
      '<button class="pa-btn" type="button" onclick="paNbModalClose()">取消</button>'
      + '<button class="pa-btn pa-btn-main" type="button" onclick="paNbStudioRun(\'' + esc(kind) + '\')">立即生成</button>');
  }
  window.paNbCfgFmt = function(btn){
    var p = btn.parentNode; if(!p) return;
    for(var i=0;i<p.children.length;i++) p.children[i].classList.toggle('on', p.children[i] === btn);
  };
  window.paNbStudioRun = function(kind){
    var f = document.querySelector('.pa-nb-fmts .pa-nb-fmt.on');
    var lang = $('paNbCfgLang'), focus = $('paNbCfgFocus');
    NB.studioKind = kind;
    NB.studioOpts[kind] = {format: f ? f.getAttribute('data-v') : '', language: lang ? lang.value : '中文（简体）', focus: focus ? focus.value.trim() : ''};
    paNbModalClose();
    paNbStudioGen();
  };
  window.paNbStudioGen = async function(){
    if(!NB.cur){ msg('Studio 需先选一个笔记本'); return; }
    var selIds = paNbSelectedIds();
    if(!selIds.length){ msg('先勾选来源，再生成'); return; }
    var b = $('paNbGenBtn'); if(b) b.disabled = true; msg('生成中…（本地模型）');
    try{
      var d = await req('/v9/pa/notebooks/' + encodeURIComponent(NB.cur) + '/studio', {method:'POST', body:{
        kind:NB.studioKind, note_ids:selIds, options:NB.studioOpts[NB.studioKind] || {}}});
      if(!NB.studio[NB.cur]) NB.studio[NB.cur] = {};
      NB.studio[NB.cur][NB.studioKind] = d; paNbRenderStudio();
      msg(d.model_ok ? ('已生成' + (KIND_LABEL[NB.studioKind] || '')) : '模型不可用，已照实回落为摘录');
    }catch(e){ msg('生成失败：' + ((e && e.message) || e)); }
    finally{ if(b) b.disabled = false; }
  };
  window.paNbSaveStudio = async function(){
    if(!NB.cur) return;
    var s = (NB.studio[NB.cur] || {})[NB.studioKind];
    if(!s || !s.markdown){ msg('还没有可存的产出'); return; }
    try{
      await req('/v9/pa/notebooks/' + encodeURIComponent(NB.cur) + '/notes', {method:'POST', body:{
        title: s.title || ('Studio ' + (KIND_LABEL[NB.studioKind] || '')), body: s.markdown, kind: NB.studioKind}});
      await paNbAfterAdd('Studio 产出已存为笔记');
    }catch(e){ msg('存不了：' + ((e && e.message) || e)); }
  };
  document.addEventListener('keydown', function(e){
    if(!e.target || e.target.id !== 'paNbQ') return;
    if(e.key === 'Enter' && !e.shiftKey){ e.preventDefault(); window.paNbAsk(); }
  });
})();
