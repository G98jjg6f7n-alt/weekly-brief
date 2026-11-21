"""渲染 v4：手机优先的单列阅读页——没有图片、没有卡片，只有文字。"""
from __future__ import annotations

import html as ht
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CSS = r"""
*,*::before,*::after{box-sizing:border-box}
:root{
  --bg:#fcfbf8; --ink:#14171b; --ink2:#3d434b; --ink3:#8d9199;
  --rule:#e4e0d6; --accent:#8c2f1f;
  --serif:"Songti SC","Noto Serif SC",ui-serif,Georgia,"Times New Roman",serif;
  --sans:-apple-system,BlinkMacSystemFont,"PingFang SC","Segoe UI",Roboto,sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
  --w:660px;
}
html[data-theme="dark"]{
  --bg:#101214; --ink:#f0efe9; --ink2:#b9bdc4; --ink3:#767b83;
  --rule:#25282d; --accent:#d99a86;
}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);
  font-size:16px;line-height:1.85;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
button{font-family:inherit;font-size:inherit;cursor:pointer;background:none;border:none;color:inherit}
.wrap{max-width:var(--w);margin:0 auto;padding:0 22px}

/* 刊头 */
header.top{padding:26px 0 14px}
.toprow{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
.brand{font-family:var(--serif);font-size:25px;font-weight:600;letter-spacing:.01em;line-height:1}
.topmeta{font-family:var(--mono);font-size:10px;letter-spacing:.16em;color:var(--ink3);text-align:right;line-height:1.8}
.tools{display:flex;gap:14px;margin-top:12px;font-size:12px;color:var(--ink3)}
.tools button,.tools a{padding:2px 0;border-bottom:1px solid transparent}
.tools button:hover,.tools a:hover{color:var(--ink);border-bottom-color:var(--rule)}

/* 导语 */
.note{font-family:var(--serif);font-size:17.5px;line-height:1.75;color:var(--ink);
  margin:16px 0 0;padding-left:14px;border-left:2px solid var(--accent)}
.opening{font-size:15.5px;line-height:1.9;color:var(--ink2);margin:14px 0 0}
.count{font-family:var(--mono);font-size:10.5px;color:var(--ink3);letter-spacing:.1em;margin-top:12px}

/* 目录 */
nav.chips{display:flex;gap:8px;overflow-x:auto;margin:18px 0 0;padding-bottom:4px;
  scrollbar-width:none;-webkit-overflow-scrolling:touch}
nav.chips::-webkit-scrollbar{display:none}
nav.chips a{flex:0 0 auto;font-size:13px;color:var(--ink2);border:1px solid var(--rule);
  border-radius:999px;padding:4px 12px;line-height:1.5}
nav.chips a:hover{border-color:var(--ink3);color:var(--ink)}

/* 栏目 */
section.sec{margin-top:46px;border-top:1px solid var(--rule);padding-top:18px}
section.sec h2{font-family:var(--serif);font-size:22px;font-weight:600;margin:0;line-height:1.3}
section.sec h2 .idx{font-family:var(--mono);font-size:11px;color:var(--accent);letter-spacing:.1em;margin-right:8px;vertical-align:2px}
section.sec h2 .en{font-family:var(--mono);font-size:9.5px;color:var(--ink3);letter-spacing:.18em;margin-left:10px;vertical-align:2px}
section.sec .blurb{font-size:13px;color:var(--ink3);margin:6px 0 0}

/* 单条报道 */
article.it{margin:30px 0 0}
article.it h3{font-family:var(--serif);font-size:19.5px;font-weight:600;line-height:1.45;margin:0;letter-spacing:.01em}
article.it h3 a:hover{color:var(--accent)}
article.it .meta{font-family:var(--mono);font-size:10px;letter-spacing:.09em;color:var(--ink3);margin:7px 0 0}
article.it .lede{font-size:16.5px;line-height:1.8;color:var(--ink);margin:12px 0 0}
article.it .body p{font-size:16px;line-height:1.9;color:var(--ink2);margin:12px 0 0}
article.it .body p::selection,article.it .lede::selection{background:#f3d9b8}
.tags{font-size:11.5px;color:var(--ink3);margin-top:14px;line-height:1.9}
.tags span{margin-right:10px}
.ops{display:flex;flex-wrap:wrap;gap:16px;margin-top:10px;font-size:12px;color:var(--ink3)}
.ops button,.ops a{padding:2px 0;border-bottom:1px solid transparent}
.ops button:hover,.ops a:hover{color:var(--ink)}
.ops button.on{color:var(--accent);border-bottom-color:var(--accent)}
.hidden{display:none!important}

/* 深度观察 */
section.deep{margin-top:56px;border-top:2px solid var(--ink);padding-top:18px}
section.deep .kicker{font-family:var(--mono);font-size:10px;letter-spacing:.2em;color:var(--accent);text-transform:uppercase}
section.deep h2{font-family:var(--serif);font-size:24px;line-height:1.4;margin:12px 0 0;font-weight:600}
section.deep .lead{font-family:var(--serif);font-size:17px;line-height:1.8;color:var(--ink2);margin:12px 0 0}
section.deep h4{font-family:var(--mono);font-size:10px;letter-spacing:.16em;color:var(--ink3);
  text-transform:uppercase;margin:28px 0 8px;font-weight:400}
section.deep p{font-size:16px;line-height:1.9;color:var(--ink2);margin:0}
section.deep ul{list-style:none;padding:0;margin:0}
section.deep li{font-size:15px;line-height:1.8;color:var(--ink2);padding:6px 0;border-bottom:1px solid var(--rule)}
section.deep li:last-child{border-bottom:none}
section.deep li .w{font-family:var(--mono);font-size:10.5px;color:var(--ink3);display:block}
section.deep .vw{padding:10px 0;border-bottom:1px solid var(--rule)}
section.deep .vw:last-child{border-bottom:none}
section.deep .vw b{display:block;font-size:13px;color:var(--ink);margin-bottom:2px}

/* 页脚 */
footer{margin-top:56px;border-top:1px solid var(--rule);padding:18px 0 60px;
  font-size:12px;color:var(--ink3);line-height:1.9}
footer a{border-bottom:1px solid var(--rule);margin-right:16px}

/* 归档 / 思想档案 */
main.page{padding-top:10px}
h1.title{font-family:var(--serif);font-size:28px;font-weight:600;margin:0 0 6px}
p.sub{font-size:13px;color:var(--ink3);margin:0 0 20px}
input.search{width:100%;font-family:var(--sans);font-size:15px;padding:10px 12px;border-radius:8px;
  border:1px solid var(--rule);background:transparent;color:var(--ink);outline:none;margin:6px 0 0}
input.search:focus{border-color:var(--ink3)}
ul.archlist{list-style:none;padding:0;margin:22px 0 0}
ul.archlist li{border-bottom:1px solid var(--rule)}
ul.archlist a{display:flex;justify-content:space-between;gap:12px;padding:13px 0;font-size:14px;line-height:1.6}
ul.archlist .w{font-family:var(--mono);font-size:11px;color:var(--accent);flex:0 0 auto}
ul.archlist .t{flex:1;color:var(--ink2)}
.hit{padding:12px 0;border-bottom:1px solid var(--rule)}
.hit b{font-size:14.5px;font-weight:600}
.hit span{display:block;font-size:11px;color:var(--ink3);margin-top:3px;font-family:var(--mono)}

@media (max-width:420px){
  .wrap{padding:0 18px}
  article.it h3{font-size:18.5px}
  .note{font-size:16.5px}
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
<meta name="theme-color" content="#fcfbf8">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' fill='%2314171b'/><text x='50' y='70' font-size='54' text-anchor='middle' fill='%23fff' font-family='serif'>W</text></svg>">
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
    paras = [p for p in (item.get("paras") or []) if p]
    if not paras and item.get("summary"):
        paras = [item["summary"]]
    body = "".join(f"<p>{esc(p)}</p>" for p in paras)
    lede = (item.get("lede") or "").strip()
    tags = "".join(f"<span>{esc(k)}</span>" for k in (item.get("keywords") or [])[:4])
    iid = esc(item.get("id", ""))
    meta = " · ".join(x for x in [_sources(item), item.get("date_pub", "")] if x)
    search = " ".join([item.get("headline", ""), lede] + paras + list(item.get("keywords") or []))
    return f"""<article class="it" id="i-{iid}" data-k="{esc(search)}">
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
  <h2><span class="idx">{esc(sec.get('idx',''))}</span>{esc(sec['name'])}<span class="en">{esc(sec.get('en',''))}</span></h2>
  <p class="blurb">{esc(sec.get('blurb',''))}</p>
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
        tn = "".join(f"<li>{esc(t)}</li>" for t in dd["tensions"])
        blocks.append(f"<h4>核心矛盾</h4><ul>{tn}</ul>")
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
    return f"""<header class="top"><div class="wrap">
  <div class="toprow">
    <div class="brand"><a href="index.html">WEEKLY BRIEF</a></div>
    <div class="topmeta">{esc(week)}{f'　第 {num} 期' if num else ''}<br>{esc(issue.get('range',''))}</div>
  </div>
  <div class="tools">{extra_tools}
    <button id="sbtn">搜索</button>
    <button id="favfilter">只看收藏</button>
    <button id="theme">明暗</button>
  </div>
  <div id="searchwrap" class="hidden"><input id="search" class="search" type="search" placeholder="搜索标题、正文、关键词"></div>
</div></header>"""


def _nav(issue: dict) -> str:
    links = "".join(
        f'<a href="#{esc(s["key"])}">{esc(s["name"])}</a>' for s in issue.get("sections", [])
    )
    if issue.get("deep_dive"):
        links += '<a href="#deep">深度观察</a>'
    return f'<nav class="chips"><div class="wrap" style="display:flex;gap:8px">{links}</div></nav>'


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
        intro += f'<p class="note">{esc(lead)}</p>'
    intro += f'<div class="count">本期 {total} 篇 · 约 {max(4, round(total * 1.6))} 分钟</div>'

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
    head = f"""<header class="top"><div class="wrap">
  <div class="toprow"><div class="brand"><a href="index.html">WEEKLY BRIEF</a></div>
  <div class="topmeta">ARCHIVE</div></div>
  <div class="tools"><button id="theme">明暗</button></div></div></header>"""
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
    head = f"""<header class="top"><div class="wrap">
  <div class="toprow"><div class="brand"><a href="index.html">WEEKLY BRIEF</a></div>
  <div class="topmeta">THINKING</div></div>
  <div class="tools"><a href="archive.html">往期</a><button id="theme">明暗</button></div></div></header>"""
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
