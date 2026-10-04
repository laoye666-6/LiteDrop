# -*- coding: utf-8 -*-
"""轻传 LiteDrop — 手机端页面(单文件内嵌,无外部依赖)。"""

PAGE_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0a0f1c">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>轻传 LiteDrop</title>
<style>
:root{
  --bg:#0a0f1c; --card:#121a2b; --card2:#0d1526; --line:rgba(255,255,255,.07);
  --text:#e8eef9; --muted:#8ca0c0; --ac1:#4f7cff; --ac2:#22d3ee;
  --grad:linear-gradient(135deg,#4f7cff,#22d3ee);
  --danger:#ef4444; --ok:#34d399;
  --shadow:0 6px 24px rgba(0,0,0,.30);
}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
html,body{height:100%}
body{
  background:var(--bg); color:var(--text);
  font-family:-apple-system,"PingFang SC","HarmonyOS Sans SC","Microsoft YaHei",sans-serif;
  padding-bottom:calc(76px + env(safe-area-inset-bottom));
  background-image:
    radial-gradient(640px 260px at 50% -70px,rgba(79,124,255,.20),transparent),
    radial-gradient(480px 260px at 100% 102%,rgba(34,211,238,.07),transparent);
}
button{font-family:inherit;border:0;cursor:pointer;color:inherit}
/* ---------- 头部 ---------- */
header{
  padding:calc(16px + env(safe-area-inset-top)) 18px 18px;
  background:var(--grad); color:#fff; border-radius:0 0 28px 28px;
  box-shadow:0 10px 32px rgba(79,124,255,.35);
}
.brand{display:flex;align-items:center;gap:13px}
.logo{
  width:46px;height:46px;flex:none;border-radius:15px;
  background:rgba(255,255,255,.22);backdrop-filter:blur(6px);
  display:flex;align-items:center;justify-content:center;font-size:24px;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.25);
}
header h1{font-size:21px;font-weight:800;letter-spacing:.5px;line-height:1.2}
header .sub{font-size:12px;opacity:.92;margin-top:3px;display:flex;align-items:center;gap:6px}
.dot{width:8px;height:8px;border-radius:50%;background:rgba(255,255,255,.55);flex:none}
.dot.on{background:#b9ffdf;animation:pulse 2s infinite}
@keyframes pulse{
  0%{box-shadow:0 0 0 0 rgba(185,255,223,.55)}
  70%{box-shadow:0 0 0 7px rgba(185,255,223,0)}
  100%{box-shadow:0 0 0 0 rgba(185,255,223,0)}
}
/* ---------- 主体 ---------- */
main{padding:18px 14px;max-width:560px;margin:0 auto}
.page{display:none;animation:fadein .28s ease}
.page.active{display:block}
@keyframes fadein{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.card{
  background:var(--card);border:1px solid var(--line);border-radius:18px;
  padding:15px;margin-bottom:16px;box-shadow:var(--shadow);
}
.sect{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--muted);
  margin:2px 2px 11px;font-weight:600;letter-spacing:1px}
.sect::before{content:"";width:4px;height:14px;border-radius:2px;
  background:var(--grad);display:block;flex:none}
textarea{
  width:100%;min-height:112px;resize:vertical;background:var(--card2);
  border:1px solid var(--line);border-radius:14px;color:var(--text);
  padding:12px;font-size:15px;line-height:1.55;outline:none;transition:border-color .2s;
}
textarea:focus{border-color:var(--ac1);box-shadow:0 0 0 3px rgba(79,124,255,.15)}
.btn-main{
  display:block;width:100%;padding:14px;border-radius:14px;margin-top:12px;
  background:var(--grad);color:#fff;font-size:16px;font-weight:700;letter-spacing:2px;
  box-shadow:0 8px 22px rgba(79,124,255,.38);
  transition:transform .12s,box-shadow .2s,opacity .2s;
}
.btn-main:active{transform:scale(.97) translateY(1px);box-shadow:0 4px 12px rgba(79,124,255,.28)}
.btn-main:disabled{opacity:.5;box-shadow:none}
/* ---------- 选择文件区 ---------- */
.drop{
  border:2px dashed #2c3d60;border-radius:18px;padding:30px 12px;text-align:center;
  color:var(--muted);font-size:14px;user-select:none;line-height:1.8;
  transition:border-color .2s,background .2s,transform .15s;
}
.drop:active,.drop.over{border-color:var(--ac1);background:rgba(79,124,255,.08);transform:scale(.99)}
.drop .em{font-size:34px;display:block;margin-bottom:8px;filter:drop-shadow(0 4px 10px rgba(79,124,255,.35))}
.drop .hint2{font-size:12px;opacity:.65}
/* ---------- 上传队列 ---------- */
.up{display:flex;flex-direction:column;gap:11px}
.uprow{
  background:var(--card2);border:1px solid var(--line);border-radius:14px;
  padding:12px 13px;transition:border-color .3s;
}
.uprow .row1{display:flex;justify-content:space-between;gap:8px;font-size:13px;margin-bottom:9px;align-items:center}
.uprow .name{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1;font-weight:600}
.uprow .pct{color:var(--muted);flex:none;font-variant-numeric:tabular-nums}
.bar{height:7px;border-radius:5px;background:#1c2740;overflow:hidden}
.bar i{display:block;height:100%;width:0;background:var(--grad);border-radius:5px;
  transition:width .3s ease;position:relative}
.bar i::after{content:"";position:absolute;inset:0;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.28),transparent);
  animation:shine 1.4s infinite}
