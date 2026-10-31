"""渲染：把一期周报变成一份自包含、手机优先的 HTML。"""
from __future__ import annotations

import html as ht
import json
import os

from .util import fmt_cn

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CSS = r"""
*,*::before,*::after{box-sizing:border-box}
:root{
  --bg:#f8f8f6; --bg-soft:#efefea; --card:#ffffff; --fg:#17181a; --fg-2:#4a4d52;
  --fg-3:#8b8f96; --line:#e2e2dc; --accent:#6c5ce7; --shadow:0 1px 2px rgba(20,20,25,.04),0 12px 32px -20px rgba(20,20,25,.28);
  --serif:"Songti SC","Noto Serif SC",ui-serif,Georgia,"Times New Roman",serif;
  --sans:-apple-system,BlinkMacSystemFont,"SF Pro SC","PingFang SC","Segoe UI",Roboto,"Helvetica Neue",sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
  --maxw:720px;
}
html[data-theme="dark"]{
  --bg:#0e0f11; --bg-soft:#16181b; --card:#15171a; --fg:#f2f2ef; --fg-2:#b9bcc2;
  --fg-3:#7d828a; --line:#26292e; --shadow:0 1px 2px rgba(0,0,0,.5),0 18px 40px -24px rgba(0,0,0,.8);
}
html{ -webkit-text-size-adjust:100%; scroll-behavior:smooth; }
body{
  margin:0; background:var(--bg); color:var(--fg); font-family:var(--sans);
  font-size:16px; line-height:1.75; letter-spacing:.01em;
  -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility;
  overflow-x:hidden;
}
@media (prefers-reduced-motion:reduce){ html{scroll-behavior:auto} *{animation:none!important;transition:none!important} }
::selection{background:var(--accent);color:#fff}
a{color:inherit;text-decoration:none}
.wrap{max-width:var(--maxw);margin:0 auto;padding:0 22px}
.wide{max-width:900px;margin:0 auto;padding:0 22px}

/* ---------- 进度条 ---------- */
#prog{position:fixed;top:0;left:0;height:2px;width:0;background:var(--accent);z-index:99;transition:width .1s linear}

/* ---------- 顶部 ---------- */
.hero{padding:64px 0 34px;position:relative}
.hero::after{content:"";position:absolute;inset:0;z-index:-1;
  background:radial-gradient(760px 340px at 12% -12%, color-mix(in srgb, var(--accent) 8%, transparent), transparent 72%);}
.kicker{font-family:var(--mono);font-size:11px;letter-spacing:.28em;text-transform:uppercase;color:var(--fg-3);
  display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.kicker .dot{width:5px;height:5px;border-radius:50%;background:var(--accent);display:inline-block}
h1{font-family:var(--serif);font-weight:600;font-size:clamp(40px,10vw,68px);line-height:1.02;
  letter-spacing:-.02em;margin:18px 0 6px}
h1 .num{font-family:var(--mono);font-size:.32em;letter-spacing:.1em;color:var(--fg-3);vertical-align:super;margin-left:6px;font-weight:400}
.meta-line{display:flex;gap:10px;flex-wrap:wrap;align-items:center;color:var(--fg-3);font-size:13px;margin-top:14px}
.meta-line span{white-space:nowrap}
.sep{width:3px;height:3px;border-radius:50%;background:var(--fg-3);opacity:.6}
.opening{font-family:var(--serif);font-size:clamp(17px,2.4vw,19px);line-height:1.9;color:var(--fg-2);
  margin:26px 0 0;padding-left:18px;border-left:2px solid var(--accent)}
.notice{margin:22px 0 0;padding:10px 14px;border:1px dashed var(--line);border-radius:8px;
  font-size:13px;color:var(--fg-2);background:var(--bg-soft);line-height:1.7}
.notice.warn{border-color:#e17055;background:color-mix(in srgb,#e17055 8%,transparent)}
.notice.warn b{color:#e17055}
.notice b{font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin-right:8px}
.mode{display:inline-flex;align-items:center;gap:6px;font-family:var(--mono);font-size:10px;letter-spacing:.12em;
  text-transform:uppercase;border:1px solid var(--line);border-radius:99px;padding:3px 9px;color:var(--fg-3)}

/* ---------- 导航 ---------- */
nav.toc{position:sticky;top:0;z-index:40;backdrop-filter:saturate(160%) blur(14px);
  -webkit-backdrop-filter:saturate(160%) blur(14px);background:color-mix(in srgb,var(--bg) 82%,transparent);
  border-bottom:1px solid var(--line)}
nav.toc .inner{display:flex;gap:6px;overflow-x:auto;padding:10px 22px;max-width:var(--maxw);margin:0 auto;
  scrollbar-width:none}
nav.toc .inner::-webkit-scrollbar{display:none}
nav.toc a{flex:0 0 auto;font-size:13px;color:var(--fg-2);padding:6px 12px;border-radius:99px;
  border:1px solid transparent;transition:.18s;display:flex;gap:7px;align-items:center}
nav.toc a b{font-family:var(--mono);font-size:10px;color:var(--fg-3);font-weight:400}
nav.toc a:hover{border-color:var(--line);background:var(--card)}
nav.toc a.on{background:var(--fg);color:var(--bg);border-color:var(--fg)}
nav.toc a.on b{color:color-mix(in srgb,var(--bg) 60%,transparent)}

/* ---------- 板块 ---------- */
section.sec{padding:56px 0 10px;border-top:1px solid var(--line);margin-top:34px}
.sec-head{display:flex;align-items:flex-start;gap:16px;margin-bottom:8px}
.sec-idx{font-family:var(--mono);font-size:12px;color:var(--accent);letter-spacing:.1em;padding-top:14px;min-width:26px}
.sec-title{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.sec-title h2{font-family:var(--serif);font-size:clamp(28px,6vw,38px);margin:0;font-weight:600;letter-spacing:-.01em}
.sec-title em{font-style:normal;font-size:12px;letter-spacing:.3em;text-transform:uppercase;color:var(--fg-3);font-family:var(--mono)}
.sec-blurb{color:var(--fg-3);font-size:13px;margin:2px 0 0}
.sec-intro{font-size:15px;color:var(--fg-2);margin:16px 0 30px;line-height:1.85}
.sec-bar{height:2px;background:linear-gradient(90deg,var(--accent),transparent);margin:18px 0 0;border-radius:2px;opacity:.5}

/* ---------- 详读 ---------- */
article.deep{margin:0 0 30px;padding:0 0 0 0;position:relative}
.deep .no{font-family:var(--mono);font-size:11px;color:var(--accent);letter-spacing:.15em;display:block;margin-bottom:6px}
.deep h3{font-size:clamp(19px,3.6vw,22px);line-height:1.45;margin:0 0 8px;font-weight:650;letter-spacing:-.01em}
.src{font-family:var(--mono);font-size:11px;color:var(--fg-3);letter-spacing:.06em;display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
.src .pill{border:1px solid var(--line);border-radius:4px;padding:1px 6px}
.pts{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:14px}
.pt{display:flex;flex-direction:column;gap:2px}
.pt .en{font-family:var(--serif);font-size:14.5px;line-height:1.65;color:var(--fg-3);margin:0;font-style:italic}
.pt .en::before{content:"“";opacity:.45}
.pt .en::after{content:"”";opacity:.45}
.pt .zh{margin:0;font-size:16.5px;line-height:1.85;color:var(--fg)}
.why{margin:14px 0 0;font-size:13.5px;color:var(--fg-2);padding:8px 12px;border-radius:6px;
  background:color-mix(in srgb,var(--accent) 7%,transparent);border-left:2px solid var(--accent)}
.why b{color:var(--accent);font-weight:600;font-family:var(--mono);font-size:10px;letter-spacing:.14em;
  text-transform:uppercase;margin-right:8px;display:inline-block}
.read{font-size:12px;color:var(--fg-3);border-bottom:1px solid var(--line);padding-bottom:1px;margin-left:auto}
.read:hover{color:var(--accent);border-color:var(--accent)}

/* ---------- 速览 ---------- */
.briefs{margin-top:36px;border-top:1px dashed var(--line);padding-top:26px}
.briefs h4{font-family:var(--mono);font-size:10px;letter-spacing:.24em;text-transform:uppercase;color:var(--fg-3);
  margin:0 0 18px;font-weight:500}
ul.blist{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:0}
ul.blist li{border-bottom:1px solid var(--line);padding:14px 0}
ul.blist li:last-child{border-bottom:none}
.bl{display:flex;gap:10px;align-items:baseline}
.bl .bul{color:var(--accent);font-family:var(--mono);font-size:11px;flex:0 0 auto;padding-top:2px}
.bl h5{margin:0;font-size:15.5px;font-weight:600;line-height:1.6;flex:1}
.bl h5 a:hover{color:var(--accent)}
.blzh{margin:4px 0 0 21px;font-size:14px;color:var(--fg-2);line-height:1.7}
.blen{margin:2px 0 0 21px;font-family:var(--serif);font-size:13px;color:var(--fg-3);font-style:italic;line-height:1.6}
.blsrc{margin:3px 0 0 21px;font-family:var(--mono);font-size:10px;color:var(--fg-3);letter-spacing:.08em}

/* ---------- 页脚 ---------- */
footer{margin-top:70px;border-top:1px solid var(--line);padding:30px 0 60px;color:var(--fg-3);font-size:12px}
footer .grid{display:grid;grid-template-columns:1fr 1fr;gap:28px}
footer h6{font-family:var(--mono);font-size:9.5px;letter-spacing:.2em;text-transform:uppercase;margin:0 0 10px;color:var(--fg-3)}
footer ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:4px}
footer li{display:flex;justify-content:space-between;gap:10px}
footer .bad{color:#d63031}
footer .ok{color:#00b894}
.tools{position:fixed;right:16px;bottom:16px;display:flex;flex-direction:column;gap:8px;z-index:50}
.tools button{width:40px;height:40px;border-radius:50%;border:1px solid var(--line);background:var(--card);
  color:var(--fg-2);cursor:pointer;display:grid;place-items:center;box-shadow:var(--shadow);font-size:15px}
.tools button:hover{color:var(--accent)}

/* ---------- 动效 ---------- */
.rv{opacity:0;transform:translateY(14px);transition:opacity .6s cubic-bezier(.2,.7,.3,1),transform .6s cubic-bezier(.2,.7,.3,1)}
.rv.in{opacity:1;transform:none}
@media (prefers-reduced-motion:reduce){ .rv{opacity:1;transform:none} }
@media (max-width:560px){
  .hero{padding:44px 0 24px}
  section.sec{padding:42px 0 6px}
  article.deep{margin-bottom:26px}
  footer .grid{grid-template-columns:1fr}
}
"""

