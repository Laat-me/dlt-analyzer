---
name: dlt-crowd-recommendation
description: Aggregate public online 大乐透 blogger and expert recommendations into two traceable 5+2 entertainment picks. Use whenever the user asks to search the web for lottery blogger picks, collect网友推荐, combine public prediction numbers, or summarize multiple sources. Preserve source URLs, deduplicate reposts, validate numbers, and never claim improved odds or profit.
---

# 大乐透网友推荐聚合

这个 skill 将公开网页上的网友/博主推荐整理成可追溯数据，再综合输出两注 5+2。它是独立的娱乐参考模块，不修改 AI_U_wide、EVO-20、走势或玄学正式模型。

## 标准流程

1. 确定目标期号和采集截止时间；未指定时从本地 `draws.json` 推算下一期。
2. 使用公开搜索查询多个关键词与多个平台，尽量收集至少 20 个候选页面；不要绕过登录、验证码、付费墙或反爬限制。
3. 保存来源标题、作者/账号、平台、URL、发布时间、抓取时间、目标期、原文摘录和内容哈希。
4. 用 `schemas.py` 解析完整 5+2、前区池、胆码、后区池和杀号；验证号码范围、数量、重复和期号。
5. 按 URL、正文哈希、作者/标题模板和号码指纹去重；转载只算一个独立来源簇。
6. 用 `aggregate_recommendations.py` 按来源簇、解析置信度、时间衰减和边际投票生成两注，并保留每个号码的来源证据。
7. 用 `verify_recommendations.py` 在开奖后根据官方 `draws.json` 验证，不回填开奖后的来源。
8. 输出运行报告：来源总数、独立簇、有效完整票、拒绝数、两注、证据来源、随机基线和免责声明。

## 文件

- `schemas.py`：纯解析、校验、标准化、来源指纹。
- `collect_recommendations.py`：读取搜索/网页采集 JSONL，解析并写入来源与推荐记录；不负责绕过网站限制。
- `aggregate_recommendations.py`：生成两注和报告。
- `verify_recommendations.py`：按官方开奖验证历史推荐。
- `tests/`：解析与聚合单元测试。
- `data/sources.jsonl`：原始来源审计记录。
- `data/recommendations.jsonl`：规范推荐记录。
- `data/runs/`：按期号保存聚合报告。

## 输入约定

采集器输入 JSONL 每行至少包含：

```json
{"platform":"公开搜索","author":"作者","title":"标题","url":"https://...","publishedAt":"2026-10-10","targetDrawNum":"26115","rawText":"大乐透26115期：前区 01 04 15 27 35，后区 03 06"}
```

若不能确认目标期号，必须标记 `parseStatus=rejected`，不能猜测。

## 聚合原则

- 只有 `exact_5_plus_2` 直接作为完整票投票；池类推荐只提供边际支持。
- 初始来源权重相同，不按自称专家、粉丝数或广告宣传自动加权。
- 同一正文、相同模板或号码完全相同的推荐归入同一 cluster，防止转载制造虚假共识。
- 第一注取边际分最高的合法组合；第二注对第一注号码增加重叠惩罚，保留独立高分号码。
- 只做轻量合法性约束（5 个不同前区 1–35、2 个不同后区 1–12）；奇偶、区间、和值只作可选多样性约束，不能宣称改变概率。
- 输出每个号码的来源数、独立 cluster 数、分数和来源 URL。

## 诚实边界

公开推荐聚合只能反映“网上意见”，不是独立开奖信息。重复转载不是多个独立证据；没有历史冻结采集记录时，不得声称某博主长期更准；不得声称两注提高中奖率、回报率或盈利概率。
