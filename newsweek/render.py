"""渲染 v2：信息杂志风格的周报页面（自包含 HTML，手机优先）。"""
from __future__ import annotations

import html as ht
import json
import os
from datetime import datetime

from .util import TZ

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CSS = r"""
*,*::before,*::after{box-sizing:border-box}
:root{
  --bg:#fbfaf7; --bg2:#f2f0ea; --card:#fff; --fg:#14161a; --fg2:#4b4f57; --fg3:#8a8f98;
  --line:#e4e1d8; --accent:#3d5a80; --shadow:0 1px 2px rgba(20,20,25,.04),0 14px 34px -22px rgba(20,20,25,.3);
  --serif:"Songti SC","Noto Serif SC",ui-serif,Georgia,"Times New Roman",serif;
  --sans:-apple-system,BlinkMacSystemFont,"SF Pro SC","PingFang SC","Segoe UI",Roboto,"Helvetica Neue",sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
  --maxw:740px;
}
html[data-theme="dark"]{
  --bg:#0f1012; --bg2:#17191c; --card:#15171a; --fg:#f2f1ec; --fg2:#b6b9c0; --fg3:#7c818a;
  --line:#26282d; --shadow:0 1px 2px rgba(0,0,0,.5),0 18px 40px -24px rgba(0,0,0,.8);
}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--sans);font-size:16px;line-height:1.75;
  letter-spacing:.01em;-webkit-font-smoothing:antialiased;overflow-x:hidden}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{animation:none!important;transition:none!important}}
::selection{background:var(--accent);color:#fff}
a{color:inherit;text-decoration:none}
button{font-family:inherit;font-size:inherit;cursor:pointer}
.wrap{max-width:var(--maxw);margin:0 auto;padding:0 20px}
#prog{position:fixed;top:0;left:0;height:2px;width:0;background:var(--accent);z-index:99;transition:width .1s}

/* header */
.hero{padding:56px 0 26px;position:relative}
.hero::after{content:"";position:absolute;inset:0;z-index:-1;
  background:radial-gradient(700px 300px at 10% -14%, color-mix(in srgb,var(--accent) 7%,transparent), transparent 72%)}
.kicker{font-family:var(--mono);font-size:10.5px;letter-spacing:.26em;text-transform:uppercase;color:var(--fg3);
  display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.kicker .dot{width:5px;height:5px;border-radius:50%;background:var(--accent)}
h1{font-family:var(--serif);font-weight:600;font-size:clamp(38px,9vw,60px);line-height:1.02;letter-spacing:-.02em;margin:16px 0 4px}
h1 .num{font-family:var(--mono);font-size:.3em;letter-spacing:.1em;color:var(--fg3);vertical-align:super;margin-left:8px;font-weight:400}
.meta-line{display:flex;gap:9px;flex-wrap:wrap;align-items:center;color:var(--fg3);font-size:12.5px;margin-top:12px}
.sep{width:3px;height:3px;border-radius:50%;background:var(--fg3);opacity:.55}
.theme{font-family:var(--mono);font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);margin:22px 0 8px}
.opening{font-family:var(--serif);font-size:clamp(16.5px,2.3vw,18.5px);line-height:1.95;color:var(--fg2);
  margin:24px 0 0;padding-left:16px;border-left:2px solid var(--accent)}
.chip{display:inline-flex;align-items:center;gap:5px;font-family:var(--mono);font-size:10px;letter-spacing:.1em;
  text-transform:uppercase;border:1px solid var(--line);border-radius:99px;padding:3px 9px;color:var(--fg3)}

/* toolbar */
.bar{position:sticky;top:0;z-index:40;background:color-mix(in srgb,var(--bg) 88%,transparent);
  backdrop-filter:saturate(160%) blur(14px);-webkit-backdrop-filter:saturate(160%) blur(14px);border-bottom:1px solid var(--line)}
.bar .inner{max-width:var(--maxw);margin:0 auto;padding:9px 20px;display:flex;gap:8px;align-items:center}
.nav{display:flex;gap:4px;overflow-x:auto;scrollbar-width:none;flex:1;
  -webkit-mask-image:linear-gradient(90deg,#000 0,#000 92%,transparent 100%);
  mask-image:linear-gradient(90deg,#000 0,#000 92%,transparent 100%)}
.nav::-webkit-scrollbar{display:none}
.nav a{flex:0 0 auto;font-size:12.5px;color:var(--fg2);padding:5px 10px;border-radius:99px;border:1px solid transparent;white-space:nowrap}
.nav a:hover{border-color:var(--line);background:var(--card)}
.nav a.on{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.tools{display:flex;gap:6px;flex:0 0 auto}
.icon{width:34px;height:34px;border-radius:50%;border:1px solid var(--line);background:var(--card);color:var(--fg2);
  display:grid;place-items:center;font-size:14px;transition:.15s}
.icon:hover{color:var(--accent);border-color:var(--accent)}
.icon.act{background:var(--accent);color:#fff;border-color:var(--accent)}
.search-wrap{display:none;padding:0 20px 12px;max-width:var(--maxw);margin:0 auto}
.search-wrap.on{display:block}
.search{width:100%;padding:10px 14px;border:1px solid var(--line);border-radius:10px;background:var(--card);
  color:var(--fg);font-size:14px;outline:none}
.search:focus{border-color:var(--accent)}

/* top5 */
.top5{padding:34px 0 6px}
.sec-label{font-family:var(--mono);font-size:10px;letter-spacing:.24em;text-transform:uppercase;color:var(--fg3);
  display:flex;align-items:center;gap:10px;margin:0 0 16px}
.sec-label::after{content:"";flex:1;height:1px;background:var(--line)}
.t5{display:flex;flex-direction:column;gap:0}
.t5 a{display:grid;grid-template-columns:44px 1fr;gap:12px;padding:15px 0;border-bottom:1px solid var(--line);align-items:start}
.t5 a:last-child{border-bottom:none}
.t5 .n{font-family:var(--mono);font-size:11px;color:var(--accent);letter-spacing:.1em;padding-top:5px}
.t5 h3{margin:0;font-family:var(--serif);font-size:19px;line-height:1.5;font-weight:600}
.t5 p{margin:3px 0 0;font-size:13px;color:var(--fg3)}
.t5 a:hover h3{color:var(--accent)}

/* section */
section.sec{padding:44px 0 4px}
.sec-head{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:2px}
.sec-idx{font-family:var(--mono);font-size:11px;color:var(--fg3);letter-spacing:.16em}
.sec-head h2{font-family:var(--serif);font-size:clamp(24px,5vw,31px);margin:0;font-weight:600;letter-spacing:-.01em}
.sec-head em{font-style:normal;font-size:10.5px;letter-spacing:.26em;color:var(--fg3);font-family:var(--mono)}
.blurb{color:var(--fg3);font-size:12.5px;margin:2px 0 18px}
.sbar{height:2px;background:linear-gradient(90deg,var(--accent),transparent);opacity:.45;border-radius:2px;margin-bottom:22px}

/* item */
article.it{padding:0 0 26px;margin:0 0 26px;border-bottom:1px solid var(--line);position:relative}
article.it:last-child{border-bottom:none;margin-bottom:0}
.it .top{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:7px;
  font-family:var(--mono);font-size:10.5px;color:var(--fg3);letter-spacing:.05em}
.it .top .imp{color:var(--accent)}
.it h3{font-family:var(--serif);font-size:clamp(19px,3.8vw,22px);line-height:1.45;margin:0 0 10px;font-weight:600}
.it .sum{margin:0 0 12px;font-size:15.5px;line-height:1.9;color:var(--fg)}
.it .sum::first-letter{font-weight:600}
.it .why{margin:0 0 12px;font-size:13.5px;color:var(--fg2);padding:9px 12px;border-left:2px solid var(--accent);
  background:color-mix(in srgb,var(--accent) 6%,transparent);border-radius:0 6px 6px 0}
.it .why b{font-family:var(--mono);font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin-right:7px}
.kw{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 12px}
.kw span{font-size:11px;color:var(--fg3);border:1px solid var(--line);border-radius:4px;padding:1px 7px}

/* observer */
.obs{margin:4px 0 14px;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--bg2)}
.obs-h{display:flex;align-items:center;gap:8px;padding:10px 14px;font-size:12.5px;color:var(--fg2)}
.obs-h b{font-family:var(--mono);font-size:9.5px;letter-spacing:.18em;text-transform:uppercase;color:var(--accent)}
.obs-h .sp{flex:1}
.obs-h button{border:none;background:none;color:var(--fg3);font-size:12px;padding:2px 4px}
.obs-h button:hover{color:var(--accent)}
.obs-b{display:none;padding:0 14px 14px;font-size:14.5px;line-height:1.9;color:var(--fg2)}
.obs.open .obs-b{display:block}
.obs-b .part{margin:0 0 12px}
.obs-b .part:last-child{margin-bottom:0}
.obs-b .part h4{font-family:var(--mono);font-size:9.5px;letter-spacing:.18em;text-transform:uppercase;color:var(--accent);margin:0 0 4px}
.obs-b .part p{margin:0}
.obs-b ol{margin:0;padding-left:18px}
.obs-b ol li{margin-bottom:4px}
.obs-pre{padding:0 14px 12px;font-size:13px;color:var(--fg3);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.obs.open .obs-pre{display:none}
.askbox{display:none;padding:0 14px 14px}
.askbox.on{display:block}
.askbox textarea{width:100%;min-height:64px;padding:9px 11px;border:1px solid var(--line);border-radius:8px;
  background:var(--card);color:var(--fg);font-family:inherit;font-size:13.5px;resize:vertical;outline:none}
.askbox .row{display:flex;gap:8px;justify-content:flex-end;margin-top:8px}
.askbox button{padding:6px 14px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--fg2);font-size:13px}
.askbox button.pri{background:var(--accent);color:#fff;border-color:var(--accent)}
.answer{margin-top:10px;font-size:14px;line-height:1.85;color:var(--fg2);white-space:pre-wrap}

/* actions */
.acts{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.act{display:inline-flex;align-items:center;gap:5px;padding:4px 10px;border:1px solid var(--line);border-radius:99px;
  background:var(--card);color:var(--fg3);font-size:12px;transition:.15s}
.act:hover{color:var(--accent);border-color:var(--accent)}
.act.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.act.src{margin-left:auto}

/* deep dive */
.deep{margin-top:52px;padding:34px 0 0;border-top:2px solid var(--fg)}
.deep .q{font-family:var(--serif);font-size:clamp(24px,5vw,32px);line-height:1.35;margin:8px 0 14px;font-weight:600}
.deep .lead{font-size:15.5px;line-height:1.95;color:var(--fg2);margin:0 0 24px}
.dblock{margin:0 0 26px}
.dblock h4{font-family:var(--mono);font-size:10px;letter-spacing:.2em;text-transform:uppercase;color:var(--fg3);margin:0 0 10px}
.dblock p{margin:0;font-size:15px;line-height:1.95;color:var(--fg2)}
.tl{list-style:none;margin:0;padding:0;border-left:1px solid var(--line)}
.tl li{position:relative;padding:0 0 14px 18px}
.tl li::before{content:"";position:absolute;left:-3.5px;top:8px;width:6px;height:6px;border-radius:50%;background:var(--accent)}
.tl .w{font-family:var(--mono);font-size:10.5px;color:var(--accent);letter-spacing:.08em;display:block}
.tl .t{font-size:14.5px;color:var(--fg2)}
.tn{list-style:none;margin:0;padding:0}
.tn li{padding:9px 0;border-bottom:1px dashed var(--line);font-size:14.5px;color:var(--fg2)}
.tn li:last-child{border:none}
.tn li b{color:var(--fg);font-weight:600;margin-right:6px}
.vw{display:grid;gap:10px}
.vw div{padding:10px 12px;border-radius:8px;background:var(--bg2);font-size:14px;line-height:1.8;color:var(--fg2)}
.vw div b{color:var(--fg);display:block;font-size:12.5px;margin-bottom:2px}
.rd{list-style:none;margin:0;padding:0}
.rd li{padding:7px 0;font-size:14px;color:var(--fg2);border-bottom:1px dashed var(--line)}
.rd li:last-child{border:none}
.rd b{color:var(--fg);font-weight:600}

/* footer */
footer{margin-top:64px;border-top:1px solid var(--line);padding:26px 0 70px;color:var(--fg3);font-size:12px}
footer .grid{display:grid;grid-template-columns:1fr 1fr;gap:26px}
footer h6{font-family:var(--mono);font-size:9.5px;letter-spacing:.2em;text-transform:uppercase;margin:0 0 8px;color:var(--fg3)}
footer ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:3px}
footer li{display:flex;justify-content:space-between;gap:8px}
.ok{color:#2a9d8f}.bad{color:#c1443c}
.foot-btns{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.foot-btns button{font-size:11.5px;padding:4px 10px;border-radius:99px;border:1px solid var(--line);background:var(--card);color:var(--fg2)}
.foot-btns button:hover{border-color:var(--accent);color:var(--accent)}

/* empty / filter states */
.none{display:none}
body.fav-only .it:not(.fav){display:none}
body.fav-only .sec{display:none}
body.fav-only .sec.has-fav{display:block}
body.fav-only .top5{display:none}
body.fav-only .deep{display:none}
.noresult{padding:40px 0;color:var(--fg3);font-size:14px;display:none}
body.searching .noresult.show{display:block}

@media (max-width:560px){
  .hero{padding:40px 0 20px}
  section.sec{padding:34px 0 2px}
  .t5 a{grid-template-columns:34px 1fr;gap:9px}
  footer .grid{grid-template-columns:1fr}
  .bar .inner{padding:8px 14px}
  .search-wrap{padding:0 14px 10px}
  .wrap{padding:0 16px}
}
"""