JS = r"""
(function(){
  var root=document.documentElement;
  var saved=localStorage.getItem('wb-theme');
  if(saved){root.dataset.theme=saved}
  else{root.dataset.theme=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}

  var btn=document.getElementById('theme');
  if(btn){btn.addEventListener('click',function(){
    var next=root.dataset.theme==='dark'?'light':'dark';
    root.dataset.theme=next;localStorage.setItem('wb-theme',next);
    btn.textContent=next==='dark'?'☀':'☾';
  });
  btn.textContent=root.dataset.theme==='dark'?'☀':'☾';}

  var prog=document.getElementById('prog');
  function onScroll(){
    var h=document.documentElement;
    var pct=h.scrollTop/(h.scrollHeight-h.clientHeight)*100;
    if(prog)prog.style.width=pct+'%';
  }
  addEventListener('scroll',onScroll,{passive:true});onScroll();

  var links=[].slice.call(document.querySelectorAll('nav.toc a'));
  var secs=links.map(function(a){return document.querySelector(a.getAttribute('href'))});
  var io=new IntersectionObserver(function(es){
    es.forEach(function(e){
      if(e.isIntersecting){
        var i=secs.indexOf(e.target);
        links.forEach(function(l,j){l.classList.toggle('on',j===i)});
      }
    });
  },{rootMargin:'-45% 0px -50% 0px'});
  secs.forEach(function(s){if(s)io.observe(s)});

  var rv=[].slice.call(document.querySelectorAll('.rv'));
  if('IntersectionObserver' in window){
    var io2=new IntersectionObserver(function(es){
      es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('in');io2.unobserve(e.target)}});
    },{rootMargin:'0px 0px -8% 0px',threshold:.05});
    rv.forEach(function(n){io2.observe(n)});
  }else{rv.forEach(function(n){n.classList.add('in')})}

  var top=document.getElementById('top');
  if(top)top.addEventListener('click',function(){scrollTo({top:0,behavior:'smooth'})});
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
<meta name="theme-color" content="__THEME_COLOR__">
<meta property="og:title" content="__TITLE__">
<meta property="og:description" content="__DESC__">
<meta property="og:type" content="article">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='22' fill='%230e0f11'/><text x='50' y='68' font-size='52' text-anchor='middle' fill='%23ffffff' font-family='monospace'>W</text></svg>">
<style>__CSS__</style>
</head>
<body>
<div id="prog"></div>
__BODY__
<div class="tools"><button id="theme" aria-label="切换主题">☾</button><button id="top" aria-label="回到顶部">↑</button></div>
<script>__JS__</script>
</body>
</html>
"""


