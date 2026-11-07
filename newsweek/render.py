"""渲染 v3：杂志化版式（封面 / 大图头条 / 图文混排 / 专题内页）。"""
from __future__ import annotations

import html as ht
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CSS = r"""
*,*::before,*::after{box-sizing:border-box}
:root{
  --bg:#fcfbf8; --paper:#fff; --ink:#121417; --ink2:#454a52; --ink3:#8b9099;
  --rule:#e3dfd5; --rule2:#cfcabc; --accent:#8c2f1f;
  --serif:"Songti SC","Noto Serif SC",ui-serif,Georgia,"Times New Roman",serif;
  --sans:-apple-system,BlinkMacSystemFont,"SF Pro SC","PingFang SC","Segoe UI",Roboto,sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
  --w:760px;
}
html[data-theme="dark"]{
  --bg:#0f1012; --paper:#15171a; --ink:#f2f1ec; --ink2:#b5b9c0; --ink3:#7b8089;
  --rule:#26282d; --rule2:#33373d; --accent:#d98b76;
}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:16px;line-height:1.75;
  letter-spacing:.01em;-webkit-font-smoothing:antialiased;overflow-x:hidden}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
a{color:inherit;text-decoration:none}
button{font-family:inherit;font-size:inherit;cursor:pointer;background:none;border:none;color:inherit}
.wrap{max-width:var(--w);margin:0 auto;padding:0 20px}
#prog{position:fixed;top:0;left:0;height:2px;width:0;background:var(--accent);z-index:99}

/* ---------- 刊头 ---------- */
.masthead{border-bottom:2px solid var(--ink);margin-top:0;padding:22px 0 10px}
.masthead .inner{max-width:var(--w);margin:0 auto;padding:0 20px;display:flex;align-items:flex-end;justify-content:space-between;gap:14px;flex-wrap:wrap}
.brand{font-family:var(--serif);font-size:clamp(26px,6vw,38px);font-weight:600;letter-spacing:-.01em;line-height:1}
.mast-right{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;color:var(--ink3);text-align:right;line-height:1.7}

/* ---------- 封面 ---------- */
.cover{padding:26px 0 0}
.cover .kicker{font-family:var(--mono);font-size:10px;letter-spacing:.22em;color:var(--accent);text-transform:uppercase;margin-bottom:10px}
.cover h2{font-family:var(--serif);font-size:clamp(29px,7vw,46px);line-height:1.22;letter-spacing:-.015em;margin:0 0 12px;font-weight:600}
.cover .dek{font-family:var(--serif);font-size:clamp(16px,2.4vw,18px);line-height:1.8;color:var(--ink2);margin:0 0 18px;max-width:34em}
.coverlist{list-style:none;margin:16px 0 0;padding:12px 0 0;border-top:1px solid var(--rule)}
.coverlist li{border-bottom:1px solid var(--rule)}
.coverlist li:last-child{border-bottom:none}
.coverlist a{display:grid;grid-template-columns:30px 1fr;gap:8px;padding:8px 0;align-items:baseline}
.coverlist .n{font-family:var(--mono);font-size:10px;color:var(--ink3)}
.coverlist .t{font-size:14.5px;line-height:1.6}
.coverlist a:hover .t{color:var(--accent)}
.cover .theme{font-size:13px;color:var(--ink3);border-top:1px solid var(--rule);padding-top:10px;margin-top:2px}

/* ---------- 图 ---------- */
figure.fig{margin:0 0 16px}
figure.fig img{display:block;width:100%;height:auto;max-height:420px;object-fit:cover;background:var(--rule)}
figure.fig figcaption{display:flex;gap:10px;justify-content:space-between;font-size:11.5px;color:var(--ink3);
  line-height:1.5;padding-top:6px;border-bottom:1px solid var(--rule);padding-bottom:6px}
figure.fig .cap{flex:1}
figure.fig .cred{white-space:nowrap;font-family:var(--mono);font-size:10px;letter-spacing:.04em}
figure.fig.wide img{max-height:460px}

/* ---------- 目录条 ---------- */
.tocbar{position:sticky;top:0;z-index:40;background:color-mix(in srgb,var(--bg) 92%,transparent);
  backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border-bottom:1px solid var(--rule)}
.tocbar .inner{max-width:var(--w);margin:0 auto;padding:8px 20px;display:flex;gap:6px;align-items:center}
.toc{display:flex;gap:2px;overflow-x:auto;flex:1;scrollbar-width:none}
.toc::-webkit-scrollbar{display:none}
.toc a{flex:0 0 auto;font-size:12px;color:var(--ink2);padding:5px 9px;white-space:nowrap;border-bottom:2px solid transparent}
.toc a:hover{color:var(--accent)}
.toc a.on{color:var(--ink);border-color:var(--accent)}
.tool{width:30px;height:30px;display:grid;place-items:center;color:var(--ink3);border:1px solid var(--rule)}
.tool:hover{color:var(--accent);border-color:var(--accent)}
.tool.act{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.searchwrap{display:none;max-width:var(--w);margin:0 auto;padding:0 20px 10px}
.searchwrap.on{display:block}
.search{width:100%;padding:9px 12px;border:1px solid var(--rule2);background:var(--paper);color:var(--ink);
  font-size:14px;outline:none;border-radius:0}
.search:focus{border-color:var(--ink)}

/* ---------- 导语 ---------- */
.standfirst{padding:26px 0 8px;border-bottom:1px solid var(--rule)}
.standfirst p{font-family:var(--serif);font-size:clamp(17px,2.5vw,20px);line-height:1.9;color:var(--ink2);margin:0 0 20px}
.standfirst .byline{font-family:var(--mono);font-size:10px;letter-spacing:.14em;color:var(--ink3);margin-bottom:8px}

/* ---------- 栏目 ---------- */
section.sec{padding:38px 0 0}
.sechead{display:flex;align-items:baseline;gap:10px;padding-bottom:8px}
.sechead .idx{font-family:var(--mono);font-size:11px;color:var(--accent);letter-spacing:.1em}
.sechead h2{font-family:var(--serif);font-size:clamp(21px,4vw,27px);margin:0;font-weight:600}
.sechead .en{font-family:var(--mono);font-size:9.5px;letter-spacing:.24em;color:var(--ink3);margin-left:auto}
.blurb{font-size:12px;color:var(--ink3);margin:0 0 20px;border-bottom:1px solid var(--ink);padding-bottom:8px}

/* ---------- 条目 ---------- */
article.it{padding:0 0 26px;margin:0 0 26px;border-bottom:1px solid var(--rule)}
article.it:last-child{border-bottom:none}
.it .meta{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-family:var(--mono);font-size:10px;
  letter-spacing:.08em;color:var(--ink3);margin-bottom:8px;text-transform:uppercase}
.it .meta .hot{color:var(--accent)}
.it h3{font-family:var(--serif);font-size:clamp(20px,4vw,25px);line-height:1.42;letter-spacing:-.01em;margin:0 0 10px;font-weight:600}
.it.lead h3{font-size:clamp(24px,5vw,32px)}
.it .sum{font-size:15.5px;line-height:1.92;margin:0 0 12px;color:var(--ink)}
.it .why{font-size:13px;line-height:1.75;color:var(--ink2);border-left:2px solid var(--accent);padding-left:10px;margin:0 0 12px}
.it .why b{font-family:var(--mono);font-size:9px;letter-spacing:.14em;color:var(--accent);display:block;margin-bottom:2px}
.kw{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 12px}
.kw span{font-size:10.5px;color:var(--ink3);border:1px solid var(--rule);padding:1px 6px}

/* 紧凑条目：左图右文 */
.it.compact{display:grid;grid-template-columns:132px 1fr;gap:14px;align-items:start}
.it.compact figure.fig{margin:0}
.it.compact figure.fig img{max-height:96px}
.it.compact figure.fig figcaption{display:none}
.it.compact h3{font-size:17px;line-height:1.5;margin-bottom:6px}
.it.compact .sum{font-size:13.5px;line-height:1.8;margin-bottom:8px;
  display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.it.compact .why{margin-bottom:8px}

/* ---------- 观察者 ---------- */
.obs{margin:4px 0 14px;border-top:1px solid var(--rule2);border-bottom:1px solid var(--rule2);background:var(--paper)}
.obs-h{display:flex;align-items:center;gap:10px;padding:9px 0;font-family:var(--mono);font-size:9.5px;
  letter-spacing:.18em;text-transform:uppercase;color:var(--accent)}
.obs-h .sp{flex:1}
.obs-h button{font-family:var(--sans);font-size:12px;letter-spacing:0;text-transform:none;color:var(--ink3)}
.obs-h button:hover{color:var(--accent)}
.obs-pre{padding:0 0 12px;font-size:13px;color:var(--ink3);
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.obs-b{display:none;padding:0 0 14px;font-size:14.5px;line-height:1.9;color:var(--ink2)}
.obs.open .obs-b{display:block}
.obs.open .obs-pre{display:none}
.obs-b .part{margin:0 0 14px}
.obs-b .part:last-child{margin:0}
.obs-b h4{font-family:var(--mono);font-size:9px;letter-spacing:.18em;text-transform:uppercase;color:var(--accent);margin:0 0 4px}
.obs-b p{margin:0}
.obs-b ol{margin:0;padding-left:18px}
.obs-b li{margin-bottom:4px}
.askbox{display:none;padding:0 0 14px}
.askbox.on{display:block}
.askbox textarea{width:100%;min-height:60px;padding:9px 11px;border:1px solid var(--rule2);background:var(--bg);
  color:var(--ink);font-family:inherit;font-size:13.5px;resize:vertical;outline:none;border-radius:0}
.askbox .row{display:flex;justify-content:flex-end;margin-top:8px}
.askbox .row button{padding:6px 16px;background:var(--ink);color:var(--bg);font-size:12.5px}
.answer{margin-top:10px;font-size:13.5px;line-height:1.85;color:var(--ink2);white-space:pre-wrap}

/* ---------- 操作 ---------- */
.acts{display:flex;gap:14px;align-items:center;flex-wrap:wrap;font-size:11.5px;color:var(--ink3)}
.act{display:inline-flex;align-items:center;gap:4px;color:var(--ink3);border-bottom:1px solid transparent;padding-bottom:1px}
.act:hover{color:var(--accent);border-color:var(--accent)}
.act.on{color:var(--accent);border-color:var(--accent)}
.act.src{margin-left:auto;font-family:var(--mono);font-size:10.5px;letter-spacing:.06em}

/* ---------- 深度专题 ---------- */
.deep{margin-top:46px;border-top:3px double var(--ink);padding-top:26px}
.deep .kicker{font-family:var(--mono);font-size:10px;letter-spacing:.22em;color:var(--accent);text-transform:uppercase}
.deep h2{font-family:var(--serif);font-size:clamp(26px,5.5vw,36px);line-height:1.32;margin:10px 0 14px;font-weight:600;letter-spacing:-.01em}
.deep .lead{font-family:var(--serif);font-size:17px;line-height:1.95;color:var(--ink2);margin:0 0 22px}
.dblock{margin:0 0 24px}
.dblock h4{font-family:var(--mono);font-size:9.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--ink3);
  border-bottom:1px solid var(--rule);padding-bottom:6px;margin:0 0 10px}
.dblock p{font-size:15px;line-height:1.95;color:var(--ink2);margin:0}
.dblock p.drop::first-letter{font-family:var(--serif);font-size:3.1em;float:left;line-height:.9;padding:4px 8px 0 0;color:var(--ink)}
.pull{margin:22px 0;padding:14px 0;border-top:1px solid var(--ink);border-bottom:1px solid var(--ink);
  font-family:var(--serif);font-size:20px;line-height:1.6;color:var(--ink)}
.tl{list-style:none;margin:0;padding:0}
.tl li{display:grid;grid-template-columns:84px 1fr;gap:10px;padding:8px 0;border-bottom:1px solid var(--rule)}
.tl .w{font-family:var(--mono);font-size:10.5px;color:var(--accent);letter-spacing:.06em;padding-top:3px}
.tl .t{font-size:14.5px;color:var(--ink2)}
.tn{list-style:none;margin:0;padding:0}
.tn li{padding:9px 0;border-bottom:1px solid var(--rule);font-size:14.5px;line-height:1.8;color:var(--ink2)}
.tn li b{color:var(--ink);font-weight:600;margin-right:6px}
.vw{display:grid;gap:0}
.vw div{padding:11px 0;border-bottom:1px solid var(--rule);font-size:14px;line-height:1.85;color:var(--ink2)}
.vw div b{color:var(--ink);display:block;font-size:12px;margin-bottom:2px;font-weight:600}
.rd{list-style:none;margin:0;padding:0}
.rd li{padding:7px 0;font-size:13.5px;color:var(--ink2);border-bottom:1px solid var(--rule)}
.rd b{color:var(--ink);font-weight:600}

/* ---------- 页脚 ---------- */
footer{margin-top:52px;border-top:2px solid var(--ink);padding:22px 0 64px;font-size:11.5px;color:var(--ink3)}
footer .grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}
footer h6{font-family:var(--mono);font-size:9px;letter-spacing:.2em;text-transform:uppercase;margin:0 0 8px;color:var(--ink3)}
footer ul{list-style:none;margin:0;padding:0}
footer li{display:flex;justify-content:space-between;gap:8px;padding:1px 0}
.ok{color:#2a7f62}.bad{color:#a33}
.foot-btns{display:flex;gap:12px;margin-top:10px;flex-wrap:wrap}
.foot-btns a,.foot-btns button{font-size:11.5px;color:var(--ink2);border-bottom:1px solid var(--rule2)}
.noresult{display:none;padding:30px 0;color:var(--ink3);font-size:14px}
body.searching .noresult.show{display:block}
body.fav-only .cover,body.fav-only .deep,body.fav-only .standfirst{display:none}
body.fav-only .it:not(.fav){display:none}
body.fav-only .sec{display:none}
body.fav-only .sec.has-fav{display:block}

@media (max-width:600px){
  .masthead{padding:16px 0 8px}
  .mast-right{font-size:9.5px}
  .cover{padding:20px 0 0}
  .it.compact{grid-template-columns:96px 1fr;gap:10px}
  .it.compact .sum{-webkit-line-clamp:4}
  footer .grid{grid-template-columns:1fr}
  figure.fig img{max-height:300px}
}
"""

