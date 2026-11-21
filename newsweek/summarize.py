"""精选、摘要与「观察者视角」：全部由大模型生成，失败逐级降级。"""
from __future__ import annotations

import re

from .fetch import Article
from .llm import LLMError, call_llm, parse_json_loose
from .util import split_sentences

BASE_SYSTEM = (
    "你是《WEEKLY BRIEF》的主编。你做的是「新闻 + 解释」，不是资讯搬运。"
    "你的文字克制、具体、有信息密度，从不用「震惊」「重磅」「炸裂」这类词，也不写空洞的套话。"
    "你必须只输出一个 JSON 对象，不要任何解释或 Markdown 代码块。"
)


def system_prompt(cfg: dict) -> str:
    """把读者的长期画像注入系统提示词。"""
    prof = cfg.get("profile") or {}
    if not prof:
        return BASE_SYSTEM
    qs = "；".join(prof.get("questions") or [])
    return (
        BASE_SYSTEM
        + f"\n\n读者画像：{prof.get('who','')}"
        + (f"\n他长期想弄明白的问题：{qs}。" if qs else "")
        + f"\n阅读偏好：{prof.get('taste','')}"
        + (f"\n不要给他：{'、'.join(prof.get('avoid') or [])}。" if prof.get("avoid") else "")
        + f"\n{prof.get('diversity','')}"
    )


def _clip(text: str, n: int) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text[:n]


# ---------------------------------------------------------------- 精选


CURATE_RULES = """你是《WEEKLY BRIEF》的主编。读者是一名中国高中生，但不要按中学生水平选新闻：
他读经济、政治、科技、社会学的深度内容，要求事实、逻辑和机制解释。

【他的兴趣，按优先级】
1. 科技与 AI：模型能力跃升、技术路线变化、Agent/机器人/具身智能、算力与芯片、
   AI 产业链、AI 对就业和教育的影响、真实生产力而不只是产品发布、科技公司的战略竞争。
2. 宏观经济与金融：中国与全球经济、增长与分配、房地产与地方财政、就业与通胀、
   贸易与关税、资本流动、金融风险、政策效果——尤其喜欢「数据背后的机制」。
3. 国际关系：中美、中欧、美国政治、欧洲、冲突与外交、产业链重构、大国竞争、
   贸易体系、能源安全、国际组织。不要日常外交礼仪和例行会议。
4. 社会学与社会结构：人口、生育率、老龄化、城市化、教育、阶层与流动、劳动、
   消费主义、媒体与技术对人的影响、社会心理。要结构性问题，不要单个社会新闻。
5. 历史、政治思想与公共议题：新研究、历史与现实的联系、制度、哲学、思想史、
   公民社会、国家与个人的关系。能挑战常识的最好。
6. 汽车与工业：设计、工程、电动化、智能驾驶、产业格局、车企竞争、概念车、
   汽车史、汽车与 AI 结合、中国车企的全球竞争力。
   普通新车上市、改款、配置调整、商用车发布一律不收，除非它带来真正的工程突破或改变产业格局。
7. 科学与前沿：物理、数学、生物、医学、天文、能源、材料。只要真正的新发现、
   理论进展或长期潜力，不要论文流水账和夸张的「科学家发现」。
8. 企业与产业：Apple/NVIDIA/Tesla/OpenAI/Google/微软/DeepSeek、中国科技企业、
   全球车企、半导体。看战略、技术、商业模式、竞争格局、成败原因，不看日常动态。

【评分：每条候选打 0-10 分，按下面六条权衡】
A 影响范围：影响多少人、多少行业、多少国家？
B 长期影响：三年后还会被提起吗？会改变什么规则或结构？
C 信息增量：有没有新事实、新数据、新趋势，而不只是又一次重复？
D 解释价值：读完能不能更理解某个机制（经济怎么运转、技术怎么扩散、制度怎么失灵）？
E 兴趣匹配：是否落在他上面八个领域里，且是其中的「结构性」事件？
F 重大程度：事情本身的分量，不是当天的热度。
G 不可替代：有没有更重要的事可以替代它？同样的事是不是已经有一条了？

评分尺度：
9-10 = 本周必读，改变格局或有长期解释力；
7-8  = 重要，值得完整报道；
5-6  = 有信息量，可作补充；
0-4  = 不收（例行、地方性、宣传、猎奇、八卦、重复、无背景）。

【一律不收】
地方性偶发社会新闻；普通产品发布与功能更新；企业日常动态；会议、活动、仪式、讲话；
娱乐八卦与名人日常；情绪化煽动内容；营销稿；标题党；同一事件的重复报道；
只因「奇怪」而收录的猎奇新闻；来源不可靠的消息；只有一句「发生了什么」的空壳新闻。

【关于社会新闻的唯一例外】
只有当它能揭示结构性问题时才收：例如一家养老院因资金断裂无法迁址，本身没有价值；
但如果它指向养老体系、地方财政、公共服务供给之间的矛盾，并且材料里有这些信息，才可以收，
且必须在 why 里写明它揭示的是什么结构问题。判断不了就不收。

【配额】
- 目标 12-20 条，宁少勿滥。可以少于 12 条，如果本周确实没有那么多值得读的。
- 不要为了填满栏目而凑数：某个栏目本周没有值得报道的内容，就让它是空的。
- 科技与 AI、经济、国际关系是重点，但不要为了数量把边角料塞进去。
- 保留 0-2 条他兴趣之外、但确实有解释力的内容（例如一篇好的科学史或社会学研究）。
- 单一栏目不超过 4 条。**同一件事只能出现一次**——即使来源不同、措辞不同、角度略有差别；
  只有其中一条是明确的深度分析（解析/调查/评论/复盘）时，才允许第二条，且最多两条。

输出 JSON：
{"picks":[{"id":编号,"section":"栏目key","score":0-10,"importance":3|2|1,
           "why":"不超过 25 字，说明它为什么值得读，或它揭示什么机制"}],
 "note":"本期主线，40-70 字的一句话：把本周最值得记住的 2-3 条线索串起来，说清它们共同指向什么",
 "dropped":"如果本周某栏目明显缺好稿，用一句话说明（没有就留空）"}

importance 对应：3 = 值得做深度报道（每周 3-5 条），2 = 完整报道，1 = 简短一提。"""