@keyframes shine{from{transform:translateX(-100%)}to{transform:translateX(100%)}}
.uprow.done{border-color:rgba(52,211,153,.4)}
.uprow.done .pct{color:var(--ok)}
.uprow.done .bar i::after{display:none}
.uprow.fail{border-color:rgba(239,68,68,.45)}
.uprow.fail .pct{color:var(--danger)}
.uprow.fail .bar i{background:var(--danger)}
.uprow.fail .bar i::after{display:none}
.retry{margin-top:9px;background:rgba(239,68,68,.15);color:var(--danger);
  border-radius:9px;padding:6px 14px;font-size:12px;font-weight:600}
/* ---------- 接收 ---------- */
.tcard{
  background:var(--card);border:1px solid var(--line);border-radius:18px;
  padding:13px 15px;margin-bottom:13px;box-shadow:var(--shadow);
}
.tcard.fresh{animation:pop .4s cubic-bezier(.2,.8,.3,1)}
@keyframes pop{0%{opacity:0;transform:translateY(12px) scale(.97)}100%{opacity:1;transform:none}}
.tcard .meta{display:flex;align-items:center;gap:8px;margin-bottom:7px}
.chip{font-size:11px;color:var(--muted);background:var(--card2);
  border-radius:20px;padding:3px 11px;font-variant-numeric:tabular-nums}
.tcard .txt{font-size:15px;line-height:1.6;white-space:pre-wrap;word-break:break-word}
.copy{margin-left:auto;background:rgba(79,124,255,.16);color:#8fb0ff;
  border-radius:20px;padding:5px 15px;font-size:12px;font-weight:600;
  transition:background .2s,color .2s,transform .12s}
.copy:active{transform:scale(.94)}
.copy.ok{background:rgba(52,211,153,.18);color:var(--ok)}
.frow{
  display:flex;align-items:center;gap:13px;background:var(--card);
  border:1px solid var(--line);border-radius:18px;padding:13px 14px;
  margin-bottom:13px;box-shadow:var(--shadow);
}
.frow .ico{width:44px;height:44px;flex:none;border-radius:14px;display:flex;
  align-items:center;justify-content:center;font-size:22px;
  background:linear-gradient(135deg,rgba(79,124,255,.18),rgba(34,211,238,.12))}