JS = r"""
(function(){
  var root=document.documentElement;
  root.dataset.theme = localStorage.getItem('wb-theme') ||
    (matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');
  var $=function(s,c){return (c||document).querySelector(s)};
  var $$=function(s,c){return [].slice.call((c||document).querySelectorAll(s))};

  var tb=$('#theme');
  function paint(){ if(tb) tb.textContent = root.dataset.theme==='dark'?'☀':'☾'; }
  if(tb) tb.addEventListener('click',function(){
    var n=root.dataset.theme==='dark'?'light':'dark';
    root.dataset.theme=n; localStorage.setItem('wb-theme',n); paint();
  });
  paint();

  var prog=$('#prog');
  function onScroll(){ var h=document.documentElement;
    if(prog) prog.style.width=(h.scrollTop/(h.scrollHeight-h.clientHeight)*100)+'%'; }
  addEventListener('scroll',onScroll,{passive:true}); onScroll();

  var links=$$('.toc a'), secs=links.map(function(a){return $(a.getAttribute('href'))});
  if('IntersectionObserver' in window){
    var io=new IntersectionObserver(function(es){ es.forEach(function(e){ if(e.isIntersecting){
      var i=secs.indexOf(e.target); links.forEach(function(l,j){l.classList.toggle('on',j===i)}); }}); },
      {rootMargin:'-45% 0px -50% 0px'});
    secs.forEach(function(s){ if(s) io.observe(s); });
  }

  function load(k,d){ try{return JSON.parse(localStorage.getItem(k))||d}catch(e){return d} }
  var favs=load('wb-favs',{}), fb=load('wb-feedback',{}), watch=load('wb-watch',[]);
  function syncFav(){
    $$('.it').forEach(function(el){ el.classList.toggle('fav', !!favs[el.dataset.id]); });
    $$('[data-act="fav"]').forEach(function(b){ b.classList.toggle('on', !!favs[b.dataset.id]); });
    $$('.sec').forEach(function(s){ s.classList.toggle('has-fav', $$('.it.fav',s).length>0); });
  }
  function syncFb(){
    $$('[data-act="like"],[data-act="dislike"]').forEach(function(b){
      b.classList.toggle('on', fb[b.dataset.id]===b.dataset.act); });
  }

  document.addEventListener('click',function(e){
    var b=e.target.closest('[data-act]'); if(!b) return;
    var id=b.dataset.id, act=b.dataset.act;
    if(act==='fav'){ favs[id]=!favs[id]; localStorage.setItem('wb-favs',JSON.stringify(favs)); syncFav(); }
    if(act==='like'||act==='dislike'){ fb[id]=fb[id]===act?null:act;
      localStorage.setItem('wb-feedback',JSON.stringify(fb)); syncFb(); }
    if(act==='watch'){ var t=b.dataset.topic||'';
      if(t && watch.indexOf(t)<0){ watch.push(t); localStorage.setItem('wb-watch',JSON.stringify(watch));
        b.classList.add('on'); b.textContent='已加入观察'; } }
    if(act==='obs'){ var box=b.closest('.obs'); box.classList.toggle('open');
      b.textContent=box.classList.contains('open')?'收起':'展开'; }
    if(act==='ask'){ var ab=b.closest('.obs').querySelector('.askbox'); ab.classList.toggle('on');
      var ta=ab.querySelector('textarea'); if(ta) ta.focus(); }
  });

  var fbBtn=$('#favfilter');
  if(fbBtn) fbBtn.addEventListener('click',function(){
    document.body.classList.toggle('fav-only');
    fbBtn.classList.toggle('act', document.body.classList.contains('fav-only'));
  });

  var sBtn=$('#sbtn'), sWrap=$('#searchwrap'), sInput=$('#search');
  function clearSearch(){ document.body.classList.remove('searching');
    $$('.it').forEach(function(el){el.classList.remove('none')});
    $$('section.sec').forEach(function(s){s.classList.remove('none')}); if(sInput) sInput.value=''; }
  function runSearch(){
    var q=(sInput.value||'').trim().toLowerCase();
    if(!q){ clearSearch(); return; }
    document.body.classList.add('searching'); var any=false;
    $$('.it').forEach(function(el){ var hit=(el.dataset.text||'').indexOf(q)>=0;
      el.classList.toggle('none',!hit); if(hit) any=true; });
    $$('section.sec').forEach(function(s){ s.classList.toggle('none', $$('.it:not(.none)',s).length===0); });
    var nr=$('#noresult'); if(nr) nr.classList.toggle('show',!any);
  }
  if(sBtn) sBtn.addEventListener('click',function(){ sWrap.classList.toggle('on');
    if(sWrap.classList.contains('on')) sInput.focus(); else clearSearch(); });
  if(sInput) sInput.addEventListener('input',runSearch);

  document.addEventListener('submit',function(e){
    if(!e.target.matches('.askform')) return;
    e.preventDefault();
    var form=e.target, box=form.closest('.askbox'), out=box.querySelector('.answer');
    var q=form.querySelector('textarea').value.trim(); if(!q) return;
    out.textContent='思考中…';
    fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({issue:window.WB_ISSUE||'', id:box.dataset.id,
        headline:box.dataset.headline, summary:box.dataset.summary, question:q})})
      .then(function(r){return r.json()})
      .then(function(d){ out.textContent=d.answer||d.error||'没有返回内容'; })
      .catch(function(){ out.textContent='追问需要本地服务：python3 serve.py 后访问 127.0.0.1:8000'; });
  });

  var exp=$('#export');
  if(exp) exp.addEventListener('click',function(){
    var data={favorites:Object.keys(favs).filter(function(k){return favs[k]}), feedback:fb,
      watch:watch, exported_at:new Date().toISOString()};
    var blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
    var a=document.createElement('a'); a.href=URL.createObjectURL(blob);
    a.download='wb-profile.json'; a.click();
  });
  syncFav(); syncFb();
})();
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>__TITLE__</title>
<meta name="description" content="__DESC__">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#fcfbf8">
<meta property="og:title" content="__TITLE__">
<meta property="og:description" content="__DESC__">
<meta property="og:image" content="__OGIMG__">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' fill='%23121417'/><text x='50' y='68' font-size='52' text-anchor='middle' fill='%23fff' font-family='serif'>W</text></svg>">
<style>__CSS__</style>
</head>
<body>
<div id="prog"></div>
__BODY__
<script>window.WB_ISSUE="__WEEK__";</script>
<script>__JS__</script>
</body>
</html>
"""