JS = r"""
(function(){
  var root=document.documentElement;
  var saved=localStorage.getItem('wb-theme');
  root.dataset.theme = saved || (matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');

  var $=function(s,c){return (c||document).querySelector(s)};
  var $$=function(s,c){return [].slice.call((c||document).querySelectorAll(s))};

  // 主题
  var tb=$('#theme');
  function paintTheme(){ if(tb) tb.textContent = root.dataset.theme==='dark'?'☀':'☾'; }
  if(tb){ tb.addEventListener('click',function(){
    var n = root.dataset.theme==='dark'?'light':'dark';
    root.dataset.theme=n; localStorage.setItem('wb-theme',n); paintTheme();
  });}
  paintTheme();

  // 进度 + 导航高亮
  var prog=$('#prog');
  function onScroll(){
    var h=document.documentElement;
    if(prog) prog.style.width=(h.scrollTop/(h.scrollHeight-h.clientHeight)*100)+'%';
  }
  addEventListener('scroll',onScroll,{passive:true}); onScroll();
  var links=$$('.nav a'), secs=links.map(function(a){return $(a.getAttribute('href'))});
  if('IntersectionObserver' in window){
    var io=new IntersectionObserver(function(es){
      es.forEach(function(e){ if(e.isIntersecting){
        var i=secs.indexOf(e.target);
        links.forEach(function(l,j){l.classList.toggle('on',j===i)});
      }});
    },{rootMargin:'-42% 0px -52% 0px'});
    secs.forEach(function(s){ if(s) io.observe(s); });
  }

  // 存储
  function load(k,d){ try{ return JSON.parse(localStorage.getItem(k)) || d; }catch(e){ return d; } }
  function save(k,v){ localStorage.setItem(k, JSON.stringify(v)); }
  var favs=load('wb-favs',{});
  var fb=load('wb-feedback',{});
  var watch=load('wb-watch',[]);

  function syncFav(){
    $$('.it').forEach(function(el){ el.classList.toggle('fav', !!favs[el.dataset.id]); });
    $$('.act[data-act="fav"]').forEach(function(b){ b.classList.toggle('on', !!favs[b.dataset.id]); });
    $$('.sec').forEach(function(sec){ sec.classList.toggle('has-fav', $$('.it.fav',sec).length>0); });
  }
  function syncFb(){
    $$('.act[data-act="like"],.act[data-act="dislike"]').forEach(function(b){
      var v=fb[b.dataset.id]; b.classList.toggle('on', v===b.dataset.act);
    });
  }

  // 收藏 / 反馈
  document.addEventListener('click',function(e){
    var b=e.target.closest('[data-act]'); if(!b) return;
    var id=b.dataset.id, act=b.dataset.act;
    if(act==='fav'){ favs[id]=!favs[id]; save('wb-favs',favs); syncFav(); }
    if(act==='like'||act==='dislike'){ fb[id] = fb[id]===act?null:act; save('wb-feedback',fb); syncFb(); }
    if(act==='watch'){ 
      var t=b.dataset.topic||'';
      if(t && watch.indexOf(t)<0){ watch.push(t); save('wb-watch',watch); b.classList.add('on'); b.textContent='已加入观察'; }
    }
    if(act==='obs'){ var box=b.closest('.obs'); box.classList.toggle('open');
      b.textContent = box.classList.contains('open')?'收起':'展开'; }
    if(act==='ask'){ var ab=b.closest('.obs').querySelector('.askbox'); ab.classList.toggle('on');
      var ta=ab.querySelector('textarea'); if(ta) ta.focus(); }
  });

  // 只看收藏
  var favBtn=$('#favfilter');
  if(favBtn) favBtn.addEventListener('click',function(){
    document.body.classList.toggle('fav-only');
    favBtn.classList.toggle('act', document.body.classList.contains('fav-only'));
    syncFav();
  });

  // 搜索
  var sBtn=$('#sbtn'), sWrap=$('#searchwrap'), sInput=$('#search');
  if(sBtn) sBtn.addEventListener('click',function(){
    sWrap.classList.toggle('on'); if(sWrap.classList.contains('on')) sInput.focus(); else clearSearch();
  });
  function clearSearch(){
    document.body.classList.remove('searching');
    $$('.it').forEach(function(el){el.classList.remove('none')});
    $$('section.sec').forEach(function(s){s.classList.remove('none')});
    if(sInput) sInput.value='';
  }
  function runSearch(){
    var q=(sInput.value||'').trim().toLowerCase();
    if(!q){ clearSearch(); return; }
    document.body.classList.add('searching');
    var any=false;
    $$('.it').forEach(function(el){
      var hit=(el.dataset.text||'').indexOf(q)>=0;
      el.classList.toggle('none',!hit); if(hit) any=true;
    });
    $$('section.sec').forEach(function(s){
      s.classList.toggle('none', $$('.it:not(.none)',s).length===0);
    });
    var nr=$('#noresult'); if(nr) nr.classList.toggle('show',!any);
  }
  if(sInput){ sInput.addEventListener('input',runSearch); }

  // 追问
  document.addEventListener('submit',function(e){
    if(!e.target.matches('.askform')) return;
    e.preventDefault();
    var form=e.target, box=form.closest('.askbox'), out=box.querySelector('.answer');
    var q=form.querySelector('textarea').value.trim(); if(!q) return;
    out.textContent='思考中…';
    fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({issue:window.WB_ISSUE||'', id:box.dataset.id, headline:box.dataset.headline,
        summary:box.dataset.summary, question:q})})
      .then(function(r){ return r.json(); })
      .then(function(d){ out.textContent = d.answer || d.error || '没有返回内容'; })
      .catch(function(){ out.textContent='追问需要本地服务：在项目目录运行 python3 serve.py 后打开 http://127.0.0.1:8000'; });
  });

  // 导出反馈
  var exp=$('#export');
  if(exp) exp.addEventListener('click',function(){
    var data={favorites:Object.keys(favs).filter(function(k){return favs[k]}),
              feedback:fb, watch:watch, exported_at:new Date().toISOString()};
    var blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
    var a=document.createElement('a');
    a.href=URL.createObjectURL(blob); a.download='wb-profile.json'; a.click();
  });

  // 回到顶部
  var top=$('#top');
  if(top) top.addEventListener('click',function(){scrollTo({top:0,behavior:'smooth'})});

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
<meta name="theme-color" content="#fbfaf7">
<meta property="og:title" content="__TITLE__">
<meta property="og:description" content="__DESC__">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%2314161a'/><text x='50' y='66' font-size='46' text-anchor='middle' fill='%23fff' font-family='monospace'>W</text></svg>">
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


def esc(s: str) -> str:
    return ht.escape(str(s or ""), quote=True)


def _item_text(item: dict, section: dict) -> str:
    parts = [
        item.get("headline", ""),
        item.get("summary", ""),
        item.get("why", ""),
        " ".join(item.get("keywords") or []),
        item.get("source", ""),
        section.get("name", ""),
        item.get("take", {}).get("text", ""),
        item.get("take", {}).get("background", ""),
    ]
    return esc(" ".join(parts).lower())


def _obs_html(item: dict) -> str:
    take = item.get("take") or {}
    if not take:
        return ""
    if take.get("mode") == "full":
        qs = "".join(f"<li>{esc(q)}</li>" for q in take.get("questions") or [])
        body = (
            f'<div class="part"><h4>事件背后</h4><p>{esc(take.get("background",""))}</p></div>'
            f'<div class="part"><h4>深层影响</h4><p>{esc(take.get("impact",""))}</p></div>'
            f'<div class="part"><h4>不同视角</h4><p>{esc(take.get("perspectives",""))}</p></div>'
            + (f'<div class="part"><h4>值得思考</h4><ol>{qs}</ol></div>' if qs else "")
        )
        preview = esc((take.get("background", "") or "")[:80]) + "…"
    else:
        text = take.get("text", "")
        if not text:
            return ""
        body = f'<div class="part"><p>{esc(text)}</p></div>'
        preview = esc(text[:90]) + "…"
    item_id = esc(item.get("id", ""))
    return f"""<div class="obs">
  <div class="obs-h"><b>观察者视角</b><span class="sp"></span>
    <button data-act="ask" data-id="{item_id}">追问</button>
    <button data-act="obs" data-id="{item_id}">展开</button>
  </div>
  <div class="obs-pre">{preview}</div>
  <div class="obs-b">{body}</div>
  <div class="askbox" data-id="{item_id}" data-headline="{esc(item.get('headline',''))}" data-summary="{esc(item.get('summary','')[:300])}">
    <form class="askform"><textarea placeholder="就这条新闻继续追问，比如：这个判断有哪些反例？"></textarea>
    <div class="row"><button type="submit" class="pri">提问</button></div></form>
    <div class="answer"></div>
  </div>
