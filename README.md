# WEEKLY BRIEF · 每周新闻周报

每周五晚自动生成的一份中文周报，覆盖 **AI、汽车、数码、摄影** 四个方向。
英文来源配英文原句 + 中文翻译，句句对照，顺便练英语。

- 输出是一份**自包含 HTML**：不依赖外网字体、图片和脚本，断网也能看，手机上也好看
- 生成逻辑**零第三方依赖**，只用 Python 标准库（不需要 pip install）
- 大模型不可用时自动降级为规则摘要，**每周一定有东西可看**

---

## 一、它是怎么跑起来的

```
抓取(24 个 RSS 源) → 关键词分流 → 去重聚类 → 打分排序
      → 抓取正文 → 大模型写摘要(失败则规则兜底) → 生成 HTML → 归档
```

> **2026-11-06 更新**：GitHub 的 `schedule` 定时器在这台仓库上实测**完全不触发**
> （6 天 0 次；把 cron 改成每 5 分钟，11 分钟仍 0 次）。所以主链路改成了
> **本机 launchd 每周五 21:00 生成并推送 + 推送触发云端部署**，云端 cron 保留为兜底。
> 本机任务的安装：`./install_schedule.sh`（卸载 `--remove`）。

云端的原理（你问的那个问题）：

1. 代码放在你的 GitHub 仓库里；
2. GitHub Actions 是一台**免费租用的临时服务器**，按 cron 表达式定时醒来
   （`0 13 * * 5` = 每周五 UTC 13:00 = 北京时间 21:00）；
3. 它 checkout 你的代码 → 装 Python → 跑 `run.py` → 生成 `site/` 目录；
4. 生成的静态文件被推到 GitHub Pages，得到一个固定网址，手机随时能打开；
5. 跑完服务器立刻销毁，下周五再租一台新的。

所以：**不需要你的 Mac 开机**，不需要买服务器。代价是仓库必须是公开的
（Pages 免费版只支持公开仓库），代码本身不含任何密钥——密钥放在
仓库 Settings → Secrets 里，只有 Actions 运行时才注入。

## 二、成本

用 `deepseek-flash`：每周输入约 2 万 token、输出约 5 千 token，
周五 21:00 是错峰时段（价格减半），**一周大约 0.05 元，一个月不到 3 毛钱**。
GitHub Actions 对公开仓库免费，Pages 托管免费。

## 三、占多少空间

| 项目 | 大小 |
|---|---|
| 程序本体（含全部源码） | 约 200 KB |
| 每期周报（HTML + 数据） | 约 75 KB |
| 一年 52 期 | 约 4 MB |
| 第三方依赖 | **0**（没有 node_modules，没有虚拟环境，不用 pip install） |

所有历史都存在 `site/data/` 里，攒五年也才 20 MB。

## 四、部署（约 10 分钟，一次性）

1. 在 GitHub 建一个**公开**仓库（比如 `weekly-brief`），把本项目推上去。
   如果懒得敲命令，直接用脚本（会问你用户名和仓库名，然后打印剩下三步）：

   ```bash
   ./deploy.sh 你的用户名 weekly-brief
   ```

   或者手动：

   ```bash
   git init -b main && git add . && git commit -m "init"
   git remote add origin https://github.com/你的用户名/weekly-brief.git
   git push -u origin main
   ```

2. 去 <https://platform.deepseek.com> 创建 API Key（充 10 元能用很久）。

3. 仓库 → Settings → Secrets and variables → Actions → New repository secret：
   - `DEEPSEEK_API_KEY` = 你的 key

4. 仓库 → Settings → Pages → Build and deployment → Source 选 **GitHub Actions**。

5. 仓库 → Actions → 左侧 `weekly-brief` → **Run workflow** 手动跑一次。
   跑完 Pages 会给出网址，形如 `https://你的用户名.github.io/weekly-brief/`。

之后每周五 21:00 自动更新；想立刻看就当周手动点一次 Run workflow。

> **国内访问 Pages 偶尔会慢。** 如果打不开，把仓库导入 Cloudflare Pages
> （免费，构建命令 `python3 run.py --no-open`，输出目录 `site`），
> 或者在自己的 VPS 上 `git pull` 后用 Nginx 托管 `site/` 目录。

## 五、本地使用

```bash
python3 run.py                  # 生成本周周报并自动打开（第一次会花 30~60 秒）
python3 run.py --serve          # 生成后起本地服务，手机连同一 WiFi 也能看
python3 run.py --no-llm         # 没有 key 时，纯规则摘要
python3 run.py --only ai,photo  # 只跑两个板块，结果写到 site/preview/，不影响正式站点
```