.frow .info{flex:1;min-width:0}
.frow .fname{font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.frow .fsize{font-size:12px;color:var(--muted);margin-top:3px;font-variant-numeric:tabular-nums}
.dl{flex:none;background:var(--grad);color:#fff;border-radius:20px;
  padding:8px 18px;font-size:13px;font-weight:700;text-decoration:none;
  box-shadow:0 4px 14px rgba(79,124,255,.32);transition:transform .12s}
.dl:active{transform:scale(.93)}
.empty{text-align:center;color:var(--muted);padding:46px 0;font-size:14px;line-height:2}
.empty .em{font-size:44px;display:block;margin-bottom:10px;opacity:.85;
  filter:drop-shadow(0 6px 14px rgba(79,124,255,.25))}
/* ---------- 底部导航 ---------- */
nav{
  position:fixed;left:12px;right:12px;bottom:calc(10px + env(safe-area-inset-bottom));
  z-index:9;display:flex;justify-content:space-around;max-width:536px;margin:0 auto;
  background:rgba(13,21,38,.88);backdrop-filter:blur(14px);
  border:1px solid var(--line);border-radius:20px;
  padding:7px;box-shadow:0 10px 30px rgba(0,0,0,.45);
}
.navbtn{position:relative;background:none;font-size:12px;color:var(--muted);
  display:flex;flex-direction:column;align-items:center;gap:3px;padding:7px 26px;
  border-radius:14px;transition:color .2s,background .25s}
.navbtn .em{font-size:21px;transition:transform .2s}
.navbtn.active{color:#fff;background:linear-gradient(135deg,rgba(79,124,255,.28),rgba(34,211,238,.18))}
.navbtn.active .em{transform:translateY(-1px) scale(1.08)}
.badge{position:absolute;top:0;right:14px;min-width:17px;height:17px;
  border-radius:9px;background:var(--danger);color:#fff;font-size:10px;
  display:none;align-items:center;justify-content:center;padding:0 4px;font-weight:700;
  box-shadow:0 2px 8px rgba(239,68,68,.5)}
.badge.show{display:flex}
/* ---------- Toast ---------- */
#toast{
  position:fixed;left:50%;bottom:calc(92px + env(safe-area-inset-bottom));
  transform:translateX(-50%) translateY(16px);background:rgba(27,41,70,.95);
  backdrop-filter:blur(8px);color:var(--text);
  border:1px solid rgba(255,255,255,.1);border-radius:24px;padding:10px 22px;
  font-size:13px;opacity:0;pointer-events:none;
  transition:opacity .25s,transform .25s;z-index:99;max-width:82vw;
  box-shadow:0 10px 30px rgba(0,0,0,.5);text-align:center}
#toast.show{opacity:1;transform:translateX(-50%)}
</style>
</head>
<body>
<header>
  <div class="brand">
    <div class="logo">📡</div>
    <div>
      <h1>轻传 LiteDrop</h1>
      <div class="sub"><span class="dot" id="dot"></span><span id="pcname">连接中…</span></div>
    </div>
  </div>
</header>

<main>
  <!-- 发送 -->
  <section class="page active" id="page-send">
    <div class="sect">文 本</div>
    <div class="card">
      <textarea id="txt" placeholder="输入文字,发送后在电脑上查看(新内容会自动复制到电脑剪贴板)"></textarea>
      <button class="btn-main" id="sendTxt">发送文本</button>
    </div>
    <div class="sect">文 件</div>
    <div class="drop" id="drop">
      <span class="em">📁</span>点按选择文件,或把文件拖到这里<br>
      <span class="hint2">大文件自动分块 · 断块自动重试 · 无需联网</span>
    </div>
    <input type="file" id="fileInput" multiple hidden>
    <div class="up" id="upList" style="margin-top:13px"></div>
  </section>

  <!-- 接收 -->
  <section class="page" id="page-recv">
    <div class="sect">来自电脑的文本</div>
    <div id="textList"><div class="empty"><span class="em">📭</span>还没有内容<br>在电脑端发送文本后会出现在这里</div></div>
    <div class="sect" style="margin-top:22px">来自电脑的文件</div>
    <div id="fileList"><div class="empty"><span class="em">🗂️</span>电脑端添加的文件会出现在这里</div></div>
  </section>
</main>

<nav>
  <button class="navbtn active" id="tab-send"><span class="em">📤</span>发送</button>
  <button class="navbtn" id="tab-recv"><span class="em">📥</span>接收<span class="badge" id="badge">0</span></button>
</nav>
<div id="toast"></div>

<script>
const TOKEN = new URLSearchParams(location.search).get('k') || '';
const CHUNK = 8 * 1024 * 1024;
let cursor = 0, unread = 0, pcName = '';

const $ = id => document.getElementById(id);
const fmtSize = n => n >= 1<<30 ? (n/(1<<30)).toFixed(2)+' GB'
  : n >= 1<<20 ? (n/(1<<20)).toFixed(1)+' MB' : n >= 1024 ? (n/1024).toFixed(0)+' KB' : n+' B';
const sleep = ms => new Promise(r => setTimeout(r, ms));
function fileEmoji(n){
  const e = (n.split('.').pop() || '').toLowerCase();
  if (['png','jpg','jpeg','gif','webp','bmp','heic','svg'].includes(e)) return '🖼️';
  if (['mp4','mov','avi','mkv','webm','flv'].includes(e)) return '🎬';
  if (['mp3','wav','flac','m4a','aac','ogg'].includes(e)) return '🎵';
  if (['zip','rar','7z','tar','gz','iso'].includes(e)) return '📦';
  if (['pdf'].includes(e)) return '📕';
  if (['doc','docx','txt','md','rtf'].includes(e)) return '📄';
  if (['xls','xlsx','csv'].includes(e)) return '📊';
  if (['py','js','ts','html','css','json','java','c','cpp','go'].includes(e)) return '🧾';
  return '📁';
}
let toastTimer;
function toast(msg){
  const t = $('toast'); t.textContent = msg; t.classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(()=>t.classList.remove('show'), 2200);
}
async function api(path, opt={}){
  opt.headers = Object.assign({'X-Auth': TOKEN}, opt.headers||{});
  const sep = path.includes('?') ? '&' : '?';
  const r = await fetch(path + sep + 'k=' + encodeURIComponent(TOKEN), opt);
  if (r.status === 403) throw new Error('口令无效');
  const data = await r.json();
  if (!r.ok || data.ok === false) throw new Error(data.error || ('HTTP ' + r.status));
  return data;
}

/* ---------- 标签页 ---------- */
function switchTab(recv){
  $('page-send').classList.toggle('active', !recv);
  $('page-recv').classList.toggle('active', recv);
  $('tab-send').classList.toggle('active', !recv);
  $('tab-recv').classList.toggle('active', recv);
  if (recv){ unread = 0; $('badge').classList.remove('show'); }
}
$('tab-send').onclick = () => switchTab(false);
$('tab-recv').onclick = () => switchTab(true);

/* ---------- 文本发送 ---------- */
$('sendTxt').onclick = async () => {
  const el = $('txt'), text = el.value.trim();
  if (!text) return toast('先输入点内容吧');
  $('sendTxt').disabled = true;
  try{
    await api('/api/text', {method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({text})});
    el.value = ''; toast('已发送到电脑 ✓');
  }catch(e){ toast('发送失败:' + e.message); }
  $('sendTxt').disabled = false;
};
$('txt').addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') $('sendTxt').click();
});