</div>"""


def _item_html(item: dict, section: dict) -> str:
    imp = int(item.get("importance") or 1)
    stars = {3: "重点", 2: "关注", 1: "速览"}.get(imp, "速览")
    src_all = [s for s in (item.get("sources_all") or []) if s and s != item.get("source")]
    cross = f'<span>+{len(src_all)} 家报道</span><span class="sep"></span>' if src_all else ""
    kws = "".join(f"<span>{esc(k)}</span>" for k in item.get("keywords") or [])
    if item.get("watch"):
        kws += "".join(f'<span style="color:var(--accent);border-color:var(--accent)">你在观察：{esc(w)}</span>' for w in item["watch"])
    why = f'<p class="why"><b>为什么重要</b>{esc(item.get("why",""))}</p>' if item.get("why") else ""
    topic = esc((item.get("keywords") or [""])[0] or section.get("name", ""))
    return f"""<article class="it" id="i-{esc(item.get('id',''))}" data-id="{esc(item.get('id',''))}"
  data-text="{_item_text(item, section)}">
  <div class="top"><span class="imp">{stars}</span><span class="sep"></span>
    <span>{esc(item.get('source',''))}</span><span class="sep"></span>
    <span>{esc(item.get('date_pub',''))}</span>{cross}
    {f'<span class="sep"></span><span>事件 {esc(item["event_date"])}</span>' if item.get('event_date') else ''}
  </div>
  <h3>{esc(item.get('headline',''))}</h3>
  <p class="sum">{esc(item.get('summary',''))}</p>
  {why}
  {f'<div class="kw">{kws}</div>' if kws else ''}
  {_obs_html(item)}
  <div class="acts">
    <button class="act" data-act="fav" data-id="{esc(item.get('id',''))}">☆ 收藏</button>
    <button class="act" data-act="like" data-id="{esc(item.get('id',''))}">感兴趣</button>
    <button class="act" data-act="dislike" data-id="{esc(item.get('id',''))}">不感兴趣</button>
    <button class="act" data-act="watch" data-topic="{topic}" data-id="{esc(item.get('id',''))}">加入观察</button>
    <a class="act src" href="{esc(item.get('url',''))}" target="_blank" rel="noopener">原文 ↗</a>
  </div>