def esc(s) -> str:
    return ht.escape(str(s or ""), quote=True)


def _figure(img: dict, wide: bool = False, show_cap: bool = True) -> str:
    if not img:
        return ""
    cap = (img.get("alt") or "").strip() or "报道配图"
    cred = (img.get("credit") or "").strip()
    cap_html = (
        f'<figcaption><span class="cap">{esc(cap)}</span>'
        f'<span class="cred">{esc(cred)}</span></figcaption>'
        if show_cap
        else ""
    )
    return (
        f'<figure class="fig{" wide" if wide else ""}">'
        f'<img src="{esc(img["url"])}" width="{img.get("w",0)}" height="{img.get("h",0)}" '
        f'alt="{esc(img.get("alt") or "")}" loading="lazy" referrerpolicy="no-referrer" '
        f'onerror="this.closest(\'figure\').remove()">{cap_html}</figure>'
    )


def _item_text(item: dict, section: dict) -> str:
    parts = [item.get("headline", ""), item.get("summary", ""), item.get("why", ""),
             " ".join(item.get("keywords") or []), item.get("source", ""), section.get("name", "")]
    take = item.get("take") or {}
    parts += [take.get("text", ""), take.get("background", "")]
    return esc(" ".join(parts).lower())


def _obs_html(item: dict) -> str:
    take = item.get("take") or {}
    if take.get("mode") == "full":
        qs = "".join(f"<li>{esc(q)}</li>" for q in take.get("questions") or [])
        body = (
            f'<div class="part"><h4>事件背后</h4><p>{esc(take.get("background",""))}</p></div>'
            f'<div class="part"><h4>深层影响</h4><p>{esc(take.get("impact",""))}</p></div>'
            f'<div class="part"><h4>不同视角</h4><p>{esc(take.get("perspectives",""))}</p></div>'
            + (f'<div class="part"><h4>值得思考</h4><ol>{qs}</ol></div>' if qs else "")
        )
        prev = esc((take.get("background", "") or "")[:90]) + "…"
    else:
        text = take.get("text", "")
        if not text:
            return ""
        body = f'<div class="part"><p>{esc(text)}</p></div>'
        prev = esc(text[:100]) + "…"
    iid = esc(item.get("id", ""))
    return f"""<div class="obs">
  <div class="obs-h"><span>观察者视角</span><span class="sp"></span>
    <button data-act="ask" data-id="{iid}">追问</button>
    <button data-act="obs" data-id="{iid}">展开</button></div>
  <div class="obs-pre">{prev}</div>
  <div class="obs-b">{body}</div>
  <div class="askbox" data-id="{iid}" data-headline="{esc(item.get('headline',''))}" data-summary="{esc((item.get('summary') or '')[:300])}">
    <form class="askform"><textarea placeholder="就这条新闻继续追问：这个判断有哪些反例？"></textarea>
    <div class="row"><button type="submit">提问</button></div></form>
    <div class="answer"></div></div>
</div>"""


