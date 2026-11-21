"""渲染 v4：手机优先的单列阅读页——没有图片、没有卡片，只有文字。"""
from __future__ import annotations

import html as ht
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CSS = r"""
*,*::before,*::after{box-sizing:border-box}
:root{
  --paper:#efe7d5; --paper2:#e7dcc4; --ink:#17120c; --ink2:#463c31; --ink3:#8b7f6d;
  --rule:rgba(23,18,12,.16); --rule2:rgba(23,18,12,.52); --accent:#a63325;
  --serif:"Songti SC","Noto Serif SC",ui-serif,Georgia,"Times New Roman",serif;
  --sans:-apple-system,BlinkMacSystemFont,"PingFang SC","Segoe UI",Roboto,sans-serif;
  --disp:"HelveticaNeue-CondensedBold","Helvetica Neue Condensed Bold","Arial Narrow","PingFang SC",Impact,sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
  --w:680px;
}
html[data-theme="dark"]{
  --paper:#141110; --paper2:#1d1916; --ink:#efe6d3; --ink2:#bdb2a0; --ink3:#7f7567;
  --rule:rgba(239,230,211,.17); --rule2:rgba(239,230,211,.46); --accent:#dc6d56;
}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--serif);
  font-size:16.5px;line-height:1.95;-webkit-font-smoothing:antialiased;
  background-image:radial-gradient(rgba(23,18,12,.05) .6px,transparent .7px);
  background-size:4px 4px}
html[data-theme="dark"] body{background-image:radial-gradient(rgba(255,255,255,.035) .6px,transparent .7px)}
body::after{content:"";position:fixed;inset:11px;border:1px solid var(--rule);pointer-events:none;z-index:80}
a{color:inherit;text-decoration:none}
button{font-family:inherit;font-size:inherit;cursor:pointer;background:none;border:none;color:inherit}
::selection{background:var(--accent);color:var(--paper)}
.wrap{max-width:var(--w);margin:0 auto;padding:0 22px}

/* 刊头 */
header.mast{padding-top:20px}
.mast-top{display:flex;justify-content:space-between;align-items:baseline;gap:12px;
  padding-bottom:9px;border-bottom:1px solid var(--rule2)}
.brand{font-family:var(--disp);font-size:13px;letter-spacing:.16em;text-transform:uppercase}
.brand:before{content:"";display:inline-block;width:7px;height:7px;background:var(--accent);margin-right:9px;vertical-align:1px}
.issue{font-family:var(--mono);font-size:9.5px;letter-spacing:.2em;color:var(--ink3);text-transform:uppercase}
.title-block{text-align:center;padding:24px 0 6px}
h1.mast-title{font-family:var(--disp);font-weight:700;margin:0;line-height:.88;
  font-size:clamp(38px,12.5vw,62px);letter-spacing:-.015em;text-transform:uppercase}
.mast-sub{font-family:var(--mono);font-size:9.5px;letter-spacing:.34em;color:var(--ink3);
  text-transform:uppercase;margin-top:14px}
.dateline{display:flex;align-items:center;gap:12px;margin-top:14px;
  font-family:var(--mono);font-size:10px;letter-spacing:.2em;color:var(--ink2)}
.dateline:before,.dateline:after{content:"";flex:1;height:1px;background:var(--rule2)}

/* 索引条 */
nav.ticker{display:flex;overflow-x:auto;margin-top:18px;border-top:1px solid var(--rule2);
  -webkit-mask-image:linear-gradient(90deg,#000 86%,transparent);mask-image:linear-gradient(90deg,#000 86%,transparent);
  border-bottom:1px solid var(--rule2);background:var(--paper2);
  scrollbar-width:none;-webkit-overflow-scrolling:touch}
nav.ticker::-webkit-scrollbar{display:none}
nav.ticker a{flex:0 0 auto;font-family:var(--sans);font-size:11.5px;letter-spacing:.1em;
  padding:10px 15px;color:var(--ink2);border-right:1px solid var(--rule);white-space:nowrap}
nav.ticker a:first-child{padding-left:0;margin-left:22px;border-right:none}
nav.ticker a:first-child:before{content:"—";margin-right:10px;color:var(--accent)}
nav.ticker a:hover{background:var(--ink);color:var(--paper)}

/* 按钮 */
.btn{display:inline-block;font-family:var(--sans);font-size:11px;letter-spacing:.1em;
  border:1px solid var(--rule2);padding:6px 12px;line-height:1.3;color:var(--ink);
  background:transparent;white-space:nowrap}
.btn:hover{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.btn.on{background:var(--accent);border-color:var(--accent);color:#fff}
.tools{display:flex;flex-wrap:wrap;gap:7px;justify-content:flex-end;margin-top:13px}
input.search{width:100%;font-family:var(--mono);font-size:13px;letter-spacing:.05em;
  padding:10px 12px;border:1px solid var(--rule2);background:transparent;color:var(--ink);
  outline:none;margin-top:12px}
input.search:focus{border-color:var(--accent)}

/* 导语 */
.standfirst{margin:30px 0 0;padding:18px 0 20px;border-top:2px solid var(--ink);border-bottom:1px solid var(--rule2)}
.lab{font-family:var(--sans);font-size:9.5px;letter-spacing:.28em;text-transform:uppercase;color:var(--accent)}
.standfirst p{font-family:var(--serif);font-size:18.5px;line-height:1.85;margin:10px 0 0}
.count{font-family:var(--mono);font-size:9.5px;letter-spacing:.18em;color:var(--ink3);
  text-transform:uppercase;margin-top:14px}

/* 栏目 */
section.sec{margin-top:44px}
.sec-head{display:flex;align-items:flex-end;gap:13px;border-top:3px double var(--rule2);padding-top:15px}
.sec-idx{font-family:var(--disp);font-size:36px;line-height:.78;color:var(--accent);letter-spacing:-.02em}
.sec-name{font-family:var(--serif);font-size:25px;font-weight:700;line-height:1.12;letter-spacing:-.01em}
.sec-en{font-family:var(--mono);font-size:9px;letter-spacing:.26em;color:var(--ink3);
  margin-left:auto;padding-bottom:5px}
.sec-blurb{font-family:var(--sans);font-size:12px;color:var(--ink3);margin:7px 0 0;letter-spacing:.02em}

/* 单条报道 */
article.it{margin:0;padding:26px 0 30px;border-bottom:1px solid var(--rule)}
section.sec article.it:first-of-type{padding-top:22px}
article.it h3{font-family:var(--serif);font-size:21px;font-weight:700;line-height:1.42;
  margin:0;letter-spacing:-.012em}
article.it.major h3{font-size:26px;line-height:1.34}
article.it h3 a:hover{color:var(--accent)}
article.it .meta{font-family:var(--mono);font-size:9.5px;letter-spacing:.18em;color:var(--ink3);
  margin-top:10px;text-transform:uppercase}
article.it .lede{font-family:var(--serif);font-size:17.5px;line-height:1.85;margin:15px 0 0}
article.it .body p{font-size:16.5px;line-height:2.02;color:var(--ink2);margin:14px 0 0}
article.it .body h4{font-family:var(--sans);font-size:10px;font-weight:600;letter-spacing:.26em;
  color:var(--accent);margin:26px 0 3px;text-transform:uppercase;display:flex;align-items:center;gap:8px}
article.it .body h4:before{content:"";width:6px;height:6px;background:var(--accent);flex:0 0 auto}
article.it.major .body p{color:var(--ink)}
.tags{display:flex;flex-wrap:wrap;gap:5px;margin-top:18px}
.tags span{font-family:var(--mono);font-size:9.5px;letter-spacing:.06em;border:1px solid var(--rule);
  padding:2px 7px;color:var(--ink3)}
.ops{display:flex;flex-wrap:wrap;gap:7px;margin-top:13px}
.ops button,.ops a{font-family:var(--sans);font-size:10.5px;letter-spacing:.1em;border:1px solid var(--rule);
  padding:5px 11px;color:var(--ink3);line-height:1.45}
.ops button:hover,.ops a:hover{border-color:var(--ink);color:var(--ink)}
.ops button.on{border-color:var(--accent);color:var(--accent)}
.hidden{display:none!important}

/* 深度观察 */
section.deep{margin-top:64px;border-top:3px double var(--rule2);padding-top:20px}
section.deep .kicker{font-family:var(--sans);font-size:9.5px;letter-spacing:.28em;color:var(--accent);text-transform:uppercase}
section.deep h2{font-family:var(--serif);font-size:28px;line-height:1.38;margin:12px 0 0;font-weight:700;letter-spacing:-.015em}
section.deep .lead{font-family:var(--serif);font-size:18px;line-height:1.85;color:var(--ink2);margin:14px 0 0}
section.deep h4{font-family:var(--sans);font-size:9.5px;letter-spacing:.26em;color:var(--accent);
  text-transform:uppercase;margin:30px 0 6px;font-weight:600;display:flex;align-items:center;gap:8px}
section.deep h4:before{content:"";width:6px;height:6px;background:var(--accent)}
section.deep p{font-size:16.5px;line-height:2;color:var(--ink2);margin:0}
section.deep ul{list-style:none;padding:0;margin:0}
section.deep li{font-size:15.5px;line-height:1.85;color:var(--ink2);padding:9px 0;border-bottom:1px solid var(--rule)}
section.deep li:last-child{border-bottom:none}
section.deep li .w{font-family:var(--mono);font-size:9.5px;letter-spacing:.14em;color:var(--ink3);display:block;margin-bottom:1px}
section.deep .vw{padding:11px 0;border-bottom:1px solid var(--rule)}
section.deep .vw:last-child{border-bottom:none}
section.deep .vw b{display:block;font-family:var(--sans);font-size:12.5px;color:var(--ink);margin-bottom:3px;letter-spacing:.02em}

/* 页脚 */
footer{margin-top:60px;border-top:3px double var(--rule2);padding:16px 0 70px;
  font-family:var(--mono);font-size:10px;letter-spacing:.1em;color:var(--ink3);line-height:2.1}
footer a{border-bottom:1px solid var(--rule);margin-right:18px}
footer a:hover{color:var(--ink)}

/* 归档 / 思想档案 */
main.page{padding-top:14px}
h1.title{font-family:var(--serif);font-size:clamp(34px,10vw,52px);font-weight:700;margin:26px 0 6px;
  line-height:1;letter-spacing:.02em}
p.sub{font-family:var(--sans);font-size:12.5px;color:var(--ink3);margin:0 0 18px}
ul.archlist{list-style:none;padding:0;margin:24px 0 0;border-top:1px solid var(--rule2)}
ul.archlist li{border-bottom:1px solid var(--rule)}
ul.archlist a{display:flex;justify-content:space-between;align-items:baseline;gap:14px;padding:14px 0;font-size:15px;line-height:1.7}
ul.archlist a:hover .t{color:var(--accent)}
ul.archlist .w{font-family:var(--mono);font-size:10px;letter-spacing:.14em;color:var(--accent);flex:0 0 auto}
ul.archlist .t{flex:1;color:var(--ink2)}
.hit{padding:13px 0;border-bottom:1px solid var(--rule)}
.hit b{font-size:15.5px;font-weight:700}
.hit span{display:block;font-family:var(--mono);font-size:9.5px;letter-spacing:.14em;color:var(--ink3);margin-top:4px}

@media (max-width:520px){
  body::after{inset:7px}
  .wrap{padding:0 18px}
  nav.ticker a:first-child{margin-left:18px}
  article.it h3{font-size:19.5px}
  article.it.major h3{font-size:23px}
  section.deep h2{font-size:24px}
  .standfirst p{font-size:17px}
  h1.mast-title{font-size:clamp(34px,11.4vw,52px)}
}
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>__TITLE__</title>
<meta name="description" content="__DESC__">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#efe7d5">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' fill='%2317120c'/><text x='50' y='70' font-size='54' text-anchor='middle' fill='%23fff' font-family='serif'>W</text></svg>">
<style>__CSS__</style>
</head>
<body>
__BODY__
<script>window.WB_ISSUE="__WEEK__";</script>
<script>__JS__</script>
</body>
</html>
"""