def esc(text: str) -> str:
    return ht.escape(text or "", quote=True)


def reading_minutes(issue: dict) -> int:
    chars = len(issue.get("opening", ""))
    for sec in issue["sections"]:
        chars += len(sec.get("intro", ""))
        for it in sec["items"]:
            chars += len(it["headline"]) + len(it.get("why", ""))
            for p in it["points"]:
                chars += len(p["zh"]) + len(p["en"]) // 2
    return max(1, round(chars / 420))


def _points_html(item: dict) -> str:
    rows = []
    for p in item["points"]:
        en = (p.get("en") or "").strip()
        zh = (p.get("zh") or "").strip()
        if en:
            rows.append(f'<li class="pt"><p class="en">{esc(en)}</p><p class="zh">{esc(zh)}</p></li>')
        elif zh:
            rows.append(f'<li class="pt"><p class="zh">{esc(zh)}</p></li>')
    return '<ul class="pts">' + "".join(rows) + "</ul>" if rows else ""


def _detailed_html(item: dict, idx: int) -> str:
    src = esc(item.get("source", ""))
    date = esc(item.get("date", ""))
    extra = [s for s in item.get("sources_all", []) if s and s != item.get("source")]
    also = f'<span class="pill">+{len(extra)} 家同时报道</span>' if extra else ""
    why = (
        f'<p class="why"><b>Why</b>{esc(item["why"])}</p>' if item.get("why") else ""
    )
    link = (
        f'<a class="read" href="{esc(item["url"])}" target="_blank" rel="noopener">原文 ↗</a>'
        if item.get("url") else ""
    )
    return f"""<article class="deep rv">
  <span class="no">{idx:02d}</span>
  <h3>{esc(item["headline"])}</h3>
  <div class="src"><span>{src}</span><span class="sep"></span><span>{date}</span>{also}{link}</div>
  {_points_html(item)}
  {why}
</article>"""