def _item_html(item: dict, section: dict, lead: bool = False, compact: bool = False) -> str:
    imp = int(item.get("importance") or 1)
    tag = {3: "重点", 2: "关注", 1: "速览"}.get(imp, "速览")
    extra = [s for s in (item.get("sources_all") or []) if s and s != item.get("source")]
    cross = f'<span>+{len(extra)} 家</span>' if extra else ""
    kws = "".join(f"<span>{esc(k)}</span>" for k in item.get("keywords") or [])
    if item.get("watch"):
        kws += "".join(f'<span style="color:var(--accent);border-color:var(--accent)">观察：{esc(w)}</span>' for w in item["watch"])
    why = f'<p class="why"><b>为什么重要</b>{esc(item.get("why",""))}</p>' if item.get("why") else ""
    fig = _figure(item.get("image") or {}, wide=lead, show_cap=not compact)
    topic = esc((item.get("keywords") or [""])[0] or section.get("name", ""))
    cls = "it lead" if lead else ("it compact" if compact else "it")
    body = f"""{fig}
  <h3>{esc(item.get('headline',''))}</h3>
  <p class="sum">{esc(item.get('summary',''))}</p>
  {why}
  {f'<div class="kw">{kws}</div>' if kws and not compact else ''}"""
    actions = f"""<div class="acts">
    <button class="act" data-act="fav" data-id="{esc(item.get('id',''))}">收藏</button>
    <button class="act" data-act="like" data-id="{esc(item.get('id',''))}">感兴趣</button>
    <button class="act" data-act="dislike" data-id="{esc(item.get('id',''))}">不感兴趣</button>
    <button class="act" data-act="watch" data-topic="{topic}" data-id="{esc(item.get('id',''))}">加入观察</button>
    <a class="act src" href="{esc(item.get('url',''))}" target="_blank" rel="noopener">原文 ↗</a>
  </div>"""
    meta = f"""<div class="meta"><span class="{"hot" if imp>=3 else ""}">{tag}</span>
    <span>{esc(item.get('source',''))}</span><span>{esc(item.get('date_pub',''))}</span>{cross}
    {f'<span>事件 {esc(item["event_date"])}</span>' if item.get('event_date') else ''}</div>"""
    obs = "" if compact else _obs_html(item)
    return (f'<article class="{cls}" id="i-{esc(item.get("id",""))}" data-id="{esc(item.get("id",""))}" '
            f'data-text="{_item_text(item, section)}">{meta}{body}{obs}{actions}</article>')


