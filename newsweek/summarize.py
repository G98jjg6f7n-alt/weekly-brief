"""精选、摘要与「观察者视角」：全部由大模型生成，失败逐级降级。"""
from __future__ import annotations

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


CURATE_RULES = """你是周报主编，要从本周几百条候选新闻里挑出 12-18 条真正值得读的。
判断标准，按权重从高到低：
1. 事件本身有多重要（影响范围、涉及多少人、是否改变规则）；
2. 对理解社会、经济、科技运行机制的帮助有多大；
3. 是否有长期影响，而不只是当天的热闹；
4. 信息是否可靠（官方文件、一手数据、专业媒体优先）。

坚决排除：
- 明星八卦、娱乐热搜、体育赛果（除非有超出比赛本身的意义）；
- 常规产品发布、价格促销、企业公关稿；
- 没有技术突破的「AI 新品」通稿；
- 同一事件的多篇重复报道（只留信息最全的一条）；
- 无实质内容的日常社会小新闻。

七个栏目是：world(世界与秩序)、china(中国与社会)、economy(经济与产业)、
tech(科技与未来)、industry(工业与设计)、thought(思想与文明)、nature(自然与人类)。

要求：
- 每个栏目至少 1 条，但不要为了填满而凑数；总数为 12-18 条。
- 保留 1-2 条读者兴趣之外、但确实有价值的「陌生领域」内容。
- importance：3 = 值得写深度评论；2 = 重要；1 = 值得一扫。
输出 JSON：{"picks":[{"id":编号,"section":"栏目key","importance":2}],"note":"一句话说明本期主线"}"""


def curate(sections: list[dict], pool: dict[str, list[Article]], cfg: dict) -> tuple[list[dict], str]:
    """让模型从候选池里挑条目。失败返回空，由调用方退回本地排序。"""
    lines: list[str] = []
    index: dict[int, tuple[str, Article]] = {}
    n = 1
    for sec in sections:
        arts = pool.get(sec["key"], [])[:22]
        for art in arts:
            index[n] = (sec["key"], art)
            lines.append(
                f"#{n} [{sec['key']}] {_clip(art.title, 60)} | {art.source} | {_clip(art.excerpt, 90)}"
            )
            n += 1
    if not lines:
        return [], ""
    user = (
        CURATE_RULES
        + "\n\n候选列表（编号 | 栏目 | 标题 | 来源 | 摘要）：\n"
        + "\n".join(lines)
    )
    try:
        data = parse_json_loose(call_llm(cfg, system_prompt(cfg), user, max_tokens=3000))
    except Exception:  # noqa: BLE001
        return [], ""
    picks: list[dict] = []
    seen: set[str] = set()
    for p in data.get("picks", []):
        try:
            idx = int(p.get("id"))
        except (TypeError, ValueError):
            continue
        if idx not in index:
            continue
        sec_key, art = index[idx]
        if art.url in seen:
            continue
        seen.add(art.url)
        picks.append(
            {
                "article": art,
                "section": p.get("section") if p.get("section") in {s["key"] for s in sections} else sec_key,
                "importance": max(1, min(3, int(p.get("importance", 2)))),
            }
        )
    return picks, str(data.get("note", "")).strip()


# ---------------------------------------------------------------- 单条写作


WRITE_RULES = """为下列每条新闻写一篇由你撰写的报道——不是摘要，也不是评论。

- headline：不超过 22 字，具体（主体 + 动作 + 关键信息），不用问句和夸张词；
- lede：1 句话、30-50 字，把最重要的事实一次说清（谁、做了什么、关键数字）；
- paras：3 段，每段 80-140 字：
  1) 发生了什么：事实、数字、时间地点，可用原文里的直接引语；
     （注意：第一段不要重复 lede 已经说过的信息，直接进入细节）
  2) 为什么会这样：背景、机制、各方动机；
  3) 这意味着什么：影响与不确定性，短长期分开讲；
- keywords：3-4 个中文关键词，用于检索。

写作纪律：
- 只能使用材料里出现的事实和数字，不得编造；材料没说的，写「目前尚不确定」；
- 事实是骨架，判断要有依据；不要写成社论，也不要复述通稿；
- 如果材料来自不同立场的媒体，指出报道口径的差异；
- 语言清楚，高中生能读懂；专业概念第一次出现用一句话解释。
输出 JSON：{"items":[{"id":编号,"headline":"","lede":"","paras":["","",""],"keywords":[]}]}"""


def write_items(sec: dict, arts: list[Article], cfg: dict, chunk: int = 3) -> dict[str, dict]:
    """让模型为每条新闻写一篇报道；分块调用以免单次输出过长。"""
    out: dict[str, dict] = {}
    for i in range(0, len(arts), chunk):
        part = arts[i:i + chunk]
        blocks = []
        for j, art in enumerate(part, 1):
            others = [d for d in (art.duplicates or []) if d and d != art.source]
            extra = f"（同一事件另有报道：{'、'.join(others[:3])}）" if others else ""
            blocks.append(
                f"[{j}] 栏目：{sec['name']}\n标题：{art.title}\n来源：{art.source}{extra}\n"
                f"材料：{_clip(art.text or art.excerpt, 1600)}"
            )
        user = "\n\n".join(blocks) + "\n\n" + WRITE_RULES
        try:
            data = parse_json_loose(call_llm(cfg, system_prompt(cfg), user, max_tokens=4200))
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
            paras = [str(x).strip() for x in (e.get("paras") or []) if str(x).strip()]
            lede = str(e.get("lede") or "").strip()
            if not paras:
                rc = rule_content(art)
                paras, lede = rc["paras"], rc.get("lede", "")
            out[art.url] = {
                "headline": str(e.get("headline") or art.title)[:40],
                "lede": lede[:140],
                "paras": [p[:400] for p in paras[:4]],
                "keywords": [str(x)[:12] for x in (e.get("keywords") or [])][:4],
            }
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