def _bigrams(text: str) -> set[str]:
    t = "".join(ch for ch in (text or "") if ch.strip())
    return {t[i:i + 2] for i in range(max(0, len(t) - 1))}


def _similar(a: str, b: str) -> float:
    A, B = _bigrams(a), _bigrams(b)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


def curate(
    sections: list[dict],
    pool: dict[str, list[Article]],
    cfg: dict,
    exclude: set[str] | None = None,
    floor: float | None = None,
    want: int = 0,
    bias: list[str] | None = None,
) -> tuple[list[dict], str]:
    """让模型给候选打分并挑选。失败返回空，由调用方退回本地排序。"""
    lines: list[str] = []
    index: dict[int, tuple[str, Article]] = {}
    n = 1
    per_sec = int((cfg.get("selection") or {}).get("candidates_per_section", 26))
    for sec in sections:
        arts = pool.get(sec["key"], [])[:per_sec]
        for art in arts:
            index[n] = (sec["key"], art)
            lines.append(
                f"#{n} [{sec['key']}] {_clip(art.title, 70)} | {art.source} | {_clip(art.excerpt, 110)}"
            )
            n += 1
    if not lines:
        return [], ""
    user = (
        CURATE_RULES
        + "\n\n候选列表（编号 | 栏目 | 标题 | 来源 | 摘要）：\n"
        + "\n".join(lines)
    )
    if exclude:
        by_url = {art.url: art.title for _k, art in index.values()}
        done = [by_url[u][:16] for u in exclude if u in by_url]
        if done:
            user += "\n\n下面这些已经选过，不要再选：" + "、".join(done)
    if bias:
        missing = [s["name"] for s in sections if s["key"] in set(bias)]
        if missing:
            user += "\n\n这几个栏目目前是空的，优先从里面挑：\n" + "、".join(missing)
    if want:
        user += (
            f"\n\n现在只需要再补 {want} 条。门槛可以放宽到 6 分："
            "宁可要一条有解释力的小报道，也不要交白卷；但绝不能收例行新闻和产品通稿。"
        )
    try:
        data = parse_json_loose(call_llm(cfg, system_prompt(cfg), user, max_tokens=4500))
    except Exception:  # noqa: BLE001
        return [], ""
    picks: list[dict] = []
    seen: set[str] = set()
    kept_titles: list[dict] = []
    order = {s["key"]: i for i, s in enumerate(sections)}
    raw = []
    for p in data.get("picks", []):
        try:
            idx = int(p.get("id"))
            score = float(p.get("score", 6))
        except (TypeError, ValueError):
            continue
        if idx not in index:
            continue
        sec_key, art = index[idx]
        raw.append((score, p, sec_key, art))
    raw.sort(key=lambda x: -x[0])
    cap = int(cfg.get("max_items", 20))
    per_cap = int((cfg.get("selection") or {}).get("section_cap", 4))
    sec_count: dict[str, int] = {}
    for score, p, sec_key, art in raw:
        floor_v = float(floor if floor is not None else (cfg.get("selection") or {}).get("min_score", 7))
        if score < floor_v or len(picks) >= cap:
            continue
        if art.url in seen or (exclude and art.url in exclude):
            continue
        sec = p.get("section") if p.get("section") in order else sec_key
        if sec_count.get(sec, 0) >= per_cap:
            continue
        # 同一事件限流：标题二元组相似度 >0.45 视为同一件事
        dup_hit = False
        interpretive = bool(re.search(r"(解析|解读|分析|评论|调查|幕后|为何|如何|深度|专访|复盘)", art.title))
        for prev in kept_titles:
            if _similar(art.title, prev["title"]) > 0.45:
                same_src = prev["source"] == art.source
                if same_src or not interpretive or prev.get("n", 1) >= 2:
                    dup_hit = True
                prev["n"] = prev.get("n", 1) + 1
                break
        if dup_hit:
            continue
        seen.add(art.url)
        kept_titles.append({"title": art.title, "source": art.source, "n": 1})
        sec_count[sec] = sec_count.get(sec, 0) + 1
        picks.append(
            {
                "article": art,
                "section": sec,
                "score": score,
                "importance": max(1, min(3, int(p.get("importance", 2)))),
                "why": str(p.get("why", ""))[:60],
            }
        )
    return picks, str(data.get("note", "")).strip()


