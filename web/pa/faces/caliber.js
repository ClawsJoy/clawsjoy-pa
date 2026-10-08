/* ---- PM-011 · N1 接线（2026-09-30 · PM 批「没接线的闸优先接线」）：**口径面板** ----------------
   病：`/v9/pa/caliber`（L0）· `/v9/pa/caliber/change`（L1）· `/v9/pa/caliber/check`（L2 门）
   三端点后端**在场且有单测**，但 `web/pa.html` **0 命中** ⇒ 前端够不着 ⇒ **闸在场没接线**
   （设计稿 v9_pa_frontend_refactor_design.md §4.3「新增 口径面板 … 待接」／§4.4 第 13–15 条）。
   照设计稿 §4.2 三条纪律（不吞／不造／不复述）：
     ① 不吞：读不到 ⇒ 明说**读数不可得**（⛔ 不报 0、⛔ 不填占位符）；
     ② 不造：变更单四项 id/status/owner/why **缺一即拒**，⛔ 前端不代填默认值；
     ③ 改前值：提交**前**把 store 现值与本次提交并排渲染（P7「含改前值」的前端侧）。
   ⛔ 本步只接线：⛔ 不改后端语义、⛔ 不加新卡型（仍走 #caliberPanel 容器）、
      ⛔ 不碰生效判定（谁放行仍由后端 `caliber.check()` 判）。 */
