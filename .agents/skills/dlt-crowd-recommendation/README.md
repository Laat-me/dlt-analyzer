# 大乐透网友推荐聚合 Skill

## 默认：自动发现参考网站

从公开 Bing HTML 搜索结果发现推荐网站，按域名去重，只保存网站清单：

```sh
python3 discover_websites.py 26117 --output data/sites.json --pages 2 --per-page 10 --max-sites 50
```

结果只包含域名、一个代表性 URL、命中过的查询词、目标期号、发现时间和统计计数；不会保存网页正文、作者、号码、搜索摘要或推荐记录。同一网站的多个页面会合并成一个域名条目。

搜索遇到验证码、登录、付费墙或反爬时安全失败，不绕过限制。网站数量不等于独立博主数量，更不等于预测准确率或中奖概率。

## Legacy：解析已保存的推荐文本

如果用户明确要求解析已有推荐文本，仍可使用：

```sh
python3 collect_recommendations.py raw_sources.jsonl --out-dir data
python3 aggregate_recommendations.py 26115 --input data/recommendations.jsonl --out-dir data/runs
python3 verify_recommendations.py --recommendations data/recommendations.jsonl
```

Legacy 流程支持完整 5+2、前区/后区胆码和号码池，并会写入来源及推荐记录；它不是默认的网站发现流程。测试 fixture 仅用于单元测试，不是实际博主数据。