/* ---------- 文件上传 ---------- */
const drop = $('drop');
drop.onclick = () => $('fileInput').click();
$('fileInput').onchange = e => { addJobs([...e.target.files]); e.target.value=''; };
['dragover','dragenter'].forEach(ev => drop.addEventListener(ev, e => {
  e.preventDefault(); drop.classList.add('over'); }));
['dragleave','drop'].forEach(ev => drop.addEventListener(ev, e => {
  e.preventDefault(); drop.classList.remove('over'); }));
drop.addEventListener('drop', e => addJobs([...e.dataTransfer.files]));

const queue = [];
let uploading = false;
function addJobs(files){
  if (!files.length) return;
  for (const f of files){
    const row = document.createElement('div');
    row.className = 'uprow';
    row.innerHTML = `<div class="row1"><span class="name">${fileEmoji(f.name)} ${f.name}</span>
      <span class="pct">${fmtSize(f.size)}</span></div>
      <div class="bar"><i></i></div>`;
    $('upList').prepend(row);
    queue.push({file:f, row});
  }
  pump();
}
async function pump(){
  if (uploading) return; uploading = true;
  while (queue.length){
    const job = queue.shift();
    try { await uploadOne(job); }
    catch(e){ markFail(job, e.message); }
  }
  uploading = false;
}
async function uploadOne({file, row}){
  const id = crypto.randomUUID ? crypto.randomUUID() :
    Date.now() + '-' + Math.random().toString(16).slice(2);
  const total = Math.max(1, Math.ceil(file.size / CHUNK));
  const bar = row.querySelector('.bar i'), pct = row.querySelector('.pct');
  row.classList.remove('fail');
  const retryBtn = row.querySelector('.retry'); if (retryBtn) retryBtn.remove();
  for (let i = 0; i < total; i++){
    const blob = file.slice(i*CHUNK, Math.min(file.size, (i+1)*CHUNK));
    let ok = false, lastErr;
    for (let a = 0; a < 3 && !ok; a++){
      try{
        const r = await fetch(`/api/upload/chunk?uploadId=${id}&name=${encodeURIComponent(file.name)}&index=${i}&total=${total}&k=${encodeURIComponent(TOKEN)}`,
          {method:'POST', headers:{'X-Auth':TOKEN,'Content-Type':'application/octet-stream'}, body: blob});
        ok = r.ok;
        if (!ok){ const d = await r.json().catch(()=>({})); lastErr = d.error || r.status; }
      }catch(e){ lastErr = e.message; if (a < 2) await sleep(900*(a+1)); }
    }
    if (!ok) throw new Error(lastErr || '上传失败');
    const done = Math.min(file.size, (i+1)*CHUNK);
    const p = Math.round(done*100/file.size);
    bar.style.width = p + '%';
    pct.textContent = p + '% · ' + fmtSize(done) + ' / ' + fmtSize(file.size);
  }
  await api('/api/upload/finish', {method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({uploadId:id, name:file.name})});
  row.classList.add('done'); pct.textContent = '已完成 ✓';
  toast(`「${file.name}」发送成功`);
}
function markFail({file, row}, msg){
  row.classList.add('fail');
  row.querySelector('.pct').textContent = '失败';
  const b = document.createElement('button');
  b.className = 'retry'; b.textContent = '点击重试(' + msg + ')';
  b.onclick = () => { queue.push({file, row}); pump(); };
  row.appendChild(b);
}