</article>"""


def _section_html(sec: dict) -> str:
    items = "".join(_item_html(it, sec) for it in sec["items"])
    return f"""<section class="sec" id="{esc(sec['key'])}" style="--accent:{esc(sec.get('accent','#3d5a80'))}">
  <div class="sec-head"><span class="sec-idx">{esc(sec.get('idx',''))}</span>
    <h2>{esc(sec['name'])}</h2><em>{esc(sec.get('en',''))}</em></div>
  <p class="blurb">{esc(sec.get('blurb',''))}</p>
  <div class="sbar"></div>
  {items}
</section>"""


def _top5_html(items: list[dict], sections: list[dict]) -> str:
    sec_map = {s["key"]: s for s in sections}
    rows = []
    for i, it in enumerate(items[:5], 1):
        sec = sec_map.get(it["section"], {})
        rows.append(
            f'<a href="#i-{esc(it["id"])}"><span class="n">{i:02d}</span>'
            f'<span><h3>{esc(it["headline"])}</h3><p>{esc(sec.get("name",""))} · {esc(it.get("source",""))}</p></span></a>'
        )
    return f'<div class="top5"><div class="sec-label">本周最重要</div><div class="t5">{"".join(rows)}</div></div>'


def _deep_html(dd: dict) -> str:
    if not dd or not dd.get("question"):
        return ""
    timeline = "".join(
        f'<li><span class="w">{esc(t.get("when",""))}</span><span class="t">{esc(t.get("what",""))}</span></li>'
        for t in dd.get("timeline") or []
    )
    tensions = "".join(f"<li>{esc(t)}</li>" for t in dd.get("tensions") or [])
    views = "".join(
        f'<div><b>{esc(v.get("stance",""))}</b>{esc(v.get("claim",""))}</div>' for v in dd.get("views") or []
    )
    reading = "".join(
        f'<li><b>{esc(r.get("title",""))}</b>　{esc(r.get("author",""))}——{esc(r.get("why",""))}</li>'
        for r in dd.get("reading") or []
    )
    blocks = []
    if dd.get("background"):
        blocks.append(f'<div class="dblock"><h4>背景脉络</h4><p>{esc(dd["background"])}</p></div>')
    if timeline:
        blocks.append(f'<div class="dblock"><h4>时间线</h4><ul class="tl">{timeline}</ul></div>')
    if tensions:
        blocks.append(f'<div class="dblock"><h4>核心矛盾</h4><ul class="tn">{tensions}</ul></div>')
    if views:
        blocks.append(f'<div class="dblock"><h4>不同立场</h4><div class="vw">{views}</div></div>')
    if reading:
        blocks.append(
            '<div class="dblock"><h4>延伸阅读</h4><ul class="rd">' + reading + "</ul>"
            '<p style="margin-top:6px;font-size:11.5px;color:var(--fg3)">'
            "书目由模型推荐，请自行核实版本与出处。</p></div>"
        )
    return f"""<section class="deep" id="deep">
  <div class="sec-label">08｜本周深度观察</div>
  <h2 class="q">{esc(dd["question"])}</h2>
  <p class="lead">{esc(dd.get("lead",""))}</p>
  {"".join(blocks)}
