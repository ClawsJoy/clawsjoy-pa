/* ---- 输入 ---- */
const ta=$('input');
ta.addEventListener('keydown',e=>{ if(e.key==='Enter'&&!e.shiftKey){ e.preventDefault(); paSend(); } });
function autoGrow(){ ta.style.height='38px'; ta.style.height=Math.min(120,Math.max(38,ta.scrollHeight))+'px'; }
ta.addEventListener('input',autoGrow);