macOS 上也可以直接双击 `run.command`。同一周重复运行会**直接打开已生成的那一期**（0.2 秒），
想重新抓一遍就加 `--force`。

想让 Mac 自己每周五 21:00 生成一份（不依赖云端）：

```bash
./install_schedule.sh          # 装到 launchd，睡眠错过会在唤醒后补跑
./install_schedule.sh --remove # 卸载
```

把 key 写进项目根目录的 `.env`（已在 .gitignore 里，不会被提交）：

```bash
DEEPSEEK_API_KEY=sk-xxxxxxxx
```

## 六、推送到手机（可选）

生成完会自动推送，在 `config.json` 的 `notify` 里填，或用环境变量：

| 方式 | 配置 | 说明 |
|---|---|---|
| **Bark**（iOS，推荐） | `BARK_URL` | App Store 搜 Bark，装上后它给你一个 `https://api.day.app/xxx` 地址，粘进来即可，免费、无广告 |
| **Server 酱**（微信） | `SERVERCHAN_KEY` | <https://sct.ftqq.com> 扫码拿 key，微信里直接收 |
| **自定义 webhook** | `WEBHOOK_URL` | POST `{title,text,url,week}`，可以接飞书/钉钉机器人 |

另外，手机浏览器打开周报网址后「添加到主屏幕」，就是一个全屏的类 App 体验。

## 七、改配置

全部在 `config.json`：

| 想改什么 | 改哪里 |
|---|---|
| 加/删新闻源 | `sections[].sources[]`，字段 `name` `url` `lang` `weight` |
| 综合源自动分流 | 源里加 `"route": true`，文章会按 `route_keywords` 自动归类（IT之家、爱范儿就是这么把汽车/摄影文章送过去的） |
| 分流的误判 | 板块加 `route_exclude`，标题里出现这些词就不往这个板块搬（摄影板块排除了「电影」「游戏」，不然《沙丘 3》预告会跑进来） |
| 只要某个栏目 | 删掉对应 section，或源里加 `"disabled": true` |
| 篇幅 | `per_section.detailed`（详读条数）/ `brief`（速览条数） |
| 时间范围 | `window_days`（默认 8 天） |
| 换模型 | `llm.model`、`llm.base_url`；任何 OpenAI 兼容接口都能用，也可以用环境变量 `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL` 临时覆盖 |
| 标题 | `title` |

## 八、可靠性是怎么保证的

- **零依赖**：只用标准库，不会因为 `pip install` 失败、虚拟环境损坏而跑不起来
- **多源冗余**：每个板块 3~8 个源，单个源挂掉只降权，不会让整期失败
- **正文抓取失败 → 退回 RSS 摘要**；**大模型失败 → 退回规则摘要**
- **跨源查重**：同一事件被 5 家报道只留一条（大模型判断，失败则跳过）
- **来源配额**：单一媒体最多占 3 条，避免整期被一家刷屏
- **自检**：生成后检查板块完整性、条目数、页面大小、源站成功率，异常会在日志里告警
- **归档**：每期数据存 `site/data/YYYY-Www.json`，页面坏了可以随时从数据重新渲染
- **隔离**：调试参数 `--only` 只写 `site/preview/`，不会覆盖正式周报和归档
- **回归测试**：仓库自带 `selftest` Action，每次 push 用无密钥模式跑一遍完整流程，改代码改坏了当场发现

## 九、目录结构

```
config.json              所有配置（源、板块、篇幅、模型）
run.py                   命令行入口
run.command              macOS 双击运行
newsweek/
  fetch.py               RSS/Atom 抓取与容错解析
  extract.py             文章正文提取（轻量 readability）
  cluster.py             跨源去重聚类
  rank.py                打分排序（权重/热度/新鲜度/质量）
  summarize.py           大模型摘要 + 规则兜底 + 跨板块查重
  render.py              HTML 渲染（手机优先、明暗主题）
  notify.py              推送
  pipeline.py            主流程
site/                    生成结果（index.html 是最新一期）
.github/workflows/weekly.yml   云端定时任务
```

## 十、常见问题

**没配 key 会怎样？** 照样生成，只是条目变成「标题 + 摘录」，英文没有翻译，
页面顶部会标「规则摘要」。

**模型写错了怎么办？** 摘要里的英文原句会和原文逐字比对，对不上就丢掉英文只留中文，
不会出现编造的引语。

**能改成只看某个板块吗？** `per_section` 里把详读调成 0，或者直接删 section。

**周报里为什么有英文标题？** 没配 key 时规则摘要无法翻译；配了 key 就有中文小标题。
