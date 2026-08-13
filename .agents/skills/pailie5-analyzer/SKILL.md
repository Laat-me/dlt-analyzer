---
name: pailie5-analyzer
description: >
  体彩排列五历史数据分析与预测，支持持续跟踪和自我优化。
  当用户提到排列五、排列5、P5、体彩排列五、选号、号码推荐等关键词时触发。
  自动管理本地数据文件，首次拉取全量历史，后续增量追加。
  每次执行自动 Git 同步数据文件。以 5 注组合全中为主目标，统计/概率模型提供候选。
---

# 排列五持续分析与预测系统

## 重要声明

排列五每期开奖为独立随机事件，历史数据不能真正预测未来结果。
本技能仅供统计娱乐，不构成投注建议。

---

## 玩法与命中定义

- 每期开出 5 个位置，每位数字 0-9，开奖结果为 5 位数（如 `8 3 9 4 3`）
- **线上主目标**：每期输出 5 注候选，尽量让这 5 注中至少 1 注与实际 5 位号码完全一致
- `exactHit = 1`：5 注中任意 1 注与实际号码完全一致
- `exactHitCount`：本期完全命中的注数，通常为 0 或 1
- **辅助指标**：位置命中率、Top-2 覆盖率、票组多样性
- 单注随机全中概率为 `1/100000`，5 注理论基线约 `0.005%/期`，因此出现长期 0 次全中并不代表实现错误

---

## 概率模型与组选算法

系统分两层工作：

1. **第一层：位置概率建模**
2. **第二层：从高概率候选中选 5 注组合**

### 第一层：位置概率模型

| 算法 | 核心策略 | 作用 |
|------|---------|------|
| **A_freq30** | 每位按近30期频次排序 | 基线热号法 |
| **H_dirichlet_positional** | Dirichlet 平滑每位频率 | Bayesian 低方差基线 |
| **I_recency_eb** | 递减加权经验贝叶斯 | 轻度近期漂移 |
| **J_markov_mixed** | 一阶 Markov 与频率基线混合 | 捕捉短记忆结构 |
| **K_prob_ensemble** | H/I/J 等权概率集成 | 当前默认主算法 |

当前默认主算法：
```text
K_prob_ensemble = (H_dirichlet_positional + I_recency_eb + J_markov_mixed) / 3
```

### 第二层：5 注组合算法

| 组合算法 | 策略 |
|---------|------|
| **P1_prob_top5** | 直接取联合概率最高的 5 注 |
| **P2_diverse_prob5** | 概率优先 + 票组多样性约束 |
| **P3_ensemble_portfolio** | 基于 K_prob_ensemble 生成 5 注 |
| **P4_low_crowd_portfolio** | 概率优先 + 低拥挤度惩罚 |

### 低拥挤度方向

在无真实投注数据时，用简单代理规则减少“大众爱买”模式：
- 惩罚过多 `8/6/9`
- 惩罚全相同、回文、ABABA、明显连号/顺子
- 惩罚过度重复
- 惩罚明显日期感低位结构（如过多 `0-3`）

这层只影响最终选票，不改变开奖概率本身。

---

## 评估口径

### 主指标：5 注任一全中率
- **训练段**：前 900 期
- **留出集**：后 100 期
- `trainAnyExactHitRate = 训练段中有至少 1 注全中的期数 / 训练期数`
- `holdoutAnyExactHitRate = 留出集有至少 1 注全中的期数 / 100`

### 辅助指标
- `ticketExactRate = 完全命中的注数 / 总注数`
- `top2Coverage = 实际数字落入每位 Top-2 候选集合的比例`
- `positionHitRate = 单位置主推命中率`

### 重要原则
- 算法选择只能看前 900 期；后 100 期只做最终验证
- 不允许反复看同一后 100 期结果调到过拟合
- 若无任何方法在留出集上全中，必须如实记录 `0`，不伪造达标结果

---

## 执行流程

### 步骤 0：Git 同步拉取（开始前）

```bash
cd <项目根目录> && git pull origin main --rebase 2>/dev/null || echo "pull skipped"
```

远端仓库的正式写操作统一走已配置好的 GitHub MCP（使用用户自己的 key），不要再默认依赖本地 `git push`。本地 `git commit` 只可作为临时备份，正式提交与推送以 MCP 结果为准。

### 步骤 1：读取本地数据

检查 `data/` 目录。`draws.json` 不存在 -> 首次初始化模式，必须至少建立最近 1000 期的本地全量历史库；初始化完成后后续只做累计追加，不删除旧记录。

### 步骤 2：数据获取

API: `https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=350133&provinceId=0&pageSize=100&termNum={termNum}&isSpecial=0`

