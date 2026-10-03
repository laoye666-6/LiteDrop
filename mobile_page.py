# -*- coding: utf-8 -*-
"""轻传 LiteDrop — 手机端页面(单文件内嵌,无外部依赖)。"""

PAGE_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0a0f1c">
<title>轻传 LiteDrop</title>
<style>
:root{
  --bg:#0a0f1c; --card:#121a2b; --card2:#0d1526; --line:rgba(255,255,255,.07);
  --text:#e8eef9; --muted:#8ca0c0; --ac1:#4f7cff; --ac2:#22d3ee;
  --grad:linear-gradient(135deg,#4f7cff,#22d3ee);
  --danger:#ef4444; --ok:#34d399;
}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
html,body{height:100%}
body{
  background:var(--bg); color:var(--text);
  font-family:-apple-system,"PingFang SC","HarmonyOS Sans SC","Microsoft YaHei",sans-serif;
  padding-bottom:calc(64px + env(safe-area-inset-bottom));
  background-image:radial-gradient(600px 240px at 50% -60px,rgba(79,124,255,.18),transparent);
}
button{font-family:inherit;border:0;cursor:pointer;color:inherit}
/* ---------- 头部 ---------- */
header{
  padding:calc(14px + env(safe-area-inset-top)) 18px 16px;
  background:var(--grad); color:#fff; border-radius:0 0 26px 26px;
  box-shadow:0 8px 28px rgba(79,124,255,.35);
}
header h1{font-size:20px;font-weight:700;letter-spacing:.5px}
header .sub{font-size:12px;opacity:.9;margin-top:4px;display:flex;align-items:center;gap:6px}
.dot{width:8px;height:8px;border-radius:50%;background:#fff;opacity:.85;flex:none}
.dot.on{background:#b9ffdf;box-shadow:0 0 8px #b9ffdf}
/* ---------- 主体 ---------- */
main{padding:16px 14px;max-width:560px;margin:0 auto}
.page{display:none;animation:fadein .25s ease}
.page.active{display:block}
@keyframes fadein{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px;margin-bottom:14px}
.sect{font-size:13px;color:var(--muted);margin:2px 2px 10px;font-weight:600;letter-spacing:1px}
textarea{
  width:100%;min-height:110px;resize:vertical;background:var(--card2);
  border:1px solid var(--line);border-radius:14px;color:var(--text);
  padding:12px;font-size:15px;line-height:1.5;outline:none;transition:border-color .2s;
}
textarea:focus{border-color:var(--ac1)}
.btn-main{
  display:block;width:100%;padding:13px;border-radius:14px;margin-top:12px;
  background:var(--grad);color:#fff;font-size:16px;font-weight:600;
  box-shadow:0 6px 18px rgba(79,124,255,.35);transition:transform .12s,opacity .2s;
}
.btn-main:active{transform:scale(.97)}
.btn-main:disabled{opacity:.5;box-shadow:none}
/* ---------- 选择文件区 ---------- */
.drop{
  border:1.5px dashed #2c3d60;border-radius:16px;padding:26px 12px;text-align:center;
  color:var(--muted);font-size:14px;transition:border-color .2s,background .2s;user-select:none;
}
.drop:active,.drop.over{border-color:var(--ac1);background:rgba(79,124,255,.08)}
.drop .em{font-size:30px;display:block;margin-bottom:8px}
/* ---------- 上传队列 ---------- */
.up{display:flex;flex-direction:column;gap:10px}
.uprow{background:var(--card2);border:1px solid var(--line);border-radius:12px;padding:10px 12px}
.uprow .row1{display:flex;justify-content:space-between;gap:8px;font-size:13px;margin-bottom:8px}
.uprow .name{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1}
.uprow .pct{color:var(--muted);flex:none}
.bar{height:6px;border-radius:4px;background:#1c2740;overflow:hidden}
.bar i{display:block;height:100%;width:0;background:var(--grad);border-radius:4px;transition:width .25s ease}
.uprow.done .pct{color:var(--ok)}
.uprow.fail .pct{color:var(--danger)}
.uprow.fail .bar i{background:var(--danger)}
.retry{margin-top:8px;background:rgba(239,68,68,.15);color:var(--danger);
  border-radius:8px;padding:5px 12px;font-size:12px}
/* ---------- 接收 ---------- */
.tcard{background:var(--card);border:1px solid var(--line);border-radius:16px;
  padding:12px 14px;margin-bottom:12px}
.tcard.fresh{animation:pop .35s ease}
@keyframes pop{0%{opacity:0;transform:translateY(10px) scale(.98)}100%{opacity:1;transform:none}}
.tcard .meta{display:flex;align-items:center;gap:8px;margin-bottom:6px}
.chip{font-size:11px;color:var(--muted);background:var(--card2);
  border-radius:20px;padding:2px 10px}
.tcard .txt{font-size:15px;line-height:1.55;white-space:pre-wrap;word-break:break-word}
.copy{margin-left:auto;background:rgba(79,124,255,.16);color:#8fb0ff;
  border-radius:20px;padding:4px 14px;font-size:12px}
.frow{display:flex;align-items:center;gap:12px;background:var(--card);
  border:1px solid var(--line);border-radius:16px;padding:12px 14px;margin-bottom:12px}
.frow .ico{width:40px;height:40px;flex:none;border-radius:12px;display:flex;
  align-items:center;justify-content:center;font-size:20px;background:rgba(79,124,255,.15)}
.frow .info{flex:1;min-width:0}
.frow .fname{font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.frow .fsize{font-size:12px;color:var(--muted);margin-top:3px}
.dl{flex:none;background:var(--grad);color:#fff;border-radius:20px;
  padding:7px 16px;font-size:13px;font-weight:600;text-decoration:none}
.empty{text-align:center;color:var(--muted);padding:44px 0;font-size:14px}
.empty .em{font-size:42px;display:block;margin-bottom:12px;opacity:.8}
/* ---------- 底部导航 ---------- */
nav{
  position:fixed;left:0;right:0;bottom:0;z-index:9;
  display:flex;justify-content:space-around;
  background:rgba(13,21,38,.92);backdrop-filter:blur(12px);
  border-top:1px solid var(--line);
  padding:8px 0 calc(8px + env(safe-area-inset-bottom));
}
.navbtn{position:relative;background:none;font-size:12px;color:var(--muted);
  display:flex;flex-direction:column;align-items:center;gap:3px;padding:4px 22px;
  transition:color .2s}
.navbtn .em{font-size:22px}
.navbtn.active{color:#8fb0ff}
.badge{position:absolute;top:-2px;right:12px;min-width:16px;height:16px;
  border-radius:9px;background:var(--danger);color:#fff;font-size:10px;
  display:none;align-items:center;justify-content:center;padding:0 4px;font-weight:700}
.badge.show{display:flex}
/* ---------- Toast ---------- */
#toast{position:fixed;left:50%;bottom:calc(84px + env(safe-area-inset-bottom));
  transform:translateX(-50%) translateY(16px);background:#1b2946;color:var(--text);
  border:1px solid var(--line);border-radius:24px;padding:9px 20px;font-size:13px;
  opacity:0;pointer-events:none;transition:opacity .25s,transform .25s;z-index:99;
  max-width:82vw;box-shadow:0 8px 24px rgba(0,0,0,.4)}
#toast.show{opacity:1;transform:translateX(-50%)}
</style>
</head>
<body>
<header>
  <h1>轻传 LiteDrop</h1>
  <div class="sub"><span class="dot" id="dot"></span><span id="pcname">连接中…</span></div>
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
      <span style="font-size:12px;opacity:.7">大文件自动分块,支持断点重试</span>
    </div>
    <input type="file" id="fileInput" multiple hidden>
    <div class="up" id="upList" style="margin-top:12px"></div>
  </section>

  <!-- 接收 -->
  <section class="page" id="page-recv">
    <div class="sect">来自电脑的文本</div>
    <div id="textList"><div class="empty"><span class="em">📭</span>还没有内容<br>在电脑端发送文本后会出现在这里</div></div>
    <div class="sect" style="margin-top:20px">来自电脑的文件</div>
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
    row.innerHTML = `<div class="row1"><span class="name">${f.name}</span>
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
    bar.style.width = (done*100/file.size).toFixed(1) + '%';
    pct.textContent = Math.round(done*100/file.size) + '%';
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
  b.className = 'retry'; b.textContent = '重试(' + msg + ')';
  b.onclick = () => { queue.push({file, row}); pump(); };
  row.appendChild(b);
}

/* ---------- 复制 ---------- */
function copyText(text){
  const done = () => toast('已复制 ✓');
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
    btn.textContent = '复制'; btn.onclick = () => copyText(t.text);
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
    row.innerHTML = `<div class="ico">📄</div>
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