def _brief_html(item: dict) -> str:
    en = ""
    zh = ""
    for p in item["points"]:
        if p.get("zh") and not zh:
            zh = p["zh"]
        if p.get("en") and not en:
            en = p["en"]
    en_line = f'<p class="blen">{esc(en)}</p>' if en and item.get("lang") == "en" else ""
    zh_line = f'<p class="blzh">{esc(zh)}</p>' if zh else ""
    link = (
        f'<a href="{esc(item["url"])}" target="_blank" rel="noopener">{esc(item["headline"])}</a>'
        if item.get("url") else esc(item["headline"])
    )
    return f"""<li>
  <div class="bl"><span class="bul">◆</span><h5>{link}</h5></div>
  {zh_line}{en_line}
  <p class="blsrc">{esc(item.get('source',''))} · {esc(item.get('date',''))}</p>
</li>"""


def _section_html(sec: dict, idx: int) -> str:
    detaileds = [it for it in sec["items"] if it.get("detailed")]
    briefs = [it for it in sec["items"] if not it.get("detailed")]
    deep = "\n".join(_detailed_html(it, i + 1) for i, it in enumerate(detaileds))
    brief_list = "\n".join(_brief_html(it) for it in briefs)
    brief_block = (
        f'<div class="briefs rv"><h4>其余值得一扫</h4><ul class="blist">{brief_list}</ul></div>'
        if briefs else ""
    )
    head = f"""<div class="sec-head rv">
  <span class="sec-idx">{idx:02d}</span>
  <div>
    <div class="sec-title"><h2>{esc(sec['cn'] or sec['name'])}</h2><em>{esc(sec['name'])}</em></div>
    <p class="sec-blurb">{esc(sec.get('blurb',''))}</p>
  </div>
</div>
<div class="sec-bar"></div>"""
    intro = f'<p class="sec-intro rv">{esc(sec.get("intro",""))}</p>' if sec.get("intro") else ""
    note = f'<p class="sec-blurb rv">⚠ {esc(sec["note"])}</p>' if sec.get("note") else ""
    return f"""<section class="sec" id="{esc(sec['key'])}" style="--accent:{esc(sec.get('accent','#6c5ce7'))}">
{head}
{intro}{note}
{deep}
{brief_block}
</section>"""


