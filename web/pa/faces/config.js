/* ---- 运行配置 ---- */
function loadCfg(){ const c=JSON.parse(localStorage.getItem('pa_cfg')||'{}'); const set=(id,v)=>{const el=$(id); if(el&&v) el.value=v;}; set('cfgChan',c.chan); set('cfgModel',c.model); set('cfgAppr',c.appr);   /* PA-B1：⛔ 不再从 pa_cfg 回填权限档（真源＝后端，由 fetchPaGrant 落到同一 select） */ const cv=$('cfgVault'); if(cv&&typeof c.vault==='boolean') cv.checked=c.vault; fetchPaGrant(); fetchPaBuild();   /* PM-011：授予来源面 ＋ 构建指纹（PM 2026-09-30 批） */ }
function saveCfg(){
  /* PA-B1 · 授权面板（2026-10-03 · CW b2a5182）：**改档单源 ＝ 后端**。
     病（本刻一手读原文）：本函数此前 `console.warn` 静默 —— 后端拒收（409 坏状态 / 非法档）时
     界面仍显示新值 ⇒ **假绿**（改了不生效，用户看不到）；且成功也不回读 ⇒ 顶栏与配置可长期不一致。
     承 core/pa/permission.py 抬头（2026-09-11 设计）：「只能经 /v9/pa/permission 写入」。
     ⛔ 现在：`pa_cfg` 不再存 perm（消第二真源）· 失败**可见**并**回读后端真值**（⛔ 界面不留假值）。 */
  const permEl=$('cfgPerm'); const perm=permEl?String(permEl.value||''):'';
  const cfg={chan:$('cfgChan').value,model:$('cfgModel').value,appr:$('cfgAppr').value,vault:$('cfgVault').checked};
  localStorage.setItem('pa_cfg',JSON.stringify(cfg));
  if(!perm) return;
  fetch(API+'/v9/pa/permission',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:curUser(),level:perm})})
    .then(function(r){ return r.json().then(function(d){ return {status:r.status,d:d}; }).catch(function(){ return {status:r.status,d:null}; }); })
    .then(function(x){
      var d=x.d;
      if(x.status!==200 || !d || d.ok===false){
        var msg=(d&&(d.message||d.error))||('HTTP '+x.status);
        addMsg('sys','⚠ 权限档后端拒收（HTTP '+x.status+'）：'+msg+' ⇒ 按后端真值回读（⛔ 界面不留假值）');
      }
      fetchPaGrant();   /* 回读：顶栏徽标 ／ 授权面板 ／ 本下拉 同源同步 */
    })
    .catch(function(e){ addMsg('sys','⚠ 权限档未取得回执：'+((e&&e.message)||e)+' ⇒ 后端是否已改**未知**（⛔ 不等于「没改」）'); fetchPaGrant(); });
}