def _section_html(sec: dict, skip_image_id: str = "") -> str:
    items = sec["items"]
    out = []
    for i, it in enumerate(items):
        compact = (i > 0 and int(it.get("importance") or 1) == 1 and bool(it.get("image")))
        if it.get("id") == skip_image_id:
            it = {**it, "image": None}
        out.append(_item_html(it, sec, lead=(i == 0), compact=compact))
    return f"""<section class="sec" id="{esc(sec['key'])}">
  <div class="sechead"><span class="idx">{esc(sec.get('idx',''))}</span>
    <h2>{esc(sec['name'])}</h2><span class="en">{esc(sec.get('en',''))}</span></div>
  <p class="blurb">{esc(sec.get('blurb',''))}</p>
  {"".join(out)}
</section>"""


def _cover_html(issue: dict, cfg: dict, lead: dict | None = None) -> str:
    sec_map = {s["key"]: s for s in issue["sections"]}
    top = [it for s in issue["sections"] for it in s["items"] if it["id"] in set(issue.get("top_ids") or [])]
    if not top:
        return ""
    lead = lead or top[0]
    sec = sec_map.get(lead["section"], {})
    others = [it for it in top if it["id"] != lead["id"]][:4]
    list_html = "".join(
        f'<li><a href="#i-{esc(it["id"])}"><span class="n">{i:02d}</span>'
        f'<span class="t">{esc(it["headline"])}</span></a></li>'
        for i, it in enumerate(others, 1)
    )
    fig = _figure(lead.get("image") or {}, wide=True)
    return f"""<section class="cover"><div class="wrap">
  <div class="kicker">{esc(sec.get('name',''))} · 本期封面</div>
  <h2><a href="#i-{esc(lead['id'])}">{esc(lead['headline'])}</a></h2>
  <p class="dek">{esc((lead.get('summary','') or '')[:150])}{'…' if len(lead.get('summary','') or '')>150 else ''}</p>
  {fig}
  {f'<div class="theme">本期主题 · {esc(issue["note"])}</div>' if issue.get('note') else ''}
  {f'<ul class="coverlist">{list_html}</ul>' if list_html else ''}
</div></section>"""


