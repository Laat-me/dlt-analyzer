---
name: dlt-crowd-recommendation
description: Aggregate public online 大乐透 blogger and expert recommendations into two traceable 5+2 entertainment picks. Use whenever the user asks to search the web for lottery blogger picks, collect网友推荐, combine public prediction numbers, or summarize multiple sources. Preserve source URLs, deduplicate reposts, validate numbers, and never claim improved odds or profit.
---

# 大乐透网友推荐聚合

这个 skill 将公开网页上的网友/博主推荐整理成可追溯数据，再综合输出两注 5+2。默认入口是自动公开搜索并按域名保存网站清单；它是独立的娱乐参考模块，不修改 AI_U_wide、EVO-20、走势或玄学正式模型。

## 默认流程：自动发现网站

```sh
python3 discover_websites.py 26117 --output data/sites.json --pages 2 --per-page 10 --max-sites 50
```

默认只保存：域名、代表性 URL、命中查询词、目标期号、发现时间和统计计数；不保存网页正文、号码、作者或搜索摘要。按域名去重，同站多个页面合并查询词。遇到验证码、登录、付费墙或封锁时停止该查询并保留已有清单，不绕过限制。

- `site_schema.py`：URL 标准化、域名抽取、搜索结果过滤和按域名合并。
- `discover_websites.py`：自动公开搜索并写入 `data/sites.json`。
- `schemas.py`：Legacy 号码解析、校验和推荐记录。
- `collect_recommendations.py`：Legacy 离线推荐文本导入。
- `aggregate_recommendations.py`：Legacy 两注号码聚合。
- `verify_recommendations.py`：Legacy 开奖验证。
- `tests/`：网站发现与 Legacy 解析/聚合测试。
## 输入约定

采集器输入 JSONL 每行至少包含：

```json
{"platform":"公开搜索","author":"作者","title":"标题","url":"https://...","publishedAt":"2026-10-10","targetDrawNum":"26115","rawText":"大乐透26115期：前区 01 04 15 27 35，后区 03 06"}
```

若不能确认目标期号，必须标记 `parseStatus=rejected`，不能猜测。

## 聚合原则

- 只有 `exact_5_plus_2` 直接作为完整票投票；前区胆码、前区池、后区胆码和后区池按较低权重提供边际支持，再由聚合器补齐两注。
- 初始来源权重相同，不按自称专家、粉丝数或广告宣传自动加权。
- 同一正文、相同模板或号码完全相同的推荐归入同一 cluster，防止转载制造虚假共识。
- 第一注取边际分最高的合法组合；第二注对第一注号码增加重叠惩罚，保留独立高分号码。
- 只做轻量合法性约束（5 个不同前区 1–35、2 个不同后区 1–12）；奇偶、区间、和值只作可选多样性约束，不能宣称改变概率。
- 输出每个号码的来源数、独立 cluster 数、分数和来源 URL。

## 诚实边界

自动收集到的参考网站数量不等于独立博主数量，也不等于预测准确率。搜索结果可能重复转载、缺少号码或被搜索引擎改写；默认网站发现功能只建立后续检索的去重清单，不宣称提高中奖率或盈利能力。

## Legacy：推荐号码解析与聚合

只有用户明确要求解析已经保存的推荐文本时，才使用 `schemas.py`、`collect_recommendations.py`、`aggregate_recommendations.py` 和 `verify_recommendations.py`。这些旧工具支持完整 5+2、前区/后区胆码和号码池，但会另写推荐记录，不属于默认网站清单流程。
