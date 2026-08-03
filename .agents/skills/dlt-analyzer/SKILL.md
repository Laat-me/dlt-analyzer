---
name: dlt-analyzer
description: >
  大乐透历史数据分析与预测，支持持续跟踪和自我优化。
  当用户提到大乐透、DLT、体彩选号、彩票预测、大乐透分析、
  历史开奖统计、号码推荐、对比开奖结果、模型优化等关键词时触发。
  自动管理本地数据文件，首次拉取全量历史，后续增量追加。
  每次执行自动 Git 同步数据文件。双模型（v1追冷/v2追热）对比预测。
---

# 大乐透持续分析与预测系统

## 重要声明

大乐透每期开奖为独立随机事件，历史数据不能真正预测未来结果。
本技能仅供统计娱乐，不构成投注建议。

---

## 双模型架构

系统同时运行两套独立模型，互为对照：

| 模型 | 核心策略 | 适用场景 |
|------|---------|---------|
| **v1 追冷** | gap×0.5 + cold30×2.5 + freq×0.3 | 冷号集中回补时 |
| **v2 追热** | f5×3 + f10×1.5 + neighbor×4 + streak×4 | 热号扎堆连出时 |

每次预测输出两个模型的对比，并追踪各自的命中率。

---

## 执行流程

### 步骤 0：Git 同步拉取（开始前）

```bash
cd <项目根目录> && git pull origin main --rebase 2>/dev/null || echo "pull skipped"
```

### 步骤 1：读取本地数据

检查 `data/` 目录。`draws.json` 不存在 -> 首次初始化模式，必须建立最近 1000 期的本地全量历史库。

### 步骤 2：数据获取

API: `https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85&provinceId=0&pageSize=100&termNum={lastNum}&isSpecial=0`

必须在 `lottery.gov.cn` 域名下通过页面上下文调用。每批 100 条，间隔 400-500ms。

若 `draws.json` 不存在，首次初始化必须优先补齐最近 1000 期；可直接使用官方历史开奖页分页抓取，按表格中的完整开奖行过滤，剔除“派奖”等附加说明行后落库。

若官方接口临时限流或分页被拦截，优先保留本地 `draws.json` 历史库，只追加最新开奖，避免因为全量拉取失败导致本次分析中断。

发现有新期号时自动触发步骤 4 对比。

### 步骤 3：双模型预测

#### 共同统计
- 频次分布（全期 / 近5期 / 近10期 / 近30期）
- 遗漏值
- 奇偶比分布（近50期）
- 和值分布（近100期，均值 ± 标准差）
- 区间分布（低1-12 / 中13-24 / 高25-35）

#### v1 评分（追冷）
```
前区 score = gap×0.5 + (5-freq30)×2.5 + (N/7-freq)×0.3
后区 score = gap×0.6 + (3-freq30)×2
```
高分 = 遗漏久 + 近期冷 + 全期偏冷。选号约束：奇偶2:3或3:2、区间1-2:1-2:1-2、和值±1σ、全距≥15、热号≥2 + 冷号≥1。

#### v1 实现注意
`gap` 计算必须显式判断 `=== undefined`，不能写成 `if (!gap[i])`。
否则刚开出的号码会因为 `0` 被当成 falsy 而误判成最大遗漏值，直接污染 v1 排序结果。

#### v2 评分（追热）
```
前区 score = freq5×3 + freq10×1.5 + neighborBonus×4 + streakBonus×4
后区 score = freq5×3 + freq10×1.5
```
- `freq5` = 近5期出现次数
- `freq10` = 近10期出现次数
- `neighborBonus` = 号码处于近5期热号的 ±1 邻域内 -> +4
- `streakBonus` = 近5期出现 >= 2 次 -> +4

高分 = 近期频繁出现 + 处于热区附近 + 连续出现。

v2 选号约束与 v1 相同（奇偶比、区间、和值等）。

#### 输出格式
```
## 26085 期预测

| | v1 追冷 | v2 追热 |
|--|--------|--------|
| 前区 | XX XX XX XX XX | XX XX XX XX XX |
| 后区 | XX XX | XX XX |
| 策略 | 追遗漏 | 追热区 |

### v1 选号理由
[每个号码的依据]

### v2 选号理由
[每个号码的依据]
```

### 步骤 4：结果对比

新开奖出现时：
1. 找到预测记录中未验证的条目
2. 分别计算 v1 和 v2 的命中数
3. 更新 `model.json` 中各模型独立的 `performance` 统计
4. 输出对比表格：

```
## 上期对比

| 模型 | 预测 | 前区命中 | 后区命中 |
|------|------|---------|---------|
| v1 | XX XX XX XX XX + XX XX | N/5 | N/2 |
| v2 | XX XX XX XX XX + XX XX | N/5 | N/2 |
```

5. 按学习率 0.05 独立调整各模型权重

### 步骤 5：保存预测记录

追加到 `predictions.json`，每条记录增加 `model` 字段区分 v1/v2。
若 `draws.json` 已存在，则本次同步后必须更新 `updatedAt`、`latest` 和 `draws` 列表，保证本地历史库可直接复用。

### 步骤 6：Git 提交并推送

```bash
cd <项目根目录>
git add .agents/skills/dlt-analyzer/data/
git commit -m "update: $(date +%Y-%m-%d) v1+v2双模型预测"
git push origin main
```

注意：`draws.json` 属于技能的持久化历史库，不是临时缓存。只要被初始化出来，就必须和 `model.json`、`predictions.json` 一起提交到仓库。

---

## model.json 结构

```json
{
  "version": 2,
  "models": {
    "v1": {
      "weights": {"gap": 0.30, "frequency": 0.25, "recentTrend": 0.25, "interval": 0.10, "oddEven": 0.10},
      "performance": {"totalPredictions": 0, "frontHits": {...}, "backHits": {...}}
    },
    "v2": {
      "weights": {"freq5": 0.40, "freq10": 0.25, "neighbor": 0.20, "streak": 0.15},
      "performance": {"totalPredictions": 0, "frontHits": {...}, "backHits": {...}}
    }
  }
}
```

---

## 用户指令速查

| 用户说 | 执行 |
|--------|------|
| 分析大乐透 / 推荐号码 | 全流程 0->1->2->3->5->6 |
| 对比上次结果 | 仅步骤 4 |
| v1/v2 哪个准 | 输出两模型累计命中率对比 |
| 只用 v1 / 只用 v2 | 跳过另一模型 |
| 偏冷门推荐 | v1 的 gap 权重 +50% |
| 偏热门推荐 | v2 的 freq5 权重 +50% |