def _deep_html(dd: dict, image: dict | None = None) -> str:
    if not dd or not dd.get("question"):
        return ""
    fig = _figure(image or {}, wide=True)
    tl = "".join(
        f'<li><span class="w">{esc(t.get("when",""))}</span><span class="t">{esc(t.get("what",""))}</span></li>'
        for t in dd.get("timeline") or []
    )
    tn = "".join(f"<li>{esc(t)}</li>" for t in dd.get("tensions") or [])
    vw = "".join(
        f'<div><b>{esc(v.get("stance",""))}</b>{esc(v.get("claim",""))}</div>' for v in dd.get("views") or []
    )
    rd = "".join(
        f'<li><b>{esc(r.get("title",""))}</b>　{esc(r.get("author",""))}——{esc(r.get("why",""))}</li>'
        for r in dd.get("reading") or []
    )
    blocks = []
    if dd.get("background"):
        blocks.append(f'<div class="dblock"><h4>背景脉络</h4><p class="drop">{esc(dd["background"])}</p></div>')
    if tl:
        blocks.append(f'<div class="dblock"><h4>时间线</h4><ul class="tl">{tl}</ul></div>')
    if tn:
        blocks.append(f'<div class="dblock"><h4>核心矛盾</h4><ul class="tn">{tn}</ul></div>')
    if vw:
        blocks.append(f'<div class="dblock"><h4>不同立场</h4><div class="vw">{vw}</div></div>')
    if rd:
        blocks.append(
            '<div class="dblock"><h4>延伸阅读</h4><ul class="rd">' + rd + "</ul>"
            '<p style="margin-top:6px;font-size:11px;color:var(--ink3)">书目由模型推荐，请自行核实。</p></div>'
        )
    return f"""<section class="deep" id="deep">
  <div class="kicker">08 · 本周深度观察</div>
  <h2>{esc(dd["question"])}</h2>
  <p class="lead">{esc(dd.get("lead",""))}</p>
  {fig}
  {"".join(blocks)}
</section>"""


def _footer_html(issue: dict) -> str:
    st = issue.get("stats", {})
    usage = st.get("usage") or {}
    rows = "".join(
        f'<li><span>{esc(s["name"])}</span><span class="{"ok" if s["ok"] else "bad"}">'
        f'{"✓" if s["ok"] else "×"}</span></li>' for s in issue.get("sources", [])[:16]
    )
    tokens = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
    imgs = sum(1 for s in issue["sections"] for it in s["items"] if it.get("image"))
    return f"""<footer><div class="wrap"><div class="grid">
  <div><h6>数据来源 · {st.get('sources_ok',0)}/{st.get('sources_total',0)}</h6><ul>{rows}</ul></div>
  <div><h6>本期</h6><ul>
    <li><span>生成</span><span>{esc(issue.get('generated_date',''))} {esc((issue.get('generated_at') or '')[11:16])}</span></li>
    <li><span>条目</span><span>{st.get('items',0)} 条 / {imgs} 张图</span></li>
    <li><span>处理</span><span>{st.get('articles',0)} 篇</span></li>
    <li><span>模型</span><span>{tokens/1000:.0f}k tokens</span></li>
  </ul>
  <h6 style="margin-top:14px">更多</h6>
  <div class="foot-btns"><a href="__ARCHIVE__">往期</a><a href="__THINKING__">思想档案</a>
  <button id="export">导出阅读数据</button></div></div>
</div></div></footer>"""