def _nav_html(sections: list[dict]) -> str:
    links = "".join(
        f'<a href="#{esc(s["key"])}"><b>{i+1:02d}</b>{esc(s["cn"] or s["name"])}</a>'
        for i, s in enumerate(sections)
    )
    return f'<nav class="toc"><div class="inner">{links}</div></nav>'


def _footer_html(issue: dict) -> str:
    bad = [s for s in issue["sources"] if not s["ok"]]
    rows = "".join(
        f'<li><span>{esc(s["name"])}</span><span class="{"ok" if s["ok"] else "bad"}">'
        f'{"✓ " + str(s["count"]) if s["ok"] else "×"}</span></li>'
        for s in issue["sources"][:24]
    )
    mode = {"llm": "大模型双语", "mixed": "部分降级", "rule": "规则摘要"}.get(issue.get("mode"), "规则摘要")
    return f"""<footer><div class="wrap">
<div class="grid">
  <div><h6>数据来源 · {issue['stats']['sources_ok']}/{issue['stats']['sources_total']} 正常</h6><ul>{rows}</ul></div>
  <div>
    <h6>关于本期</h6>
    <ul>
      <li><span>生成时间</span><span>{esc(issue.get('generated_date',''))} {esc(issue.get('generated_at','')[11:16])}</span></li>
      <li><span>摘要方式</span><span>{mode}</span></li>
      <li><span>处理文章</span><span>{issue['stats']['articles']} 篇</span></li>
      <li><span>耗时</span><span>{issue['stats']['elapsed']}s</span></li>
    </ul>
    <h6 style="margin-top:18px">归档</h6>
    <ul><li><a href="__ARCHIVE__">往期周报 →</a></li></ul>
  </div>
</div>
</div></footer>"""


def render_issue(issue: dict, cfg: dict | None = None) -> str:
    cfg = cfg or {}
    title_base = cfg.get("title", "WEEKLY BRIEF")
    week_num = issue["week"].split("-")[-1]
    mins = reading_minutes(issue)
    n_items = sum(len(s["items"]) for s in issue["sections"])

    opening = f'<p class="opening rv">{esc(issue["opening"])}</p>' if issue.get("opening") else ""
    notice = ""
    stats = issue.get("stats", {})
    total_items = sum(len(s["items"]) for s in issue["sections"])
    ok_ratio = (stats.get("sources_ok", 0) / stats["sources_total"]) if stats.get("sources_total") else 1
    if total_items < 12 or ok_ratio < 0.5:
        notice = (
            '<p class="notice warn"><b>注意</b>本期抓取不完整'
            f"（{stats.get('sources_ok', 0)}/{stats.get('sources_total', 0)} 个源成功，共 {total_items} 条）。"
            '内容可能偏少，可以稍后在本地重跑一次，或先看<a href="__ARCHIVE__">往期</a>。</p>'
        )
    elif issue.get("mode") != "llm":
        notice = (
            '<p class="notice"><b>提示</b>本期是规则摘要（没有配置 API Key）：'
            "英文条目只有原文和自动摘录，没有中文翻译。"
            "在 <code>.env</code> 里填入 <code>DEEPSEEK_API_KEY</code> 后，"
            "下次生成会自动变成逐句中英对照。</p>"
        )
    label = {"llm": "LLM 双语", "mixed": "部分降级", "rule": "规则摘要"}.get(issue.get("mode"), "规则摘要")
    mode_badge = f'<span class="mode">{label}</span>'

    hero = f"""<header class="hero"><div class="wrap">
  <div class="kicker"><span class="dot"></span>WEEKLY BRIEF<span class="sep"></span>{esc(issue['week'])}</div>
  <h1>{esc(title_base)}<span class="num">No.{week_num}</span></h1>
  <div class="meta-line">
    <span>{esc(issue['range'])}</span><span class="sep"></span>
    <span>{n_items} 条</span><span class="sep"></span>
    <span>约 {mins} 分钟</span><span class="sep"></span>{mode_badge}
  </div>
  {opening}
  {notice}
</div></header>"""

    live = [sec for sec in issue["sections"] if sec.get("items")]
    sections = "\n".join(_section_html(sec, i + 1) for i, sec in enumerate(live))
    body = (
        hero
        + _nav_html(live)
        + f'<main class="wrap">{sections}</main>'
        + _footer_html(issue)
    )
    archive_link = "../archive.html" if issue.get("_in_issues_dir") else "archive.html"
    body = body.replace("__ARCHIVE__", archive_link)

    return (
        TEMPLATE.replace("__CSS__", CSS)
        .replace("__JS__", JS)
        .replace("__BODY__", body)
        .replace("__TITLE__", f"{title_base} · {issue['week']} 周报")
        .replace("__DESC__", esc((issue.get("opening") or issue["range"])[:110]))
        .replace("__THEME_COLOR__", "#f7f7f4")
    )