</section>"""


def _footer_html(issue: dict) -> str:
    st = issue.get("stats", {})
    usage = st.get("usage") or {}
    rows = "".join(
        f'<li><span>{esc(s["name"])}</span><span class="{"ok" if s["ok"] else "bad"}">'
        f'{"✓ " + str(s["count"]) if s["ok"] else "×"}</span></li>'
        for s in issue.get("sources", [])[:20]
    )
    tokens = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
    return f"""<footer><div class="wrap"><div class="grid">
  <div><h6>数据来源 · {st.get('sources_ok',0)}/{st.get('sources_total',0)} 正常</h6><ul>{rows}</ul></div>
  <div>
    <h6>关于本期</h6>
    <ul>
      <li><span>生成时间</span><span>{esc(issue.get('generated_date',''))} {esc(issue.get('generated_at','')[11:16])}</span></li>
      <li><span>条目</span><span>{st.get('items',0)} 条</span></li>
      <li><span>处理文章</span><span>{st.get('articles',0)} 篇</span></li>
      <li><span>模型消耗</span><span>{tokens/1000:.0f}k tokens / {usage.get('calls',0)} 次</span></li>
      <li><span>国际源</span><span>{'已启用' if st.get('intl') else '未启用（无代理）'}</span></li>
    </ul>
    <h6 style="margin-top:16px">更多</h6>
    <ul class="foot-btns">
      <li><a href="__ARCHIVE__">往期</a></li>
      <li><a href="__THINKING__">思想档案</a></li>
      <li><button id="export">导出阅读数据</button></li>
    </ul>
  </div>