# ---------------------------------------------------------------- 单条写作


MAJOR_RULES = """为下列每条新闻写一篇完整报道。这是本期重要的新闻，要有分析深度，但仍然以事实为骨架。

输出字段：
- headline：中文，不超过 22 字，具体（主体 + 动作 + 关键信息），不用问句和夸张词；
  英文标题要翻译成中文，不要保留英文原文；
- lede：1 句、30-50 字，最重要的事实；
- facts「发生了什么」：120-180 字，事实、数字、时间地点、关键人物，可用材料里的直接引语；
  不要重复 lede 说过的那句话，直接从 lede 之后展开；
- background「背景」：120-180 字，这件事之前发生了什么，为什么会走到这一步；
- significance「为什么值得关注」：120-180 字，影响是什么，对哪些人、哪些行业、哪些国家；
- deeper「更深一层」：120-180 字，它揭示了什么趋势或机制——产业结构、政策逻辑、技术扩散、
  制度失灵，选最相关的一两点讲透，不要面面俱到；
- next「接下来看什么」：60-100 字，列出 1-2 个可验证的观察点（数据、决定、时间节点）。

纪律：
- 只能使用材料里的事实和数字，不得编造；材料没写的不猜，需要时写「目前尚不确定」；
- 区分事实、推论、预测；推论要说明依据；
- 如果材料来自不同立场的媒体，指出它们口径的差异；
- 不写社论腔，不用「标志着」「里程碑」这类空话；
- 高中生能读懂，但不要幼稚化；专业概念第一次出现时用一句话解释；
- 国家组合写全称：中美俄三国、中欧、美日，不要压成「中俄美元首」这种缩写。
输出 JSON：{"items":[{"id":编号,"headline":"","lede":"","facts":"","background":"",
"significance":"","deeper":"","next":""}]}"""


BRIEF_RULES = """为下列每条新闻写一则简短报道，控制在 180-260 字。

输出字段：
- headline：中文，不超过 22 字，具体；英文标题翻译成中文；
- lede：1 句、25-40 字，最重要的事实；
- paras：1-2 段，交代事实 + 一句它意味着什么（有依据的判断，不要空话）。

纪律：只用材料里的事实和数字；不编造；不确定就说明；不写套话；
国家组合写全称（中美俄三国），不要用「中俄美」这类压缩写法。
输出 JSON：{"items":[{"id":编号,"headline":"","lede":"","paras":["",""]}]}"""


MAJOR_HEADS = [
    ("facts", "发生了什么"),
    ("background", "背景"),
    ("significance", "为什么值得关注"),
    ("deeper", "更深一层"),
    ("next", "接下来看什么"),
]


def _blocks_major(e: dict) -> list[dict]:
    out = []
    for key, head in MAJOR_HEADS:
        txt = str(e.get(key) or "").strip()
        if txt:
            out.append({"h": head, "p": txt})
    return out