JS = r"""
(function(){
  var D=document.documentElement;
  try{var t=localStorage.getItem('wb-theme');
    if(t) D.setAttribute('data-theme',t);
    else if(window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches) D.setAttribute('data-theme','dark');
  }catch(e){}
  var tb=document.getElementById('theme');
  if(tb) tb.addEventListener('click',function(){
    var n = D.getAttribute('data-theme')==='dark'?'light':'dark';
    D.setAttribute('data-theme',n);
    try{localStorage.setItem('wb-theme',n);}catch(e){}
  });

  function ls(k,d){try{return JSON.parse(localStorage.getItem(k))||d}catch(e){return d}}
  function save(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
  var favs=ls('wb-fav',[]), likes=ls('wb-like',{});
  function sync(){
    document.querySelectorAll('[data-fav]').forEach(function(b){
      b.classList.toggle('on', favs.indexOf(b.dataset.fav)>=0);
    });
    document.querySelectorAll('[data-fb]').forEach(function(b){
      b.classList.toggle('on', likes[b.dataset.fb]===b.dataset.val);
    });
  }
  document.addEventListener('click',function(e){
    var f=e.target.closest('[data-fav]');
    if(f){ var k=f.dataset.fav, i=favs.indexOf(k);
      if(i>=0) favs.splice(i,1); else favs.push(k);
      save('wb-fav',favs); sync(); return; }
    var b=e.target.closest('[data-fb]');
    if(b){ var k2=b.dataset.fb; likes[k2] = likes[k2]===b.dataset.val ? '' : b.dataset.val;
      save('wb-like',likes); sync(); return; }
  });
  sync();

  var sb=document.getElementById('sbtn'), sw=document.getElementById('searchwrap'), si=document.getElementById('search');
  if(sb) sb.addEventListener('click',function(){
    sw.classList.toggle('hidden'); if(!sw.classList.contains('hidden')) si.focus();
  });
  if(si) si.addEventListener('input',function(){
    var v=si.value.trim().toLowerCase(), any=false;
    document.querySelectorAll('article.it').forEach(function(a){
      var hit = !v || (a.dataset.k||'').toLowerCase().indexOf(v)>=0;
      a.classList.toggle('hidden', v && !hit); if(hit) any=true;
    });
    document.querySelectorAll('section.sec').forEach(function(s){
      var vis=s.querySelectorAll('article.it:not(.hidden)').length;
      s.classList.toggle('hidden', !!v && vis===0);
    });
    var nr=document.getElementById('noresult'); if(nr) nr.classList.toggle('hidden', any || !v);
  });

  var fb=document.getElementById('favfilter');
  if(fb) fb.addEventListener('click',function(){
    var on=document.body.classList.toggle('fav-only');
    document.querySelectorAll('article.it').forEach(function(a){
      a.classList.toggle('hidden', on && favs.indexOf(a.id.slice(2))<0);
    });
    document.querySelectorAll('section.sec').forEach(function(s){
      s.classList.toggle('hidden', on && s.querySelectorAll('article.it:not(.hidden)').length===0);
    });
    fb.classList.toggle('on',on);
  });
})();
"""