</div></div></footer>"""


def render_issue(issue: dict, cfg: dict) -> str:
    sections = issue["sections"]
    sec_map = {s["key"]: s for s in sections}
    top_items = [it for s in sections for it in s["items"] if it["id"] in set(issue.get("top_ids") or [])]
    if len(top_items) < 5:
        top_items = [it for s in sections for it in s["items"]][:5]

    nav = "".join(
        f'<a href="#{esc(s["key"])}">{esc(s.get("idx",""))} {esc(s["name"])}</a>' for s in sections
    ) + ('<a href="#deep">08 深度观察</a>' if issue.get("deep_dive") else "")

    body_sections = "".join(_section_html(s) for s in sections)
    hero = f"""<header class="hero"><div class="wrap">
  <div class="kicker"><span class="dot"></span>WEEKLY BRIEF<span class="sep"></span>{esc(issue['week'])}</div>
  <h1>{esc(cfg.get('title','WEEKLY BRIEF'))}<span class="num">{esc(issue['week'].split('W')[-1])}</span></h1>
  <div class="meta-line"><span>{esc(issue['range'])}</span><span class="sep"></span>
    <span>{sum(len(s['items']) for s in sections)} 条精选</span><span class="sep"></span>
    <span>{'AI 观察者评论' if issue.get('mode')=='llm' else '规则摘要'}</span>
  </div>
  {f'<div class="theme">{esc(issue["note"])}</div>' if issue.get("note") else ''}
  {f'<p class="opening">{esc(issue["opening"])}</p>' if issue.get("opening") else ''}