DEDUPE_RULES = """下面是一期周报的标题列表。请找出「描述同一件事」的多条，决定去掉哪几条。

规则：
- 同一件事只保留一条，保留信息最全、最重要那条（编号小的通常排在前面，但以内容为准）。
- 例外：如果其中一条是明确的深度分析（解析、调查、评论、复盘、幕后），可以保留两条，但最多两条。
- 同一家公司、同一个国家、同一个领域的不同事件不算重复。
- 拿不准就不要删。

只输出 JSON：{"drop": [编号, ...], "why": {"编号": "一句话理由"}}。没有重复就返回 {"drop": []}。
"""


def dedupe(headlines: list[str], cfg: dict) -> list[int]:
    """编辑查重：返回要丢掉的 0-based 下标。"""
    if len(headlines) < 2:
        return []
    lines = "\n".join(f"{i + 1}. {h}" for i, h in enumerate(headlines))
    try:
        data = parse_json_loose(
            call_llm(cfg, system_prompt(cfg), DEDUPE_RULES + "\n\n标题列表：\n" + lines, max_tokens=400)
        )
    except Exception:  # noqa: BLE001
        return []
    out: list[int] = []
    for x in data.get("drop") or []:
        try:
            i = int(x) - 1
        except (TypeError, ValueError):
            continue
        if 0 <= i < len(headlines):
            out.append(i)
    return out


def write_items(
    sec: dict,
    arts: list[Article],
    cfg: dict,
    tiers: dict[str, str] | None = None,
    chunk: int = 3,
) -> dict[str, dict]:
    """分档写作：major 走五段结构，brief 走短稿。"""
    tiers = tiers or {}
    out: dict[str, dict] = {}
    majors = [a for a in arts if tiers.get(a.url) == "major"]
    briefs = [a for a in arts if tiers.get(a.url) != "major"]

    def run(group: list[Article], rules: str, is_major: bool) -> None:
        for i in range(0, len(group), chunk):
            part = group[i:i + chunk]
            blocks = []
            for j, art in enumerate(part, 1):
                others = [d for d in (art.duplicates or []) if d and d != art.source]
                extra = f"（同一事件另有报道：{'、'.join(others[:3])}）" if others else ""
                blocks.append(
                    f"[{j}] 栏目：{sec['name']}\n标题：{art.title}\n来源：{art.source}{extra}\n"
                    f"材料：{_clip(art.text or art.excerpt, 2000)}"
                )
            user = "\n\n".join(blocks) + "\n\n" + rules
            try:
                data = parse_json_loose(
                    call_llm(cfg, system_prompt(cfg), user, max_tokens=5000 if is_major else 2400)
                )
            except Exception:  # noqa: BLE001
                data = {}
            by_idx: dict[int, dict] = {}
            for entry in data.get("items", []):
                try:
                    k = int(entry.get("id")) - 1
                except (TypeError, ValueError):
                    continue
                if 0 <= k < len(part):
                    by_idx[k] = entry
            for k, art in enumerate(part):
                e = by_idx.get(k) or {}
                lede = str(e.get("lede") or "").strip()
                if is_major:
                    bl = _blocks_major(e)
                else:
                    paras = [str(x).strip() for x in (e.get("paras") or []) if str(x).strip()]
                    bl = [{"h": "", "p": p} for p in paras]
                if not bl:
                    rc = rule_content(art)
                    bl = [{"h": "", "p": p} for p in rc["paras"]]
                    lede = lede or rc.get("lede", "")
                out[art.url] = {
                    "tier": "major" if is_major else "brief",
                    "headline": str(e.get("headline") or art.title)[:40],
                    "lede": lede[:140],
                    "blocks": bl,
                    "keywords": [str(x)[:12] for x in (e.get("keywords") or [])][:4],
                }

    run(majors, MAJOR_RULES, True)
    run(briefs, BRIEF_RULES, False)
    return out


DEEP_RULES = """为下列每条新闻写「观察者视角」深度评论，四个部分：
1. background「事件背后」：解释这件事为什么会发生，背后的政治、经济、技术或社会机制。
2. impact「深层影响」：分别说明短期和长期影响，涉及国家、产业、社会和普通人。
3. perspectives「不同视角」：找出不同立场的合理解释——支持者、反对者、不同国家或群体、学界的争论。
   如果证据明显偏向一方，就直说，不要为了平衡强行五五开。
4. questions「值得思考」：1-2 个开放问题，能引导读者继续查资料、继续想。

写作纪律：
- 区分事实、推论、预测和价值判断；不确定的地方明确写「目前尚不确定」「这是推测」。
- 不要制造因果，不要用「必然」「注定」。
- 不要迎合读者的既有立场；如果常见看法有反例，把反例说出来。
- 不要使用「这标志着」「具有里程碑意义」这类空话。
- 语言清晰，高中生能读懂；专业概念首次出现时用一句话解释。
每部分 150-280 字。输出 JSON：{"items":[{"id":编号,"background":"","impact":"","perspectives":"","questions":["",""]}]}"""