const PA_CALIBER_API = { list:'/v9/pa/caliber', change:'/v9/pa/caliber/change', check:'/v9/pa/caliber/check' };
const PA_CALIBER_STATES = ['confirmed','unverified','pending'];
function paCaliberEl(id){ try{ return document.getElementById(id); }catch(e){ return null; } }
function paCaliberMissingFields(form){
  const f=form||{}; const miss=[];
  ['id','status','owner','why'].forEach(function(k){ if(!String(f[k]==null?'':f[k]).trim()) miss.push(k); });
  return miss;
}
function paCaliberCardHtml(c){
  const d=c||{}; const st=String(d.status==null?'':d.status);
  const known=(PA_CALIBER_STATES.indexOf(st)>=0);
  /* ⛔ 状态缺失/不认识 ⇒ 明说「未知」，⛔ 不默认成 confirmed（默认值假装成读数同族） */
  const stat=known?st:'未知（后端未给 status）';
  return '<div class="cbcard cb-'+(known?st:'unknown')+'">'
    +'<span class="cbid">'+esc(d.id==null?'（无 id）':d.id)+'</span>'
    +' <span class="cbstat">'+esc(stat)+'</span> · <span class="cbowner">'+esc(d.owner?('签 '+d.owner):'未署名')+'</span>'
    +' · <span class="cbupd">'+esc(d.updated?('改 '+d.updated):'改期未给')+'</span>'
    +'<div class="cbtopic">'+esc(d.topic==null?'':d.topic)+'</div></div>';
}
function paCaliberCountsHtml(doc){
  const d=doc||{};
  if(!d.counts) return '计数不可得（本机未给计数 ⇒ 不按 0 显示）';
  const parts=[]; PA_CALIBER_STATES.forEach(function(st){ parts.push(st+' '+(d.counts[st]||0)); });
  return parts.join(' · ')+' · 源 '+(d.source||'未给');
}
function paCaliberPrevHtml(card, patch){
  const c=card||null, p=patch||{};
  const cell=function(v,naTxt){ return (v==null||v==='')?('<span class="cbna">'+naTxt+'</span>'):esc(String(v)); };
  const row=function(k,curV,nextV,naTxt){
    return '<tr><td>'+esc(k)+'</td><td class="cbcur">'+cell(curV,naTxt)+'</td><td class="cbnext">'+cell(nextV,'本次未填')+'</td></tr>';
  };
  if(!c) return '<div class="cb-degraded">⚠ 改前值不可得：该编号不在现有清单里（新卡 ／ 编号打错 —— 本面不凭空造「改前值」）</div>';
  return '<table class="cbtable"><tr><th>键</th><th>改前（store 现值）</th><th>改后（本次提交）</th></tr>'
    + row('status', c.status, p.status, '现值未给')
    + row('owner',  c.owner,  p.owner,  '现值未给')
    + row('note',   c.note,   p.why,    '现值未给')
    + '</table>';
}
function paCaliberCheckHtml(res){
  if(res==null) return '<span class="cbna">⚠ 未取得回执</span>（不等于「未命中」—— 这是读数不可得，两态必须分得开）';
  if(res.__error) return '<span class="cbna">⚠ 未取得回执：'+esc(res.__error)+'</span>（不等于「未命中」）';
  const hits=Array.isArray(res.hits)?res.hits:[];
  if(!hits.length) return '✅ 未命中口径卡（后端 hits=0）';
  return '⚠ 命中 '+hits.length+' 条：'+hits.map(function(h){
    const a=Array.isArray(h)?h:[]; return esc((a[1]||'?')+'（'+(a[2]||'?')+'／'+(a[3]||'?')+'）');
  }).join(' · ');
}
function paCaliberPanelHtml(doc, opts){
  const o=opts||{}, d=doc||{};
  const loaded=(d.__loaded===true);
  let h='<details class="cbpanel"'+(o.open?' open':'')+'><summary>🧭 口径面板 · '
    +esc(loaded?paCaliberCountsHtml(d):'尚未加载（展开时按只读接口拉取，不刷新页面）')+'</summary>';
  if(!loaded) return h+'</details>';
  if(d.__error) return h+'<div class="cb-degraded">⚠ 口径读数不可得：'+esc(String(d.__error))+'（这不是「没有口径卡」）</div></details>';
  const cards=Array.isArray(d.cards)?d.cards:[];
  h+='<div class="cbmeta">状态读法：<b>unverified／pending</b> 的数字出现在正文 ⇒ check 命中；confirmed 不拦。'
    +' <button class="cbrefresh" onclick="paCaliberLoad(true)">刷新</button></div>';
  h+='<div class="cbscroll">'+(cards.length?cards.map(paCaliberCardHtml).join(''):'<div class="cbempty">本库暂无可口径卡（空 ≠ 读数不可得）</div>')+'</div>';
  h+='<div class="cbform"><div class="cbrow"><input id="cbId" placeholder="id（如 #4）">'
    +'<select id="cbStatus"><option value="">（未选）</option><option value="confirmed">confirmed</option>'
    +'<option value="unverified">unverified</option><option value="pending">pending</option></select>'
    +'<input id="cbOwner" placeholder="owner（谁签）"></div>'
    +'<input id="cbWhy" placeholder="why（改动理由）">'
    +'<button class="cbsubmit" title="必填四项：id ／ status ／ owner ／ why" onclick="paCaliberSubmit()">提交变更单（四项缺一即拒）</button>'
    +'<div id="cbPrev" class="cbprev">（提交前在此渲染「改前值 → 改后值」）</div></div>';
  h+='<div class="cbform"><textarea id="cbCheckBody" placeholder="产物／草稿正文（留空则用输入框草稿）"></textarea>'
    +'<button class="cbcheck" onclick="paCaliberCheck()">校验：正文是否命中未核实口径</button>'
    +'<div id="cbCheckOut" class="cbout">（校验三态：命中 ／ 未命中 ／ 未取得回执）</div></div>';
  return h+'</details>';
}
let paCaliberCache=null;
function paCaliberApiUrl(){ return API+PA_CALIBER_API.list+'?user_id='+encodeURIComponent(curUser()); }
async function paCaliberLoad(force){
  const host=paCaliberEl('caliberPanel'); if(!host) return null;
  if(paCaliberCache && !force){ renderCaliberPanel(); return paCaliberCache; }
  let doc=null;
  try{
    const r=await fetch(paCaliberApiUrl());
    let d=null; try{ d=await r.json(); }catch(e){ d=null; }
    if(r.status!==200 || !d || d.ok===false){
      doc={__loaded:true, __error:((d&&(d.message||d.error))||('HTTP '+r.status))};
    }else{
      doc={__loaded:true, cards:d.cards, counts:d.counts, source:d.source};
    }
  }catch(e){ doc={__loaded:true, __error:''+((e&&e.message)||e)}; }
  paCaliberCache=doc; renderCaliberPanel(); return doc;
}
function renderCaliberPanel(){
  const host=paCaliberEl('caliberPanel'); if(!host) return;
  const open=(host.getAttribute('data-open')==='1');
  host.innerHTML=paCaliberPanelHtml(paCaliberCache||{__loaded:false},{open:open});
  const det=host.querySelector?host.querySelector('details'):null;
  if(det&&det.addEventListener){ det.addEventListener('toggle', function(){ host.setAttribute('data-open', det.open?'1':'0'); if(det.open) paCaliberLoad(false); }); }
}
function paCaliberFindCard(id){
  const cards=(paCaliberCache&&Array.isArray(paCaliberCache.cards))?paCaliberCache.cards:[];
  for(let i=0;i<cards.length;i++){ if(String((cards[i]||{}).id)===String(id)) return cards[i]; }
  return null;
}
function paCaliberReadForm(){
  const v=function(id){ const el=paCaliberEl(id); return el?String(el.value==null?'':el.value).trim():''; };
  return {id:v('cbId'), status:v('cbStatus'), owner:v('cbOwner'), why:v('cbWhy')};
}
async function paCaliberSubmit(form){
  const f=form||paCaliberReadForm();
  const prev=paCaliberEl('cbPrev');
  const miss=paCaliberMissingFields(f);
  if(miss.length){
    if(prev) prev.innerHTML='<div class="cb-degraded">变更单还缺：'+esc(miss.join(' ／ '))+' ⇒ 不提交（四项必填，本面不代填默认值）</div>';
    return {ok:false, error:'missing_fields', missing:miss, sent:false};
  }
  if(prev) prev.innerHTML=paCaliberPrevHtml(paCaliberFindCard(f.id), f);   /* ③ 先渲染改前值，再提交 */
  try{
    const r=await fetch(API+PA_CALIBER_API.change,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(f)});
    let d=null; try{ d=await r.json(); }catch(e){ d=null; }
    if(r.status!==200 || !d || d.ok===false){
      const msg=(d&&(d.message||d.error))||('HTTP '+r.status);
      if(prev) prev.innerHTML+='<div class="cb-degraded">⚠ 本机拒收（HTTP '+r.status+'）：'+esc(String(msg))+'（原样可见，不吞）</div>';
      return {ok:false, error:msg, sent:true, status:r.status};
    }
    await paCaliberLoad(true);
    return {ok:true, sent:true, resp:d};
  }catch(e){
    const msg=''+((e&&e.message)||e);
    if(prev) prev.innerHTML+='<div class="cb-degraded">⚠ 未取得回执：'+esc(msg)+'（不等于「没改」）</div>';
    return {ok:false, error:msg, sent:true};
  }
}
async function paCaliberCheckText(text){
  const body=String(text==null?'':text);
  const box=paCaliberEl('cbCheckBody');
  const payloadBody=body.trim()?body:((box&&typeof box.value==='string')?box.value:'');
  const out=paCaliberEl('cbCheckOut');
  const say=function(html){ if(out) out.innerHTML=html; return html; };
  if(!String(payloadBody).trim()){
    const res={__error:'没有可校验的正文（本面不凭空造）'};
    say(paCaliberCheckHtml(res)); return res;
  }
  let res=null;
  try{
    const r=await fetch(API+PA_CALIBER_API.check,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({pages:[{data:{body:String(payloadBody)}}]})});
    let d=null; try{ d=await r.json(); }catch(e){ d=null; }
    res=(r.status===200 && d && d.ok!==false)?d:{__error:((d&&(d.message||d.error))||('HTTP '+r.status))};
  }catch(e){ res={__error:''+((e&&e.message)||e)}; }
  say(paCaliberCheckHtml(res));
  return res;
}
function paCaliberCheck(){
  const box=paCaliberEl('cbCheckBody'); const draft=paCaliberEl('input');
  const t=(box&&String(box.value||'').trim())?box.value:((draft&&draft.value)||'');
  return paCaliberCheckText(t);
}
/* ---- PM-011 · N1 接线 END ---- */