def render_issue(issue: dict, cfg: dict) -> str:
    sections = issue["sections"]
    nav = "".join(
        f'<a href="#{esc(s["key"])}">{esc(s.get("idx",""))} {esc(s["name"])}</a>' for s in sections
    ) + ('<a href="#deep">08 深度观察</a>' if issue.get("deep_dive") else "")

    id_map = {it["id"]: it for s in sections for it in s["items"]}
    top_ids = list(issue.get("top_ids") or [])
    cover_lead = next((id_map[i] for i in top_ids if id_map.get(i, {}).get("image")), id_map.get(top_ids[0]) if top_ids else None)
    cover = _cover_html(issue, cfg, cover_lead)
    cover_lead_id = (cover_lead or {}).get("id", "")
    standfirst = ""
    if issue.get("opening"):
        standfirst = f"""<section class="standfirst"><div class="wrap">
  <div class="byline">编者按</div><p>{esc(issue["opening"])}</p></div></section>"""

    bar = f"""<div class="tocbar"><div class="inner">
  <div class="toc">{nav}</div>
  <button class="tool" id="sbtn" aria-label="搜索">⌕</button>
  <button class="tool" id="favfilter" aria-label="只看收藏">☆</button>
  <button class="tool" id="theme" aria-label="主题">☾</button>
</div><div class="searchwrap" id="searchwrap">
  <input id="search" class="search" type="search" placeholder="搜索标题、摘要、关键词…">
</div></div>"""

    cover_img = None
    for s in sections:
        for it in s["items"]:
            if it.get("image"):
                cover_img = it["image"]["url"]
                break
        if cover_img:
            break
    deep_img = None
    for s in sections:
        for it in s["items"]:
            img = it.get("image")
            if img and img["url"] != cover_img:
                deep_img = img
                break
        if deep_img:
            break

    mast = f"""<div class="masthead"><div class="inner">
  <div class="brand">WEEKLY BRIEF</div>
  <div class="mast-right">{esc(issue['week'])}　{esc(issue['range'])}<br>第 {esc(issue['week'].split('W')[-1])} 期 · 每周五</div>
</div></div>"""

    main = (
        mast
        + cover
        + bar
        + standfirst
        + '<main class="wrap">'
        + "".join(_section_html(s, cover_lead_id) for s in sections)
        + _deep_html(issue.get("deep_dive") or {}, None)
        + '<div class="noresult" id="noresult">没有匹配的新闻，换个关键词。</div></main>'
        + _footer_html(issue)
    )

    archive = "../archive.html" if issue.get("_in_issues_dir") else "archive.html"
    thinking = "../thinking.html" if issue.get("_in_issues_dir") else "thinking.html"
    main = main.replace("__ARCHIVE__", archive).replace("__THINKING__", thinking)

    og_img = ""
    for s in sections:
        for it in s["items"]:
            if it.get("image"):
                og_img = it["image"]["url"]
                break
        if og_img:
            break

    return (
        TEMPLATE.replace("__CSS__", CSS)
        .replace("__JS__", JS)
        .replace("__BODY__", main)
        .replace("__WEEK__", issue["week"])
        .replace("__OGIMG__", esc(og_img))
        .replace("__TITLE__", f"{cfg.get('title','WEEKLY BRIEF')} · {issue['week']}")
        .replace("__DESC__", esc((issue.get("opening") or issue["range"])[:120]))
    )