- `gameNo=350133` 为排列五专属编号
- 返回 `lotteryDrawResult` 形如 `8 3 9 4 3`，解析为 5 位数字数组
- 分页：用 `pageNo` 参数翻页（每批 100 期，`pageNo=1` 为最新一期起），拉取直到满 1000 期；每批间隔 400-500ms
- 注意：`termNum` 参数在排列五接口上不生效（始终返回最新页），必须用 `pageNo` 翻页

若 `draws.json` 已存在，后续同步一律采用累计追加模式：只补新期号，不因样本上限裁剪或删除旧期号。

### 步骤 3：900/100 回测与 5 注生成

#### 共同统计
- 每位频次分布（全期 / 近10期 / 近30期）
- 每位 Markov 转移计数
- 每位递减加权频次
- 票组相似度与 crowd penalty

#### 回测框架
- 前 900 期训练、后 100 期留出
- 训练段允许 30 期窗口做稳定性观察
- 最终选用 `holdoutAnyExactHitRate` 最优的组合算法；若并列，再看训练段 exact-hit 与辅助指标

#### 输出格式
```text
## 26214 期 5注推荐

1. X X X X X
2. X X X X X
3. X X X X X
4. X X X X X
5. X X X X X

### 低拥挤度参考
1. X X X X X
2. X X X X X
3. X X X X X
4. X X X X X
5. X X X X X

### 算法说明
- 位置概率模型: K_prob_ensemble
- 组选算法: P3_ensemble_portfolio / P4_low_crowd_portfolio
- 900/100 留出结果: XX
```

### 步骤 4：结果对比

新开奖出现时：
1. 找到预测记录中未验证的条目
2. 用 `actualDigits` 与该期的 5 注逐一比较
3. 更新：
   - `matchedTicketIndexes`
   - `exactHitCount`
   - `anyExactHit`
   - 辅助的 `positionHits`
4. 更新 `model.json` 中当前组合算法的 `performance`
5. 输出对比：

```text
## 上期对比

实际: X X X X X
命中票号: 无 / [2]
是否全中: 否 / 是
```

### 步骤 5：保存预测记录

追加到 `predictions.json`，新记录以 `tickets` 为主：
- `tickets`: 5 注组合
- `probabilityPortfolio`: 概率优先 5 注
- `lowCrowdPortfolio`: 低拥挤度 5 注
- `matchedTicketIndexes`, `exactHitCount`, `anyExactHit`
- 可保留 `predictedDigits` / `top2` 兼容旧记录，但不再作为主结构

若 `draws.json` 已存在，则本次同步后必须更新 `updatedAt`、`latest` 和 `draws` 列表；已有 `draws` 只能追加新数据，不得滚动删除旧记录。

### 步骤 6：Git 提交并推送

默认使用已配置好的 GitHub MCP 直接提交到远端仓库，不再把本地 `git push` 作为常规路径。

推荐顺序：
1. 用本地文件操作完成 `data/` 内更新
2. 校验 `model.json`、`predictions.json`、`draws.json` 的一致性
3. 通过 GitHub MCP 将变更直接写入 `main`
4. 本地仓库如需保留同步历史，再单独做 `pull --rebase`

若必须保留本地命令示例，仅作为兜底，不作为默认流程：

```bash
cd <项目根目录>
git add .agents/skills/pailie5-analyzer/data/
git commit -m "update: $(date +%Y-%m-%d) 排列五5注组合预测"
git push origin main
```

注意：`draws.json` 属于技能的持久化历史库，不是临时缓存。只要被初始化出来，就必须和 `model.json`、`predictions.json` 一起提交到仓库。

---

## model.json 结构

```json
{
  "version": 3,
  "optimizationTarget": "5-ticket exact-hit",
  "activeAlgorithm": "K_prob_ensemble",
  "activePortfolioAlgorithm": "P3_ensemble_portfolio",
  "models": {
    "m1": {
      "strategy": "概率建模 + 5注组合",
      "weights": {"alpha": 1.0, "gamma": 0.995, "markovWeight": 0.35},
      "performance": {"totalPredictions": 0, "hits": {"0": 0, "1": 0}, "avgAnyExactHitRate": 0.0}
    }
  },
  "portfolioBenchmarks": [
    {"name": "P3_ensemble_portfolio", "trainAnyExactHitRate": 0.0, "holdoutAnyExactHitRate": 0.0}
  ]
}
```

---

## 用户指令速查

| 用户说 | 执行 |
|--------|------|
| 分析排列五 / 推荐号码 | 全流程 0->1->2->3->5->6 |
| 对比上次结果 | 仅步骤 4 |
| 排列五全中率 | 输出 5 注任一全中率 |
| 多给几注 | 仍按默认 5 注组合 |
| 偏少人买 | 输出 lowCrowdPortfolio 作为第二组参考 |
