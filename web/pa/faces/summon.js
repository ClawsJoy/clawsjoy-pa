/* PA 窗 v1 / 1a · Summon（CW b2a5182 · 2026-10-27 · 承 PRD v1 §3.1 ／ §4.4 ／ §5）
   热键 Ctrl+Shift+Space ／ Enter 发 ／ Esc 收但**保留草稿 5 分钟** ／ 拖件 ／ 贴图（1a：只记个数，⛔ 上传）。
   界：静态壳；⛔ 动后端 ／ ⛔ 新依赖。 */
(function(){
  'use strict';

  var DRAFT_KEY = 'paWinDraft';
  var TTL = 5 * 60 * 1000;      /* 草稿留 5 分钟（PRD §3.1） */
  var draftTimer = null;
  var attachments = [];

  function $id(x){ return document.getElementById(x); }
  function esc(s){
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }

  /* ── 草稿：{t, at}；超 5 分钟即丢 ── */
  function loadDraft(){
    try{
      var raw = localStorage.getItem(DRAFT_KEY);
      if(!raw) return '';
      var d = JSON.parse(raw);
      if(!d || !d.at || (Date.now() - d.at) > TTL){ localStorage.removeItem(DRAFT_KEY); return ''; }
      return String(d.t || '');
    }catch(e){ return ''; }
  }
  function saveDraft(t){
    try{
      if(!t){ localStorage.removeItem(DRAFT_KEY); return; }
      localStorage.setItem(DRAFT_KEY, JSON.stringify({t: t, at: Date.now()}));
    }catch(e){ /* 存不了就算了：⛔ 弹窗 */ }
  }
  function clearDraft(){ try{ localStorage.removeItem(DRAFT_KEY); }catch(e){} }

  function paintAttach(){
    var el = $id('paSummonAtt');
    if(!el) return;
    el.textContent = attachments.length ? ('附件 ' + attachments.length) : '附件 0';
    el.classList.toggle('has', attachments.length > 0);
  }

  window.paWinSummonOpen = function(){
    var s = $id('paSummon');
    if(!s) return;
    var t0 = (window.performance && performance.now) ? performance.now() : Date.now();
    var inp = $id('paSummonIn');
    if(inp && !inp.value) inp.value = loadDraft();
    s.hidden = false;
    s.classList.add('on');
    if(inp){ inp.focus(); inp.setSelectionRange(inp.value.length, inp.value.length); }
    var dt = ((window.performance && performance.now) ? performance.now() : Date.now()) - t0;
    window.paWinPerf = window.paWinPerf || {};
    window.paWinPerf.summonMs = Math.round(dt * 10) / 10;
    if(draftTimer) clearTimeout(draftTimer);
    draftTimer = setTimeout(function(){ saveDraft(inp ? inp.value : ''); }, 200);
    return dt;
  };

  window.paWinSummonClose = function(keep){
    var s = $id('paSummon');
    var inp = $id('paSummonIn');
    if(!s) return;
    if(keep !== false) saveDraft(inp ? inp.value : '');
    s.classList.remove('on');
    s.hidden = true;
    if(draftTimer){ clearTimeout(draftTimer); draftTimer = null; }
  };

  window.paWinSummonToggle = function(){
    var s = $id('paSummon');
    if(!s) return;
    if(s.hidden) window.paWinSummonOpen(); else window.paWinSummonClose(true);
  };

  /* Enter 发 ⇒ 出计划卡（⛔ 直接执行 · PRD §8.4）*/
  window.paWinSummonSend = function(){
    var inp = $id('paSummonIn');
    var txt = inp ? String(inp.value || '').trim() : '';
    if(!txt){ if(inp) inp.focus(); return; }
    clearDraft();
    if(inp) inp.value = '';
    attachments = [];
    paintAttach();
    window.paWinSummonClose(false);
    window.paWinPlan(txt);
  };

  function bindOnce(){
    var inp = $id('paSummonIn');
    if(inp && !inp.__paWinBound){
      inp.__paWinBound = true;
      inp.addEventListener('keydown', function(e){
        if(e.key === 'Enter' && !e.shiftKey){ e.preventDefault(); window.paWinSummonSend(); }
        else if(e.key === 'Escape'){ e.preventDefault(); window.paWinSummonClose(true); }
      });
      inp.addEventListener('input', function(){ saveDraft(inp.value); });
      inp.addEventListener('paste', function(e){
        var items = (e.clipboardData && e.clipboardData.items) || [];
        for(var i = 0; i < items.length; i++){
          if(String(items[i].type || '').indexOf('image') === 0){
            attachments.push({name: '贴图', kind: 'image'});
            paintAttach();
          }
        }
      });
    }
    var box = $id('paSummon');
    if(box && !box.__paWinDrop){
      box.__paWinDrop = true;
      box.addEventListener('dragover', function(e){ e.preventDefault(); box.classList.add('drag'); });
      box.addEventListener('dragleave', function(){ box.classList.remove('drag'); });
      box.addEventListener('drop', function(e){
        e.preventDefault(); box.classList.remove('drag');
        var fs = (e.dataTransfer && e.dataTransfer.files) || [];
        for(var i = 0; i < fs.length; i++) attachments.push({name: fs[i].name, kind: 'file'});
        paintAttach();
        window.paWinSay(fs.length ? ('收了 ' + fs.length + ' 件（这里先只记账，不传出去）') : '没接到东西');
      });
    }
    paintAttach();
  }

  /* 全局热键（窗内） */
  window.paWinSummonBindKeys = function(){
    if(window.__paWinKeys) return;
    window.__paWinKeys = true;
    document.addEventListener('keydown', function(e){
      if(e.ctrlKey && e.shiftKey && (e.code === 'Space' || e.key === ' ')){
        e.preventDefault(); window.paWinSummonToggle(); return;
      }
      if(e.ctrlKey && !e.shiftKey && e.key === '.'){ e.preventDefault(); window.paWinStop(); return; }
      if(e.ctrlKey && !e.shiftKey && (e.key === 'k' || e.key === 'K')){
        e.preventDefault(); window.paWinPaletteToggle(); return;
      }
      if(e.altKey && /^[1-5]$/.test(e.key)){
        e.preventDefault(); window.paWinGo(['today','agents','ledger','vault','doors'][Number(e.key) - 1]); return;
      }
      if(e.key === 'Escape'){
        var sm = $id('paSummon');
        if(sm && !sm.hidden){ window.paWinSummonClose(true); return; }
        if(document.body.classList.contains('pa-focus')){ window.paWinGo('today'); }
      }
    });
    document.addEventListener('DOMContentLoaded', bindOnce);
    if(document.readyState !== 'loading') bindOnce();
  };

  window.paWinSummonDraft = function(){ return loadDraft(); };
  window.paWinSummonAttach = function(){ return attachments.slice(); };
  window.paWinSummonReset = function(){ clearDraft(); attachments = []; paintAttach(); };
})();