</div></header>"""

    search = """<div class="search-wrap" id="searchwrap">
  <input id="search" class="search" type="search" placeholder="搜索标题、摘要、关键词…">
</div>"""

    bar = f"""<div class="bar"><div class="inner">
  <div class="nav">{nav}</div>
  <div class="tools">
    <button class="icon" id="sbtn" aria-label="搜索">⌕</button>
    <button class="icon" id="favfilter" aria-label="只看收藏">☆</button>
    <button class="icon" id="theme" aria-label="主题">☾</button>
  </div>
</div>{search}</div>"""

    main = (
        hero + bar
        + f'<main class="wrap">{_top5_html(top_items, sections)}'
        + body_sections
        + _deep_html(issue.get("deep_dive") or {})
        + '<div class="noresult" id="noresult">没有匹配的新闻，换个关键词试试。</div>'
        + "</main>"
        + _footer_html(issue)
    )

    archive = "../archive.html" if issue.get("_in_issues_dir") else "archive.html"
    thinking = "../thinking.html" if issue.get("_in_issues_dir") else "thinking.html"
    main = main.replace("__ARCHIVE__", archive).replace("__THINKING__", thinking)

    return (
        TEMPLATE.replace("__CSS__", CSS)
        .replace("__JS__", JS)
        .replace("__BODY__", main)
        .replace("__WEEK__", issue["week"])
        .replace("__TITLE__", f"{cfg.get('title','WEEKLY BRIEF')} · {issue['week']} 周报")
        .replace("__DESC__", esc((issue.get("opening") or issue["range"])[:120]))
    )


def render_archive(index: dict) -> str:
    rows = "".join(
        f'<a class="row" href="issues/{esc(i["week"])}.html"><span class="wk">{esc(i["week"])}</span>'
        f'<span class="rg">{esc(i["range"])}　{esc(i.get("note",""))}</span><span class="ct">{i.get("items",0)} 条</span></a>'
        for i in index.get("issues", [])
    )
    body = f"""<header class="hero"><div class="wrap">
  <div class="kicker"><span class="dot"></span>ARCHIVE</div>
  <h1>往期<span class="num">{len(index.get('issues', []))}</span></h1>
  <p class="opening">每周一期，按 ISO 周编号排列。可在下面检索全部历史新闻。</p>
