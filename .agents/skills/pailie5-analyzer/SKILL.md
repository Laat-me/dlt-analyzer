---
name: pailie5-analyzer
description: >
  体彩排列五历史数据分析与预测，支持持续跟踪和自我优化。
  当用户提到排列五、排列5、P5、体彩排列五、选号、号码推荐等关键词时触发。
  自动管理本地数据文件，首次拉取全量历史，后续增量追加。
  每次执行自动 Git 同步数据文件。统计/概率模型用于单注推荐。
---

# 排列五持续分析与预测系统

## 重要声明

排列五每期开奖为独立随机事件，历史数据不能真正预测未来结果。
本技能仅供统计娱乐，不构成投注建议。

---

## 玩法与命中定义

- 每期开出 5 个位置，每位数字 0-9，开奖结果为 5 位数（如 `8 3 9 4 3`）
- **线上主目标**：每期输出 1 注主推号码
- **主评估指标**：Top-2 候选覆盖率（每位给 2 个候选，实际数字落入集合即计 1 分）
- **辅助指标**：单位置主推命中率、整组 5 位全中次数
- 单注随机全中概率为 `1/100000`，长期 0 次全中并不代表实现错误

---

## 候选算法架构

系统维护一组可比较的候选算法，统一按 **900/100 留出集 Top-2 候选覆盖率** 评估：

| 算法 | 核心策略 | 作用 |
|------|---------|------|
| **A_freq30** | 每位按近30期频次排序 | 基线热号法 |
| **B_freq30+10** | `freq30×2 + freq10×0.8` | 30期热度为主 |
| **C_freq30+10+all** | `freq30×2 + freq10×0.8 + freqAll×0.1` | 加入轻微全期热度 |
| **D_current_m1** | 旧公式 `gap×0.5 + freq5×1.5 + freq10×0.8 + (100-freqAll)×0.3` | 回测对照 |
| **E_freq10** | 每位按近10期频次排序 | 短窗口热号法 |
| **F_freq5** | 每位按近5期频次排序 | 极短窗口热号法 |
| **G_freq30_only_all** | `freq30 + freqAll×0.01` | 稳定热号法 |
| **H_dirichlet_positional** | Dirichlet 平滑每位频率 | Bayesian 低方差基线 |
| **I_recency_eb** | 递减加权经验贝叶斯 | 轻度近期漂移 |
| **J_markov_mixed** | 一阶 Markov 与频率基线混合 | 捕捉短记忆结构 |
| **K_prob_ensemble** | H/I/J 等权概率集成 | 当前默认主算法 |

### 当前默认算法

```text
K_prob_ensemble = (H_dirichlet_positional + I_recency_eb + J_markov_mixed) / 3
```

- 900/100 留出集 **Top-2 覆盖率：22.0%**
- 与 `A_freq30` 并列第一，但训练段略优，因此作为当前主算法
- **同分规则**：若候选数字得分相同，取数字较小者，保证预测可复现

### 低拥挤度方向

可选地对主推做一层“少人买倾向”筛选，用于避开大众常见模式，但不改变主评估指标：
- 惩罚过多 `8/6/9`
- 惩罚全相同、回文、ABABA、明显连号/顺子
- 惩罚过度重复
- 惩罚明显日期感低位结构（如过多 `0-3`）

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

### 步骤 3：900/100 回测与单注预测

#### 共同统计
- 每位频次分布（全期 / 近10期 / 近30期）
- 每位 Markov 转移计数
- 每位递减加权频次

#### 回测框架
- 前 900 期训练、后 100 期留出
- 算法选择只能看前 900 期；后 100 期只做最终验证
- 当前选择依据：留出集 Top-2 覆盖率优先；若并列，再看训练段表现

#### 输出格式
```text
## 26214 期推荐

主推: X X X X X
Top-2: X/Y X/Y X/Y X/Y X/Y

### 算法说明
- 当前主算法: K_prob_ensemble
- 留出集 Top-2 覆盖率: 22.0%
- 低拥挤度参考: X X X X X
```

### 步骤 4：结果对比

新开奖出现时：
1. 找到预测记录中未验证的条目
2. 更新：
   - `actualDigits`
   - `positionHits`
   - `top2Hits`
   - `exactHit`（是否整组全中）
3. 更新 `model.json` 中当前主算法的 `performance`
4. 输出对比：

```text
## 上期对比

主推: X X X X X
Top-2: X/Y X/Y X/Y X/Y X/Y
实际: X X X X X
位置命中: N/5
Top-2覆盖: N/5
是否全中: 否 / 是
```

### 步骤 5：保存预测记录

追加到 `predictions.json`，每条记录至少包含：
- `predictedDigits`
- `top2`
- `actualDigits`
- `positionHits`
- `top2Hits`
- `exactHit`
- `verified`
- `algorithm`
- `altLowCrowdTicket`

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
git commit -m "update: $(date +%Y-%m-%d) 排列五单注预测"
git push origin main
```

注意：`draws.json` 属于技能的持久化历史库，不是临时缓存。只要被初始化出来，就必须和 `model.json`、`predictions.json` 一起提交到仓库。

### 算法变更记录与恢复规则（用户要求，必须遵守）

- **任何算法/公式/权重/选号流程/数据口径的修改，必须先写变更记录再实施**：在 `data/model.json` 的 `reviewNotes` 追加一条，或在技能目录维护 `CHANGELOG.md`（参考 dlt-analyzer 的模板与历史）
- 每次变更必须包含：变更内容、原因、**变更前后指标对比**、恢复方法（git commit 号或旧参数保留）
- **保留旧版**：被替换的算法/参数保留为 `*_orig` 变体或依赖 git 历史，不直接删除
- 频次统计必须用 0-based 索引（`bincount(arr-1)`），避免 base 错位（dlt-analyzer 已踩过的坑）

---

## model.json 结构

```json
{
  "version": 2,
  "optimizationTarget": "single-ticket top2-coverage",
  "activeAlgorithm": "K_prob_ensemble",
  "models": {
    "m1": {
      "strategy": "概率建模 + 单注推荐",
      "weights": {"alpha": 1.0, "gamma": 0.995, "markovWeight": 0.35},
      "performance": {"totalPredictions": 0, "hits": {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5": 0}, "avgHitRate": 0.0}
    }
  },
  "algorithmBenchmarks": [
    {"name": "K_prob_ensemble", "holdoutCoverage": 0.22, "selected": true}
  ]
}
```

---

## 用户指令速查

| 用户说 | 执行 |
|--------|------|
| 分析排列五 / 推荐号码 | 全流程 0->1->2->3->5->6 |
| 对比上次结果 | 仅步骤 4 |
| 排列五准确率 | 输出主推命中率 + Top-2 覆盖率 |
| 偏少人买 | 输出 `altLowCrowdTicket` 作为参考 |