def render_archive(index: dict) -> str:
    rows = "".join(
        f'<li><a href="issues/{esc(i["week"])}.html"><span class="w">{esc(i["week"])}</span>'
        f'<span class="t">{esc(i["range"])}　{esc(i.get("note",""))}</span>'
        f'<span class="c">{i.get("items",0)} 条</span></a></li>'
        for i in index.get("issues", [])
    )
    body = f"""<div class="masthead"><div class="inner">
  <div class="brand">WEEKLY BRIEF</div><div class="mast-right">ARCHIVE</div></div></div>
<div class="tocbar"><div class="inner"><div class="toc">
  <a href="index.html">最新一期</a><a href="thinking.html">思想档案</a></div></div></div>
<main class="wrap" style="padding-top:26px">
  <h1 style="font-family:var(--serif);font-size:32px;margin:0 0 6px">往期</h1>
  <p style="color:var(--ink3);font-size:13px;margin:0 0 20px">共 {len(index.get('issues', []))} 期，可在下方检索全部历史新闻。</p>
  <input id="q" class="search" placeholder="在全部历史新闻里搜索…">
  <div id="hits" style="margin-top:16px"></div>
  <ul class="archlist">{rows}</ul>
</main>"""
    extra = """
ul.archlist{list-style:none;margin:26px 0 0;padding:0}
ul.archlist li{border-bottom:1px solid var(--rule)}
ul.archlist a{display:grid;grid-template-columns:92px 1fr auto;gap:10px;padding:12px 0;align-items:baseline}
ul.archlist .w{font-family:var(--mono);font-size:11px;color:var(--accent)}
ul.archlist .t{font-size:14px}
ul.archlist .c{font-size:11px;color:var(--ink3)}
.hit{padding:11px 0;border-bottom:1px solid var(--rule)}
.hit b{font-size:14.5px}
.hit span{display:block;font-size:11.5px;color:var(--ink3);margin-top:2px}
"""
    script = """
(function(){
  var data=null,hits=document.getElementById('hits'),q=document.getElementById('q');
  fetch('data/index.json').then(function(r){return r.json()}).then(function(d){data=d}).catch(function(){});
  q.addEventListener('input',function(){
    var v=q.value.trim().toLowerCase(); if(!data) return;
    if(!v){hits.innerHTML='';return;}
    var rows=data.items.filter(function(it){return (it.h+' '+it.d+' '+it.k).toLowerCase().indexOf(v)>=0}).slice(0,40);
    hits.innerHTML=rows.length?rows.map(function(it){
      return '<div class="hit"><a href="issues/'+it.w+'.html#i-'+it.i+'"><b>'+it.h+'</b></a>'+
             '<span>'+it.w+' · '+it.s+'</span></div>';}).join(''):'<p style="color:var(--ink3)">没有找到。</p>';
  });
})();
"""
    return (
        TEMPLATE.replace("__CSS__", CSS + extra).replace("__JS__", JS + script).replace("__BODY__", body)
        .replace("__WEEK__", "").replace("__OGIMG__", "").replace("__TITLE__", "往期 · WEEKLY BRIEF")
        .replace("__DESC__", "往期周报与历史新闻检索")
    )


def render_thinking(index: dict, issues: list[dict]) -> str:
    items = []
    for d in issues:
        for q in d.get("questions3") or []:
            items.append(f'<li><span class="w">{esc(d.get("week",""))}</span><span class="t">{esc(q)}</span></li>')
    body = f"""<div class="masthead"><div class="inner">
  <div class="brand">WEEKLY BRIEF</div><div class="mast-right">THINKING<br>ARCHIVE</div></div></div>
<div class="tocbar"><div class="inner"><div class="toc">
  <a href="index.html">最新一期</a><a href="archive.html">往期</a></div></div></div>
<main class="wrap" style="padding-top:26px">
  <h1 style="font-family:var(--serif);font-size:32px;margin:0 0 6px">思想档案</h1>
  <p style="color:var(--ink3);font-size:13px;margin:0 0 22px">每周三个值得长期思考的问题。</p>
  <ul class="tl">{''.join(items) or '<li><span class="t">还没有积累。</span></li>'}</ul>
  <h2 style="font-family:var(--serif);font-size:22px;margin:34px 0 10px;border-top:2px solid var(--ink);padding-top:14px">我的观察清单</h2>
  <ul class="tl" id="watchlist"></ul>
</main>""" + WATCH_SCRIPT
    return (
        TEMPLATE.replace("__CSS__", CSS).replace("__JS__", JS).replace("__BODY__", body)
        .replace("__WEEK__", "").replace("__OGIMG__", "").replace("__TITLE__", "思想档案 · WEEKLY BRIEF")
        .replace("__DESC__", "每周三个值得长期思考的问题")
    )


WATCH_SCRIPT = """
<script>
(function(){
  try{
    var w=JSON.parse(localStorage.getItem('wb-watch'))||[];
    document.getElementById('watchlist').innerHTML = w.length
      ? w.map(function(t){return '<li><span class="t">'+t+'</span></li>'}).join('')
      : '<li><span class="t">在新闻卡片上点「加入观察」，这里会出现你长期关注的议题。</span></li>';
  }catch(e){}
})();
</script>"""


def write_site(issue: dict, cfg: dict) -> str:
    out = os.path.join(ROOT, cfg.get("output", {}).get("dir", "site"))
    os.makedirs(os.path.join(out, "issues"), exist_ok=True)
    os.makedirs(os.path.join(out, "data"), exist_ok=True)

    data_dir = os.path.join(out, "data")
    issues_meta, all_raw = [], []
    for name in sorted(os.listdir(data_dir), reverse=True):
        if not name.endswith(".json") or name in ("index.json", "profile.json"):
            continue
        try:
            with open(os.path.join(data_dir, name), encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception:  # noqa: BLE001
            continue
        issues_meta.append({
            "week": d.get("week", name[:-5]),
            "range": d.get("range", ""),
            "note": d.get("note", ""),
            "items": sum(len(s["items"]) for s in d.get("sections", [])),
        })
        all_raw.append(d)

    with open(os.path.join(out, "issues", f"{issue['week']}.html"), "w", encoding="utf-8") as fh:
        fh.write(render_issue({**issue, "_in_issues_dir": True}, cfg))
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(render_issue({**issue, "_in_issues_dir": False}, cfg))
    with open(os.path.join(out, "archive.html"), "w", encoding="utf-8") as fh:
        fh.write(render_archive({"issues": issues_meta}))
    with open(os.path.join(out, "thinking.html"), "w", encoding="utf-8") as fh:
        fh.write(render_thinking({"issues": issues_meta}, all_raw))
    return os.path.join(out, "issues", f"{issue['week']}.html")
