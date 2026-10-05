/* ---- 建档表单（字段驱动：后端字段表 /v9/pa/profile/schema；前端不硬编码字段）---- */
let FIELD_SPEC = {}, FIELD_ORDER = [];
async function loadFieldsForm(){
  const box = $('collectForm'); if(!box) return;
  try{
    const r = await fetch(API+'/v9/pa/profile/schema?user_id='+encodeURIComponent(curUser()));
    const d = await r.json();
    if(!d || !d.ok || !d.fields) throw 0;
    FIELD_SPEC = d.fields;
    FIELD_ORDER = d.order || Object.keys(d.fields);
    renderFieldsForm(d.values||{});
    const sw = d.switches||{};
    setCollectMsg('当前：汇报'+esc(sw.detail||'中')+(sw.auto_write?' · 可自动写':' · 写需确认')+(sw.auto_exec?' · 可自动执行':' · 执行需确认'));
  }catch(e){ box.innerHTML='<div style="color:var(--sub)">字段表未加载（/v9/pa/profile/schema 无响应）。</div>'; }
}
function renderFieldsForm(values){
  const box=$('collectForm'); box.innerHTML='';
  (FIELD_ORDER.length?FIELD_ORDER:Object.keys(FIELD_SPEC)).forEach(k=>{
    const f=FIELD_SPEC[k]; if(!f) return;
    const cur=values[k], wrap=document.createElement('label');
    wrap.setAttribute('data-key',k);
    if(f.type==='multi'){
      const g=document.createElement('span');
      g.style.cssText='display:inline-flex;flex-wrap:wrap;gap:6px;max-width:150px;justify-content:flex-end';
      (f.options||[]).forEach(o=>{
        const lb=document.createElement('span'); lb.style.whiteSpace='nowrap';
        const on = Array.isArray(cur) && cur.indexOf(o)>=0;
        lb.innerHTML='<input type="checkbox" data-field="'+esc(k)+'" value="'+esc(o)+'"'+(on?' checked':'')+'> '+esc(o);
        g.appendChild(lb);
      });
      wrap.appendChild(document.createTextNode(f.label));
      wrap.appendChild(g);
    } else {
      wrap.appendChild(document.createTextNode(f.label));
      const sel=document.createElement('select'); sel.id='cf_'+k; sel.setAttribute('data-field',k);
      sel.innerHTML='<option value="">未设置</option>'+(f.options||[]).map(o=>
        '<option value="'+esc(o)+'"'+(cur===o?' selected':'')+'>'+esc(o)+'</option>').join('');
      wrap.appendChild(sel);
    }
    box.appendChild(wrap);
  });
}
function collectValues(){
  const v={};
  Object.keys(FIELD_SPEC).forEach(k=>{
    const f=FIELD_SPEC[k];
    if(f.type==='multi'){
      const sel=Array.prototype.slice.call(document.querySelectorAll('input[data-field="'+k+'"]:checked')).map(x=>x.value);
      if(sel.length) v[k]=sel;
    } else {
      const el=$('cf_'+k), val=el?el.value:'';
      if(val) v[k]=val;
    }
  });
  return v;
}
async function saveFields(){
  const v=collectValues();
  if(!Object.keys(v).length){ setCollectMsg('没有填写任何字段'); return; }
  setCollectMsg('保存中…');
  try{
    const r=await fetch(API+'/v9/pa/profile',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({user_id:curUser(), source:'form', values:v})});
    const d=await r.json();
    if(!d || !d.ok){ setCollectMsg('写入失败：'+((d&&d.error)||'')); return; }
    const w=(d.written||[]).length, un=(d.unchanged||[]).length, rj=(d.rejected||[]);
    const sw=d.switches||{};
    setCollectMsg('已写入 '+w+' 项'+(un?('，'+un+' 项未变'):'')+(rj.length?('；被拒：'+rj.map(x=>esc(x.reason)).join(' / ')):'')
      +' · 汇报'+esc(sw.detail||'中')+(sw.auto_write?' · 可自动写':' · 写需确认'));
    if(w) console.log('[PA建档] 落库', d.fields, sw);
    loadSide();
  }catch(e){ setCollectMsg(PA_GAP.down('后端')); }
}
function setCollectMsg(t){ const el=$('collectMsg'); if(el) el.textContent=t||''; }
['cfgChan','cfgModel','cfgPerm','cfgAppr'].forEach(id=>$(id).addEventListener('change',saveCfg)); $('cfgVault').addEventListener('change',saveCfg);
