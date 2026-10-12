# 大乐透网友推荐聚合 Skill

## 默认入口：完整搜索到聚合流水线

```sh
python3 run_pipeline.py 26116 --output data/runs --pages 1 --per-page 10 --max-sites 30
```

它会搜索公开页面、逐页提取可见文本中的完整 5+2、前区池、后区池和胆码，按票面/内容聚类去重并生成两注。网页正文只在本次运行的临时目录内处理，长期输出只保存网站清单和运行聚合结果。遇到搜索噪声、验证码或无法确认目标期号时，报告 `insufficient_evidence`，不凑号码。

## 网站清单模式

```sh
python3 discover_websites.py 26116 --output data/sites.json --pages 2 --per-page 10 --max-sites 50
```

按域名保存代表性页面和命中过的查询词，不保存网页正文、作者、搜索摘要或号码。

## Legacy：解析已保存推荐文本

只有用户明确要求解析已有推荐文本时使用 `collect_recommendations.py`、`aggregate_recommendations.py`、`verify_recommendations.py`。这些工具支持完整 5+2、前区/后区胆码和号码池，会写推荐记录，不属于默认搜索流水线。

**限制：** 仅访问公开页面，不绕过登录、验证码、付费墙或反爬；网站/博主数量和号码共识不代表中奖率提高。