def render_archive(issue: dict) -> str:
    """归档页：列出 site/data 下所有期数。"""
    data_dir = os.path.join(ROOT, "site", "data")
    rows = []
    files = sorted(os.listdir(data_dir), reverse=True) if os.path.isdir(data_dir) else []
    for name in files:
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(data_dir, name), encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:  # noqa: BLE001
            continue
        week = data.get("week", name[:-5])
        count = sum(len(s["items"]) for s in data.get("sections", []))
        rows.append(
            f'<a class="row" href="issues/{esc(week)}.html">'
            f'<span class="wk">{esc(week)}</span>'
            f'<span class="rg">{esc(data.get("range",""))}</span>'
            f'<span class="ct">{count} 条</span></a>'
        )
    listing = "".join(rows) or '<p style="color:var(--fg-3)">还没有往期。</p>'
    body = f"""<header class="hero"><div class="wrap">
  <div class="kicker"><span class="dot"></span>ARCHIVE</div>
  <h1>往期<span class="num">{len(rows)}</span></h1>
  <p class="opening">每周五晚自动生成，按 ISO 周编号排列。</p>
</div></header>
<main class="wrap"><ul class="arch">{listing}</ul></main>"""
    extra_css = """
ul.arch{list-style:none;padding:0;margin:0}
ul.arch a.row{display:grid;grid-template-columns:110px 1fr auto;gap:12px;padding:16px 0;
  border-bottom:1px solid var(--line);align-items:baseline;transition:.18s}
ul.arch a.row:hover{padding-left:6px}
ul.arch .wk{font-family:var(--mono);font-size:12px;color:var(--accent);letter-spacing:.06em}
ul.arch .rg{font-size:15px}
ul.arch .ct{font-size:12px;color:var(--fg-3)}
"""
    return (
        TEMPLATE.replace("__CSS__", CSS + extra_css)
        .replace("__JS__", JS)
        .replace("__BODY__", body)
        .replace("__TITLE__", "往期 · WEEKLY BRIEF")
        .replace("__DESC__", "往期周报归档")
    )


def write_site(issue: dict, html_text: str, cfg: dict, preview: bool = False) -> str:
    out_dir = os.path.join(ROOT, cfg.get("output", {}).get("dir", "site"))
    if preview:
        prev = os.path.join(out_dir, "preview")
        os.makedirs(prev, exist_ok=True)
        path = os.path.join(prev, "index.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html_text)
        return path
    issues_dir = os.path.join(out_dir, "issues")
    os.makedirs(issues_dir, exist_ok=True)
    issue = {**issue, "_in_issues_dir": True}
    issue_html = render_issue(issue, cfg)
    issue_path = os.path.join(issues_dir, f"{issue['week']}.html")
    with open(issue_path, "w", encoding="utf-8") as fh:
        fh.write(issue_html)

    index = render_issue({**issue, "_in_issues_dir": False}, cfg)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(index)

    with open(os.path.join(out_dir, "archive.html"), "w", encoding="utf-8") as fh:
        fh.write(render_archive(issue))
    return issue_path