/* ---------- 复制 ---------- */
function flashBtn(btn){
  btn.classList.add('ok');
  const old = btn.textContent;
  btn.textContent = '已复制 ✓';
  setTimeout(()=>{ btn.classList.remove('ok'); btn.textContent = old; }, 1500);
}
function copyText(text, btn){
  const done = () => { toast('已复制 ✓'); if (btn) flashBtn(btn); };
  if (navigator.clipboard && window.isSecureContext){
    navigator.clipboard.writeText(text).then(done).catch(()=>fallbackCopy(text, done));
  } else fallbackCopy(text, done);
}
function fallbackCopy(text, done){
  const ta = document.createElement('textarea');
  ta.value = text; ta.style.cssText = 'position:fixed;opacity:0';
  document.body.appendChild(ta); ta.select();
  try{ document.execCommand('copy'); done(); }catch(e){ toast('复制失败,请长按文字手动复制'); }
  ta.remove();
}

/* ---------- 接收渲染 ---------- */
function renderTexts(texts){
  if (!texts.length) return;
  const list = $('textList');
  const empty = list.querySelector('.empty'); if (empty) empty.remove();
  for (const t of texts.slice().reverse()){
    const card = document.createElement('div');
    card.className = 'tcard fresh';
    const div = document.createElement('div');
    div.textContent = t.text; div.className = 'txt';
    const meta = document.createElement('div'); meta.className = 'meta';
    const chip = document.createElement('span'); chip.className = 'chip';
    chip.textContent = t.time || '';
    const btn = document.createElement('button'); btn.className = 'copy';
    btn.textContent = '复制'; btn.onclick = () => copyText(t.text, btn);
    meta.appendChild(chip); meta.appendChild(btn);
    card.appendChild(meta); card.appendChild(div);
    list.prepend(card);
  }
  if (!$('page-recv').classList.contains('active')){
    unread += texts.length;
    const b = $('badge'); b.textContent = unread; b.classList.add('show');
  }
}
function renderFiles(files){
  const list = $('fileList');
  list.innerHTML = '';
  if (!files.length){
    list.innerHTML = '<div class="empty"><span class="em">🗂️</span>电脑端添加的文件会出现在这里</div>';
    return;
  }
  for (const f of files){
    const row = document.createElement('div'); row.className = 'frow';
    row.innerHTML = `<div class="ico">${fileEmoji(f.name)}</div>
      <div class="info"><div class="fname"></div><div class="fsize">${fmtSize(f.size)}</div></div>
      <a class="dl" href="/api/download?id=${f.id}&k=${encodeURIComponent(TOKEN)}" download>下载</a>`;
    row.querySelector('.fname').textContent = f.name;
    list.appendChild(row);
  }
}

/* ---------- 轮询 ---------- */
async function poll(){
  if (document.hidden) return;
  try{
    const d = await api('/api/updates?cursor=' + cursor);
    $('dot').classList.add('on');
    $('pcname').textContent = '已连接 · ' + (d.pc || '电脑');
    if (d.texts && d.texts.length) renderTexts(d.texts);
    renderFiles(d.files || []);
    cursor = d.cursor || cursor;
  }catch(e){
    $('dot').classList.remove('on');
    $('pcname').textContent = e.message === '口令无效' ? '口令无效,请重新扫码' : '连接中断,重试中…';
  }
}
setInterval(poll, 2000);
poll();
if (location.hash === '#recv') switchTab(true);
</script>
</body>
</html>
"""
