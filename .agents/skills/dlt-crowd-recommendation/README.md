# 大乐透网友推荐聚合 Skill

独立工具，不改变 `dlt-page/update.js` 正式预测。公开来源输入示例：

```sh
python3 collect_recommendations.py raw_sources.jsonl --out-dir data
python3 aggregate_recommendations.py 26115 --input data/recommendations.jsonl --out-dir data/runs
python3 verify_recommendations.py --recommendations data/recommendations.jsonl
```

原始公开来源须包含 URL、目标期号、发布时间或无法确认标记、推荐原文片段。支持完整 5+2，也支持前区胆码/大底号/号码池和后区胆码/四码/号码池；池类按较低权重参与边际投票，聚合器再补齐两注。运行时需在最终报告中说明来源数、去重后的独立簇数、两注及免责声明。`tests/fixtures.jsonl` 仅用于测试，不是实际博主数据。

**限制：** 当前仅实现离线解析和聚合，不含搜索引擎采集器。需由操作者通过公开搜索收集页面，再交给 CLI 处理；不会自动抓取网页，也不绕过登录或反爬。任何来源共识都不代表中奖概率增加。