def _short(text: str, n: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else text[:n] + "…"


def esc(s) -> str:
    return ht.escape(str(s or ""), quote=True)


def _sources(item: dict) -> str:
    names = [n for n in (item.get("sources_all") or [item.get("source", "")]) if n]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return f"{names[0]} 等 {len(names)} 家"


def _item_html(item: dict) -> str:
    blocks = [b for b in (item.get("blocks") or []) if b.get("p")]
    if not blocks:
        blocks = [{"h": "", "p": item.get("summary", "")}]
    parts = []
    for b in blocks:
        head = (b.get("h") or "").strip()
        if head:
            parts.append(f'<h4>{esc(head)}</h4><p>{esc(b["p"])}</p>')
        else:
            parts.append(f'<p>{esc(b["p"])}</p>')
    body = "".join(parts)
    lede = (item.get("lede") or "").strip()
    tags = "".join(f"<span>{esc(k)}</span>" for k in (item.get("keywords") or [])[:4])
    iid = esc(item.get("id", ""))
    meta = " · ".join(x for x in [_sources(item), item.get("date_pub", "")] if x)
    major = item.get("tier") == "major"
    search = " ".join([item.get("headline", ""), lede] + [b["p"] for b in blocks] + list(item.get("keywords") or []))
    return f"""<article class="it{' major' if major else ''}" id="i-{iid}" data-k="{esc(search)}">
  <h3>{esc(item.get('headline',''))}</h3>
  <div class="meta">{esc(meta)}</div>
  {f'<p class="lede">{esc(lede)}</p>' if lede else ''}
  <div class="body">{body}</div>
  {f'<div class="tags">{tags}</div>' if tags else ''}
  <div class="ops">
    <button data-fav="{iid}">收藏</button>
    <button data-fb="{iid}" data-val="up">有用</button>
    <button data-fb="{iid}" data-val="down">没用</button>
    <a href="{esc(item.get('url',''))}" target="_blank" rel="noopener">原文 ↗</a>
  </div>
</article>"""


def _section_html(sec: dict) -> str:
    items = "".join(_item_html(it) for it in sec.get("items") or [])
    return f"""<section class="sec" id="{esc(sec['key'])}">
  <div class="sec-head">
    <span class="sec-idx">{esc(sec.get('idx',''))}</span>
    <h2 class="sec-name">{esc(sec['name'])}</h2>
    <span class="sec-en">{esc(sec.get('en',''))}</span>
  </div>
  <p class="sec-blurb">{esc(sec.get('blurb',''))}</p>
  {items}
</section>"""


def _deep_html(dd: dict) -> str:
    if not dd or not dd.get("question"):
        return ""
    blocks = []
    if dd.get("background"):
        blocks.append(f'<h4>背景</h4><p>{esc(dd["background"])}</p>')
    if dd.get("timeline"):
        tl = "".join(
            f'<li><span class="w">{esc(t.get("when",""))}</span>{esc(t.get("what",""))}</li>'
            for t in dd["timeline"]
        )
        blocks.append(f"<h4>时间线</h4><ul>{tl}</ul>")
    if dd.get("tensions"):
        rows = []
        for t in dd["tensions"]:
            if isinstance(t, dict):
                who = esc(t.get("who", ""))
                what = esc(t.get("what", ""))
                rows.append(f'<li><span class="w">{who}</span>{what}</li>' if who else f"<li>{what}</li>")
            else:
                rows.append(f"<li>{esc(t)}</li>")
        blocks.append(f'<h4>核心矛盾</h4><ul>{"".join(rows)}</ul>')
    if dd.get("views"):
        vw = "".join(
            f'<div class="vw"><b>{esc(v.get("stance",""))}</b>{esc(v.get("claim",""))}</div>' for v in dd["views"]
        )
        blocks.append(f'<h4>不同立场</h4><div>{vw}</div>')
    if dd.get("reading"):
        rd = "".join(
            f'<li><b>{esc(r.get("title",""))}</b>　{esc(r.get("author",""))}　{esc(r.get("why",""))}</li>'
            for r in dd["reading"]
        )
        blocks.append(f"<h4>延伸阅读</h4><ul>{rd}</ul>")
    return f"""<section class="deep" id="deep">
  <div class="kicker">本周深度观察</div>
  <h2>{esc(dd["question"])}</h2>
  {f'<p class="lead">{esc(dd.get("lead",""))}</p>' if dd.get("lead") else ''}
  {"".join(blocks)}
</section>"""


def _head(issue: dict, extra_tools: str = "") -> str:
    week = issue.get("week", "")
    num = week.split("W")[-1] if "W" in week else ""
    left = f"第 {num} 期" if num else "WEEKLY BRIEF"
    total = sum(len(x.get("items", [])) for x in issue.get("sections", []))
    sub = f"每周五 · {total} 篇 · 约 {max(4, round(total * 1.6))} 分钟" if total else "每周五更新"
    return f"""<header class="mast"><div class="wrap">
  <div class="mast-top">
    <span class="brand"><a href="index.html">{esc(left)}</a></span>
    <span class="issue">{esc(week)}</span>
  </div>
  <div class="title-block">
    <h1 class="mast-title">Weekly Brief</h1>
    <div class="mast-sub">{esc(sub)}</div>
  </div>
  <div class="dateline"><span>{esc(issue.get('range',''))}</span></div>
  <div class="tools">{extra_tools}
    <button id="sbtn" class="btn">搜索</button>
    <button id="favfilter" class="btn">收藏</button>
    <button id="theme" class="btn">夜间</button>
  </div>
  <div id="searchwrap" class="hidden"><input id="search" class="search" type="search" placeholder="搜索标题、正文、关键词"></div>
</div></header>"""


def _nav(issue: dict) -> str:
    links = "".join(
        f'<a href="#{esc(s["key"])}">{esc(s["name"])}</a>' for s in issue.get("sections", [])
    )
    if issue.get("deep_dive"):
        links += '<a href="#deep">深度观察</a>'
    return f'<nav class="ticker"><div class="wrap" style="display:flex">{links}</div></nav>'


def _footer(issue: dict, archive: str, thinking: str) -> str:
    st = issue.get("stats") or {}
    n = sum(len(s.get("items", [])) for s in issue.get("sections", []))
    usage = st.get("usage") or {}
    tok = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
    return f"""<footer><div class="wrap">
  {n} 篇，全部由 AI 依据本周公开报道撰写；数字与事实以其链接的原文为准。<br>
  {esc(issue.get('generated_date',''))} 生成 · 处理 {st.get('articles',0)} 篇报道 · {tok/1000:.0f}k tokens<br>
  <a href="{archive}">往期</a><a href="{thinking}">思想档案</a>
</div></footer>"""


def render_issue(issue: dict, cfg: dict) -> str:
    sections = issue.get("sections") or []
    archive = "../archive.html" if issue.get("_in_issues_dir") else "archive.html"
    thinking = "../thinking.html" if issue.get("_in_issues_dir") else "thinking.html"

    note = (issue.get("note") or "").strip()
    opening = (issue.get("opening") or "").strip()
    total = sum(len(s.get("items", [])) for s in sections)

    lead = note or opening
    intro = ""
    if lead:
        intro += (
            '<div class="standfirst"><span class="lab">本期主线 / In this issue</span>'
            f"<p>{esc(lead)}</p></div>"
        )
    intro += f'<div class="count">{total} stories · {max(4, round(total * 1.6))} min</div>'

    body = (
        _head(issue)
        + _nav(issue)
        + f'<div class="wrap">{intro}</div>'
        + '<main class="wrap">'
        + "".join(_section_html(s) for s in sections)
        + _deep_html(issue.get("deep_dive") or {})
        + '<div id="noresult" class="hidden" style="margin:40px 0;color:var(--ink3);font-size:14px">没有匹配的内容。</div>'
        + "</main>"
        + _footer(issue, archive, thinking)
    )

    return (
        TEMPLATE.replace("__CSS__", CSS)
        .replace("__JS__", JS)
        .replace("__BODY__", body)
        .replace("__WEEK__", issue.get("week", ""))
        .replace("__TITLE__", f"{cfg.get('title','WEEKLY BRIEF')} · {issue.get('week','')}")
        .replace("__DESC__", esc((opening or note or issue.get("range", ""))[:120]))
    )


def render_archive(index: dict) -> str:
    rows = "".join(
        f'<li><a href="issues/{esc(i["week"])}.html"><span class="w">{esc(i["week"])}</span>'
        f'<span class="t">{esc(i.get("range",""))}　{esc(_short(i.get("note",""),34))}</span></a></li>'
        for i in index.get("issues", [])
    )
    head = f"""<header class="mast"><div class="wrap">
  <div class="mast-top">
    <span class="brand"><a href="index.html">Weekly Brief</a></span>
    <span class="issue">ARCHIVE</span>
  </div>
  <div class="tools"><button id="theme" class="btn">夜间</button></div>
</div></header>"""
    body = head + f"""<main class="page wrap">
  <h1 class="title">往期</h1>
  <p class="sub">共 {len(index.get('issues', []))} 期。搜索会检索全部历史正文。</p>
  <input id="q" class="search" placeholder="搜索所有往期…">
  <div id="hits"></div>
  <ul class="archlist">{rows}</ul>
</main>"""
    script = r"""
(function(){
  var data=null,hits=document.getElementById('hits'),q=document.getElementById('q');
  fetch('data/index.json').then(function(r){return r.json()}).then(function(d){data=d}).catch(function(){});
  q.addEventListener('input',function(){
    var v=q.value.trim().toLowerCase(); if(!data) return;
    if(!v){hits.innerHTML='';return;}
    var rows=data.items.filter(function(it){
      return (it.h+' '+it.d+' '+it.k+' '+it.s).toLowerCase().indexOf(v)>=0;
    }).slice(0,40);
    hits.innerHTML = rows.length ? rows.map(function(it){
      return '<div class="hit"><a href="issues/'+it.w+'.html#i-'+it.i+'"><b>'+it.h+'</b></a>'+
             '<span>'+it.w+' · '+it.s+'</span></div>';}).join('')
      : '<p style="color:var(--ink3);font-size:13px;padding:14px 0">没有找到。</p>';
  });
})();
"""
    return (
        TEMPLATE.replace("__CSS__", CSS).replace("__JS__", JS + script).replace("__BODY__", body)
        .replace("__WEEK__", "").replace("__TITLE__", "往期 · WEEKLY BRIEF")
        .replace("__DESC__", "往期周报")
    )


def render_thinking(index: dict, issues: list[dict]) -> str:
    items = []
    for d in issues:
        for q in d.get("questions3") or []:
            items.append(f'<li><span class="w">{esc(d.get("week",""))}</span>{esc(q)}</li>')
    head = f"""<header class="mast"><div class="wrap">
  <div class="mast-top">
    <span class="brand"><a href="index.html">Weekly Brief</a></span>
    <span class="issue">THINKING</span>
  </div>
  <div class="tools"><a class="btn" href="archive.html">往期</a><button id="theme" class="btn">夜间</button></div>
</div></header>"""
    body = head + f"""<main class="page wrap">
  <h1 class="title">思想档案</h1>
  <p class="sub">每周三个值得长期思考的问题。</p>
  <ul class="archlist">{''.join(items) or '<li><span class="t">还没有积累。</span></li>'}</ul>
</main>"""
    return (
        TEMPLATE.replace("__CSS__", CSS).replace("__JS__", JS).replace("__BODY__", body)
        .replace("__WEEK__", "").replace("__TITLE__", "思想档案 · WEEKLY BRIEF")
        .replace("__DESC__", "每周三个值得长期思考的问题")
    )


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