</div></header>
<div class="bar"><div class="inner"><div class="nav"><a href="index.html">最新一期</a><a href="thinking.html">思想档案</a></div></div></div>
<main class="wrap" style="padding-top:26px">
  <input id="q" class="search" placeholder="在全部历史新闻里搜索…">
  <div id="hits" style="margin-top:18px"></div>
  <div class="t5" style="margin-top:26px">{rows}</div>
</main>"""
    extra = """
ul.arch{list-style:none;padding:0}
.t5 a.row{display:grid;grid-template-columns:88px 1fr auto;gap:10px}
.hit{padding:12px 0;border-bottom:1px solid var(--line)}
.hit b{font-size:15px}
.hit span{display:block;font-size:12px;color:var(--fg3);margin-top:2px}
"""
    script = """
(function(){
  var data=null;
  fetch('data/index.json').then(function(r){return r.json()}).then(function(d){data=d}).catch(function(){});
  var q=document.getElementById('q'), hits=document.getElementById('hits');
  q.addEventListener('input',function(){
    var v=q.value.trim().toLowerCase(); if(!data) return;
    if(!v){hits.innerHTML='';return;}
    var rows=data.items.filter(function(it){
      return (it.h+' '+it.d+' '+it.k).toLowerCase().indexOf(v)>=0;
    }).slice(0,40);
    hits.innerHTML = rows.map(function(it){
      return '<div class="hit"><a href="issues/'+it.w+'.html#'+'i-'+it.i+'"><b>'+it.h+'</b></a>'+
        '<span>'+it.w+' · '+it.s+'</span></div>';
    }).join('') || '<p style="color:var(--fg3)">没有找到。</p>';
  });
})();
"""
    return (
        TEMPLATE.replace("__CSS__", CSS + extra)
        .replace("__JS__", JS + script)
        .replace("__BODY__", body)
        .replace("__WEEK__", "")
        .replace("__TITLE__", "往期 · WEEKLY BRIEF")
        .replace("__DESC__", "往期周报与历史新闻检索")
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


def render_thinking(index: dict, issues: list[dict]) -> str:
    qs = []
    for d in issues:
        wk = d.get("week", "")
        for q in d.get("questions3") or []:
            qs.append(f'<li><span class="w">{esc(wk)}</span><span>{esc(q)}</span></li>')
    body = f"""<header class="hero"><div class="wrap">
  <div class="kicker"><span class="dot"></span>THINKING ARCHIVE</div>
  <h1>思想档案<span class="num">{len(qs)}</span></h1>
  <p class="opening">每周三个值得长期思考的问题，积累成一条自己的思考线索。</p>
</div></header>
<div class="bar"><div class="inner"><div class="nav"><a href="index.html">最新一期</a><a href="archive.html">往期</a></div></div></div>
<main class="wrap" style="padding-top:26px">
  <div class="sec-label">长期问题</div>
  <ul class="tl" style="margin-top:14px">{''.join(qs) or '<li>还没有积累。</li>'}</ul>
  <div class="sec-label" style="margin-top:34px">我的观察清单</div>
  <ul class="tl" id="watchlist" style="margin-top:14px"></ul>
</main>""" + WATCH_SCRIPT
    return (
        TEMPLATE.replace("__CSS__", CSS)
        .replace("__JS__", JS)
        .replace("__BODY__", body)
        .replace("__WEEK__", "")
        .replace("__TITLE__", "思想档案 · WEEKLY BRIEF")
        .replace("__DESC__", "每周三个值得长期思考的问题")
    )


def write_site(issue: dict, cfg: dict) -> str:
    out = os.path.join(ROOT, cfg.get("output", {}).get("dir", "site"))
    os.makedirs(os.path.join(out, "issues"), exist_ok=True)
    os.makedirs(os.path.join(out, "data"), exist_ok=True)

    # 归档索引
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
        issues_meta.append(
            {
                "week": d.get("week", name[:-5]),
                "range": d.get("range", ""),
                "note": d.get("note", ""),
                "items": sum(len(s["items"]) for s in d.get("sections", [])),
            }
        )
        all_raw.append(d)
    index = {"issues": issues_meta}

    week_html = render_issue({**issue, "_in_issues_dir": True}, cfg)
    path = os.path.join(out, "issues", f"{issue['week']}.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(week_html)

    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(render_issue({**issue, "_in_issues_dir": False}, cfg))

    with open(os.path.join(out, "archive.html"), "w", encoding="utf-8") as fh:
        fh.write(render_archive(index))

    with open(os.path.join(out, "thinking.html"), "w", encoding="utf-8") as fh:
        fh.write(render_thinking(index, all_raw))
    return path