def write_commentaries(arts: list[Article], summaries: dict[str, str], cfg: dict) -> dict[str, dict]:
    if not arts:
        return {}
    blocks = []
    for i, art in enumerate(arts, 1):
        blocks.append(
            f"[{i}] 标题：{art.title}\n来源：{art.source}\n"
            f"摘要：{(summaries.get(art.url) or _clip(art.text or art.excerpt, 400))}\n"
            f"正文节选：{_clip(art.text or art.excerpt, 900)}\n"
        )
    user = "\n".join(blocks) + "\n" + DEEP_RULES
    try:
        data = parse_json_loose(call_llm(cfg, system_prompt(cfg), user, max_tokens=8000))
    except Exception:  # noqa: BLE001
        return {}
    out: dict[str, dict] = {}
    for entry in data.get("items", []):
        try:
            idx = int(entry.get("id")) - 1
        except (TypeError, ValueError):
            continue
        if 0 <= idx < len(arts):
            out[arts[idx].url] = entry
    return out


# ---------------------------------------------------------------- 整体


OPENING_RULES = """根据下面各栏目的标题，写 2 句话（合计不超过 80 字）作为整期周报的开场白。
要求：指出本周最值得注意的一条主线，并把不同栏目的事件联系起来；
像懂行的朋友在跟你说话，不要罗列栏目，不要用「本周」「综上所述」开头。
输出 JSON：{"opening":"...","note":"不超过 12 字的主题词"}"""


def write_opening(digest_lines: list[str], cfg: dict) -> dict:
    user = "\n".join(digest_lines) + "\n\n" + OPENING_RULES
    try:
        data = parse_json_loose(call_llm(cfg, system_prompt(cfg), user, max_tokens=400))
        return {"opening": str(data.get("opening", "")).strip(), "note": str(data.get("note", "")).strip()}
    except Exception:  # noqa: BLE001
        return {"opening": "", "note": ""}


DEEP_DIVE_RULES = """从本周新闻里选一个值得深挖的问题，写成「本周深度观察」。它不应该是新闻复述，
而是一条理解世界的线索。要求：
- question：一个问题，不超过 30 字，具体、有张力，不要大而空；
- lead：150 字，说明为什么这个问题现在值得想；
- background：250-350 字，交代来龙去脉和关键概念（概念要解释，别默认读者懂）；
- timeline：4-6 个节点，每个 {"when":"年份或时间","what":"发生了什么，不超过 40 字"}；
- tensions：3-4 条核心矛盾，每条不超过 45 字，要具体（谁和谁、争什么）；
- views：3-4 个立场，{"stance":"立场名","claim":"这个立场怎么论证，80 字以内"}，
  必须包含相互对立的观点，不要伪造中间派；
- reading：3 条延伸阅读，{"title":"书名或文章名","author":"作者","why":"为什么读它，30 字以内"}，
  必须是真实存在的经典著作或公开报道，不确定就不要写；
- questions3：本周另外三个值得长期思考的问题，每个不超过 30 字。
输出 JSON：{"deep_dive":{...},"questions3":["","",""]}"""


def write_deep_dive(items: list[dict], cfg: dict) -> dict:
    lines = [f"- {it['headline']}：{it['summary'][:80]}" for it in items[:12]]
    user = "本周新闻：\n" + "\n".join(lines) + "\n\n" + DEEP_DIVE_RULES
    try:
        data = parse_json_loose(call_llm(cfg, system_prompt(cfg), user, max_tokens=4000))
        return {
            "deep_dive": data.get("deep_dive") or {},
            "questions3": data.get("questions3") or [],
        }
    except Exception:  # noqa: BLE001
        return {"deep_dive": {}, "questions3": []}


# ---------------------------------------------------------------- 降级


def rule_content(art: Article) -> dict:
    """没有模型时的兜底：切句成段，明确不是 AI 撰写的报道。"""
    sentences = split_sentences(art.text or art.excerpt)
    body = [s.strip() for s in sentences if s.strip()]
    paras, buf = [], ""
    for s in body:
        buf = (buf + " " + s).strip()
        if len(buf) >= 110:
            paras.append(buf)
            buf = ""
    if buf:
        paras.append(buf)
    paras = paras[:3] or [(art.excerpt or art.title)[:200]]
    return {
        "headline": art.title[:40],
        "lede": body[0][:120] if body else "",
        "paras": paras,
        "keywords": [],
    }
