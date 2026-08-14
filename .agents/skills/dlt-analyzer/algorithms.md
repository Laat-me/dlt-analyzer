# 大乐透算法池全量记录（88 个算法）

> 自动生成自 `model.json.algorithmBenchmarks`（v29）。每个算法含 900/100 回测结果；部分含 1900/1000 长窗口验证。
> 实现状态：**ORIGINAL**=原版公式已保留（SKILL.md/参数记录）；**REBUILT**=按家族描述重建，可能有细节偏差；**变体**=基于 AI_U_wide 的参数变体；**未实现**=原公式未保留，仅记录结果。

## 全部算法一览

| # | 算法 | 家族 | 900/100 ge4 | avg | ge5 | 1900/1000 | 实现状态 |
|---|------|------|-----------|-----|-----|----------|---------|
| 1 | v1_cold | gap_frequency | 0.05 | — | 0.0 | — | ORIGINAL |
| 2 | K_prob_ensemble | probability_ensemble | 0.04 | 1.52 | 0.0 | — | REBUILT |
| 3 | J_repeat_markov | markov_mixture | 0.04 | 1.49 | — | — | REBUILT |
| 4 | H_dirichlet | bayesian_positional | 0.04 | — | — | — | REBUILT |
| 5 | S_sumreg | sum_regression | 0.04 | — | — | — | REBUILT |
| 6 | I_recency_eb | recency_weighted_bayes | 0.03 | — | 0.01 | — | REBUILT |
| 7 | O_span | span_neighbor | 0.03 | — | — | — | REBUILT |
| 8 | M_tail | tail_digit | 0.03 | — | — | — | REBUILT |
| 9 | E_entropy | entropy_balance | 0.03 | — | — | — | REBUILT |
| 10 | v2_hot | recency_hot | 0.02 | — | — | — | ORIGINAL |
| 11 | P_prime | prime_bias | 0.0 | — | — | — | REBUILT |
| 12 | U_repeat_neighbor | repeat_neighbor | 0.06 | 1.53 | 0.0 | — | REBUILT |
| 13 | Q_joint_prob | joint_probability_cooccurrence | 0.04 | 1.4 | — | — | 未实现 |
| 14 | R_span_sum | span_sum_constraint | 0.04 | 1.38 | — | — | 未实现 |
| 15 | T_multi_window | multi_window_mix | 0.01 | 1.37 | — | — | 未实现 |
| 16 | V_tail_balance | tail_balance | 0.03 | 1.29 | — | — | 未实现 |
| 17 | AA_combo_advanced | multi_window_repeat_neighbor | 0.05 | 1.45 | 0.0 | — | 未实现 |
| 18 | X_gap_segment | gap_segment_weighted | 0.04 | 1.43 | 0.0 | — | 未实现 |
| 19 | W_second_order | second_order_cooccurrence | 0.04 | 1.33 | — | — | 未实现 |
| 20 | Y_back_conditional | back_conditional | 0.02 | 1.35 | 0.01 | — | 未实现 |
| 21 | Z_gap_hot_mix | gap_hot_mix | 0.01 | 1.32 | — | — | 未实现 |
| 22 | AB_fusion | weighted_fusion | 0.04 | 1.26 | — | — | 未实现 |
| 23 | AD_markov2 | second_order_markov | 0.04 | 1.36 | — | — | 未实现 |
| 24 | AE_fib_window | fibonacci_window | 0.02 | 1.29 | — | — | 未实现 |
| 25 | AF_gradient | frequency_gradient | 0.01 | 1.33 | — | — | 未实现 |
| 26 | AI_U_wide | repeat_neighbor_wide | 0.07 | 1.52 | 0.0 | 0.032 | REBUILT |
| 27 | AJ_U_cross | repeat_neighbor_gap_hot_cross | 0.05 | 1.54 | 0.0 | — | 未实现 |
| 28 | AH_combo_stability | combo_stability | 0.04 | 1.34 | — | — | 未实现 |
| 29 | AG_gap_hot_cross | gap_hot_cross | 0.02 | 1.22 | — | — | 未实现 |
| 30 | AK_U_tuned | repeat_neighbor_wide | 0.07 | 1.52 | 0.0 | — | 变体 |
| 31 | AL_double_repeat | double_repeat_neighbor | 0.03 | 1.48 | 0.0 | — | 未实现 |
| 32 | AM_back_strong | repeat_neighbor_back_strong | 0.07 | 1.52 | 0.0 | — | 变体 |
| 33 | AO_stacked_vote | stacked_vote | 0.05 | 1.52 | 0.02 | — | 未实现 |
| 34 | AP_zone_gap | zone_gap_joint | 0.05 | 1.31 | 0.0 | — | 未实现 |
| 35 | AQ_vote_repeat | vote_repeat_mix | 0.03 | 1.43 | 0.0 | — | 未实现 |
| 36 | AR_vote_repeat | stacked_vote_repeat | 0.04 | 1.5 | 0.01 | — | 未实现 |
| 37 | AS_vote_nonlinear | stacked_vote_nonlinear | 0.04 | 1.43 | 0.0 | — | 未实现 |
| 38 | AT_vote_repeat_back | stacked_vote_repeat_back | 0.02 | 1.5 | 0.0 | — | 未实现 |
| 39 | AU_consensus_repeat | consensus_repeat | 0.05 | 1.52 | 0.0 | — | 未实现 |
| 40 | AZ_period7 | period7_regression | 0.07 | 1.59 | 0.0 | — | REBUILT |
| 41 | AW_rolling500 | rolling_window500_repeat | 0.07 | 1.53 | 0.0 | — | REBUILT |
| 42 | AV_rolling300 | rolling_window300_repeat | 0.07 | 1.52 | 0.0 | — | REBUILT |
| 43 | AX_weekday | weekday_effect | 0.06 | 1.52 | 0.0 | — | 未实现 |
| 44 | AY_distance | distance_structure | 0.05 | 1.51 | 0.0 | — | 未实现 |
| 45 | BD_period5_300 | period5_rolling300 | 0.07 | 1.55 | 0.0 | — | 未实现 |
| 46 | BC_period14_300 | period14_rolling300 | 0.07 | 1.47 | 0.0 | — | 未实现 |
| 47 | BB_period7_500 | period7_rolling500 | 0.05 | 1.53 | 0.0 | — | 未实现 |
| 48 | BE_period_gated | period_gated | 0.05 | 1.53 | 0.0 | — | 未实现 |
| 49 | BF_roll500_p7 | rolling500_period7 | 0.05 | 1.52 | 0.0 | — | 未实现 |
| 50 | BG_multi_period | multi_period_7_14 | 0.05 | 1.51 | 0.0 | — | 未实现 |
| 51 | BH_sequence | cold_hot_sequence | 0.07 | 1.48 | 0.0 | — | 未实现 |
| 52 | BI_zone_streak | zone_streak | 0.07 | 1.48 | 0.0 | — | 未实现 |
| 53 | BJ_zscore | zscore_trend | 0.03 | 1.44 | 0.0 | — | 未实现 |
| 54 | BK_pair_balance | pair_balance | 0.05 | 1.5 | 0.0 | — | 未实现 |
| 55 | BL_back_cover3 | back_cover3 | 0.05 | 1.52 | 0.0 | — | 未实现 |
| 56 | BM_back_repeat_hot | back_repeat_hot | 0.04 | 1.47 | 0.0 | — | 未实现 |
| 57 | BN_back_anti_repeat | back_anti_repeat | 0.02 | 1.38 | 0.0 | — | 未实现 |
| 58 | BO_back_cold_hot | back_cold_hot_mix | 0.01 | 1.35 | 0.0 | — | 未实现 |
| 59 | BS_zone_balance | zone_balance | 0.07 | 1.52 | 0.01 | — | 未实现 |
| 60 | BP_U_top28 | repeat_neighbor_top28 | 0.06 | 1.5 | 0.0 | — | 未实现 |
| 61 | BQ_joint_conditional | front_back_joint_conditional | 0.04 | 1.47 | 0.0 | — | 未实现 |
| 62 | BR_top28_joint | top28_joint_conditional | 0.04 | 1.45 | 0.0 | — | 未实现 |
| 63 | BU_low_crowd_strong | real_betting_heat_low_crowd | 0.07 | 1.52 | 0.02 | — | 未实现 |
| 64 | BW_low_crowd_balance | real_betting_heat_balance | 0.07 | 1.52 | 0.01 | — | 未实现 |
| 65 | BT_low_crowd_real | real_betting_heat | 0.06 | 1.5 | 0.02 | — | 未实现 |
| 66 | BV_low_crowd_weak | real_betting_heat_weak | 0.06 | 1.5 | 0.02 | — | 未实现 |
| 67 | BX_prize_weighted | prize_count_weighted | 0.06 | 1.56 | 0.0 | — | 未实现 |
| 68 | BY_prize_weighted_lc | prize_weighted_low_crowd | 0.06 | 1.51 | 0.02 | — | 未实现 |
| 69 | BZ_prize_weighted_30 | prize_weighted_30 | 0.04 | 1.4 | 0.0 | — | 未实现 |
| 70 | CA_chi_shift | chi_square_shift | 0.06 | 1.53 | 0.0 | — | 未实现 |
| 71 | CB_chi_gated | chi_square_gated | 0.06 | 1.51 | 0.0 | — | 未实现 |
| 72 | CC_lag_corr | lag_autocorrelation | 0.06 | 1.51 | 0.0 | — | 未实现 |
| 73 | CD_chi_lowcrowd | chi_square_low_crowd | 0.06 | 1.51 | 0.01 | — | 未实现 |
| 74 | CE_joint_w15 | joint_6_3_scoring | 0.07 | 1.52 | 0.0 | — | 变体 |
| 75 | CF_joint_w20 | joint_6_3_scoring_w2 | 0.07 | 1.52 | 0.0 | — | 变体 |
| 76 | CH_strong_front | strong_front_back_repeat | 0.06 | 1.51 | 0.01 | — | 未实现 |
| 77 | CG_joint_cover | joint_back_cover | 0.01 | 1.35 | 0.0 | — | 未实现 |
| 78 | CL_knn5_lowcrowd | knn_history_match | 0.05 | 1.54 | 0.01 | — | 未实现 |
| 79 | CK_knn_follow2 | knn_follow2 | 0.04 | 1.56 | 0.0 | — | 未实现 |
| 80 | CJ_knn_repeat | knn_repeat | 0.05 | 1.48 | 0.0 | — | 未实现 |
| 81 | CI_knn_match | knn_basic | 0.05 | 1.46 | 0.0 | — | 未实现 |
| 82 | CO_repeat3 | fixed_repeat3 | 0.03 | 1.48 | 0.02 | — | 未实现 |
| 83 | CP_entropy | entropy_max | 0.05 | 1.47 | 0.0 | — | 未实现 |
| 84 | CN_repeat2 | fixed_repeat2 | 0.04 | 1.42 | 0.0 | — | 未实现 |
| 85 | CM_repeat1 | fixed_repeat1 | 0.03 | 1.37 | 0.0 | — | 未实现 |
| 86 | CQ_repeat3_lc | fixed_repeat3_lowcrowd | 0.03 | 1.52 | 0.0 | — | 未实现 |
| 87 | ML_RandomForest | machine_learning | 0.02 | 1.45 | 0.0 | 0.021 | REBUILT |
| 88 | ML_GBDT | machine_learning | 0.02 | 1.42 | 0.0 | — | REBUILT |

## 家族分组说明

### gap_frequency
- **v1_cold**: 900/100 ge4=0.05, avg=—

### probability_ensemble
- **K_prob_ensemble**: 900/100 ge4=0.04, avg=1.52

### markov_mixture
- **J_repeat_markov**: 900/100 ge4=0.04, avg=1.49

### bayesian_positional
- **H_dirichlet**: 900/100 ge4=0.04, avg=—

### sum_regression
- **S_sumreg**: 900/100 ge4=0.04, avg=—

### recency_weighted_bayes
- **I_recency_eb**: 900/100 ge4=0.03, avg=—

### span_neighbor
- **O_span**: 900/100 ge4=0.03, avg=—

### tail_digit
- **M_tail**: 900/100 ge4=0.03, avg=—

### entropy_balance
- **E_entropy**: 900/100 ge4=0.03, avg=—

### recency_hot
- **v2_hot**: 900/100 ge4=0.02, avg=—

### prime_bias
- **P_prime**: 900/100 ge4=0.0, avg=—

### repeat_neighbor
- **U_repeat_neighbor**: 900/100 ge4=0.06, avg=1.53

### joint_probability_cooccurrence
- **Q_joint_prob**: 900/100 ge4=0.04, avg=1.4

### span_sum_constraint
- **R_span_sum**: 900/100 ge4=0.04, avg=1.38

### multi_window_mix
- **T_multi_window**: 900/100 ge4=0.01, avg=1.37

### tail_balance
- **V_tail_balance**: 900/100 ge4=0.03, avg=1.29

### multi_window_repeat_neighbor
- **AA_combo_advanced**: 900/100 ge4=0.05, avg=1.45

### gap_segment_weighted
- **X_gap_segment**: 900/100 ge4=0.04, avg=1.43

### second_order_cooccurrence
- **W_second_order**: 900/100 ge4=0.04, avg=1.33

### back_conditional
- **Y_back_conditional**: 900/100 ge4=0.02, avg=1.35

### gap_hot_mix
- **Z_gap_hot_mix**: 900/100 ge4=0.01, avg=1.32

### weighted_fusion
- **AB_fusion**: 900/100 ge4=0.04, avg=1.26

### second_order_markov
- **AD_markov2**: 900/100 ge4=0.04, avg=1.36

### fibonacci_window
- **AE_fib_window**: 900/100 ge4=0.02, avg=1.29

### frequency_gradient
- **AF_gradient**: 900/100 ge4=0.01, avg=1.33

### repeat_neighbor_wide
- **AI_U_wide**: 900/100 ge4=0.07, avg=1.52；参数: {"repeatWeight": 0.18, "neighborRadius": 2, "neighborWeight": 0.02}；1900/1000: ge4=0.032, avg=1.378
- **AK_U_tuned**: 900/100 ge4=0.07, avg=1.52；参数: {"repeatWeight": 0.12, "neighborRadius": 2, "neighborWeight": 0.02, "backRepeatWeight": 0.12}

### repeat_neighbor_gap_hot_cross
- **AJ_U_cross**: 900/100 ge4=0.05, avg=1.54

### combo_stability
- **AH_combo_stability**: 900/100 ge4=0.04, avg=1.34

### gap_hot_cross
- **AG_gap_hot_cross**: 900/100 ge4=0.02, avg=1.22

### double_repeat_neighbor
- **AL_double_repeat**: 900/100 ge4=0.03, avg=1.48

### repeat_neighbor_back_strong
- **AM_back_strong**: 900/100 ge4=0.07, avg=1.52

### stacked_vote
- **AO_stacked_vote**: 900/100 ge4=0.05, avg=1.52；注: 出现2次命中5个号码的期数(ge5=2%), 高命中级别潜力但稳定性略逊

### zone_gap_joint
- **AP_zone_gap**: 900/100 ge4=0.05, avg=1.31

### vote_repeat_mix
- **AQ_vote_repeat**: 900/100 ge4=0.03, avg=1.43

### stacked_vote_repeat
- **AR_vote_repeat**: 900/100 ge4=0.04, avg=1.5

### stacked_vote_nonlinear
- **AS_vote_nonlinear**: 900/100 ge4=0.04, avg=1.43

### stacked_vote_repeat_back
- **AT_vote_repeat_back**: 900/100 ge4=0.02, avg=1.5

### consensus_repeat
- **AU_consensus_repeat**: 900/100 ge4=0.05, avg=1.52

### period7_regression
- **AZ_period7**: 900/100 ge4=0.07, avg=1.59；注: avg 1.59全场最高, 7期周期回归提升每期命中分布(命中3个的期数13->16)

### rolling_window500_repeat
- **AW_rolling500**: 900/100 ge4=0.07, avg=1.53

### rolling_window300_repeat
- **AV_rolling300**: 900/100 ge4=0.07, avg=1.52

### weekday_effect
- **AX_weekday**: 900/100 ge4=0.06, avg=1.52

### distance_structure
- **AY_distance**: 900/100 ge4=0.05, avg=1.51

### period5_rolling300
- **BD_period5_300**: 900/100 ge4=0.07, avg=1.55

### period14_rolling300
- **BC_period14_300**: 900/100 ge4=0.07, avg=1.47

### period7_rolling500
- **BB_period7_500**: 900/100 ge4=0.05, avg=1.53

### period_gated
- **BE_period_gated**: 900/100 ge4=0.05, avg=1.53

### rolling500_period7
- **BF_roll500_p7**: 900/100 ge4=0.05, avg=1.52

### multi_period_7_14
- **BG_multi_period**: 900/100 ge4=0.05, avg=1.51

### cold_hot_sequence
- **BH_sequence**: 900/100 ge4=0.07, avg=1.48

### zone_streak
- **BI_zone_streak**: 900/100 ge4=0.07, avg=1.48

### zscore_trend
- **BJ_zscore**: 900/100 ge4=0.03, avg=1.44

### pair_balance
- **BK_pair_balance**: 900/100 ge4=0.05, avg=1.5

### back_cover3
- **BL_back_cover3**: 900/100 ge4=0.05, avg=1.52

### back_repeat_hot
- **BM_back_repeat_hot**: 900/100 ge4=0.04, avg=1.47

### back_anti_repeat
- **BN_back_anti_repeat**: 900/100 ge4=0.02, avg=1.38

### back_cold_hot_mix
- **BO_back_cold_hot**: 900/100 ge4=0.01, avg=1.35

### zone_balance
- **BS_zone_balance**: 900/100 ge4=0.07, avg=1.52；注: 区间均衡(每段<=2)保持7%且出现1期命中5个号码(ge5=1%)

### repeat_neighbor_top28
- **BP_U_top28**: 900/100 ge4=0.06, avg=1.5

### front_back_joint_conditional
- **BQ_joint_conditional**: 900/100 ge4=0.04, avg=1.47

### top28_joint_conditional
- **BR_top28_joint**: 900/100 ge4=0.04, avg=1.45

### real_betting_heat_low_crowd
- **BU_low_crowd_strong**: 900/100 ge4=0.07, avg=1.52；注: 基于500期真实一等奖注数分析: 少人买组合特征=和值>92+高区多+低区少; ge5=2%并列最高

### real_betting_heat_balance
- **BW_low_crowd_balance**: 900/100 ge4=0.07, avg=1.52

### real_betting_heat
- **BT_low_crowd_real**: 900/100 ge4=0.06, avg=1.5

### real_betting_heat_weak
- **BV_low_crowd_weak**: 900/100 ge4=0.06, avg=1.5

### prize_count_weighted
- **BX_prize_weighted**: 900/100 ge4=0.06, avg=1.56；注: 一等奖注数加权频率(少人买期权重2.0/多人买0.5), avg 1.56为全场最高之一

### prize_weighted_low_crowd
- **BY_prize_weighted_lc**: 900/100 ge4=0.06, avg=1.51

### prize_weighted_30
- **BZ_prize_weighted_30**: 900/100 ge4=0.04, avg=1.4

### chi_square_shift
- **CA_chi_shift**: 900/100 ge4=0.06, avg=1.53；注: 卡方均匀性检验偏差利用, avg 1.53略高于AI_U_wide但ge4未超越

### chi_square_gated
- **CB_chi_gated**: 900/100 ge4=0.06, avg=1.51

### lag_autocorrelation
- **CC_lag_corr**: 900/100 ge4=0.06, avg=1.51

### chi_square_low_crowd
- **CD_chi_lowcrowd**: 900/100 ge4=0.06, avg=1.51

### joint_6_3_scoring
- **CE_joint_w15**: 900/100 ge4=0.07, avg=1.52；注: 前后区联合评分(后区权重1.5), 与AI_U_wide收敛到相同最优选择

### joint_6_3_scoring_w2
- **CF_joint_w20**: 900/100 ge4=0.07, avg=1.52

### strong_front_back_repeat
- **CH_strong_front**: 900/100 ge4=0.06, avg=1.51

### joint_back_cover
- **CG_joint_cover**: 900/100 ge4=0.01, avg=1.35

### knn_history_match
- **CL_knn5_lowcrowd**: 900/100 ge4=0.05, avg=1.54；注: 历史相似性匹配(近5期kNN)+少人买, avg 1.54高但ge4 5%未超越

### knn_follow2
- **CK_knn_follow2**: 900/100 ge4=0.04, avg=1.56；注: 相似历史期后两期号码, avg 1.56全场最高之一但ge4 4%

### knn_repeat
- **CJ_knn_repeat**: 900/100 ge4=0.05, avg=1.48

### knn_basic
- **CI_knn_match**: 900/100 ge4=0.05, avg=1.46

### fixed_repeat3
- **CO_repeat3**: 900/100 ge4=0.03, avg=1.48；注: 固定3个重号, ge5=2%出现2期命中5个号码, 高命中潜力但ge4仅3%

### entropy_max
- **CP_entropy**: 900/100 ge4=0.05, avg=1.47

### fixed_repeat2
- **CN_repeat2**: 900/100 ge4=0.04, avg=1.42

### fixed_repeat1
- **CM_repeat1**: 900/100 ge4=0.03, avg=1.37

### fixed_repeat3_lowcrowd
- **CQ_repeat3_lc**: 900/100 ge4=0.03, avg=1.52

### machine_learning
- **ML_RandomForest**: 900/100 ge4=0.02, avg=1.45；参数: {"model": "RandomForestClassifier", "n_estimators": 200, "max_depth": 8, "features": "8维(freq_all/30/10/5/7, gap, repeat, neighbor)", "data": "2900期全量历史(07010-26091)"}；注: ML方向: 训练准确率85%但仅学到多数类, 留出集ge4仅2%远低于AI_U_wide的7%；1900/1000: ge4=0.021, avg=None
- **ML_GBDT**: 900/100 ge4=0.02, avg=1.42；参数: {"model": "GradientBoostingClassifier", "n_estimators": 200, "max_depth": 4}；注: ML方向: 与RF一致, ge4仅2%

## 已实现算法（algorithms.py）

| 算法 | 实现方式 |
|------|---------|
| v1_cold | ORIGINAL：`gap×0.5 + (5-freq30)×2.5 + (N/7-freq)×0.3`（SKILL.md 原版公式） |
| v2_hot | ORIGINAL：`freq5×3 + freq10×1.5 + neighbor×4 + streak×4` |
| v3 | ORIGINAL：冷热池 2+3 配比组合 |
| AI_U_wide | ORIGINAL 参数：`norm(freq_all) + 0.18×重号 + 0.02×邻域(r2)`，可选 6+3 约束枚举 |
| U_repeat_neighbor | AI_U_wide 前身：重号+邻域（r1） |
| H/I/J/K | REBUILT：Dirichlet 平滑 / 递减加权经验贝叶斯(γ=0.995) / 重号马尔可夫混合 / 等权集成 |
| M/P/O/E/S | REBUILT：尾号加权 / 质数偏好 / 跨度邻域 / 熵均匀 / 和值回归 |
| AZ_period7 | REBUILT：7 期周期回归（7 期前同窗口号码加权） |
| AV/AW | REBUILT：滚动 300/500 期窗口 + 重号 |
| AK/AM/CE/CF | 变体：AI_U_wide 的参数/后区权重变体 |
| ML_RF/GBDT | REBUILT：8 维特征分类器（需 sklearn） |

## 未实现算法（公式未保留，仅记录结果）

以下算法仅有家族名与回测结果，原实验代码未保留。如需重建需按家族名推断公式，重建结果可能与原版有偏差：

Q_joint_prob、R_span_sum、T_multi_window、V_tail_balance、AA_combo_advanced、X_gap_segment、W_second_order、Y_back_conditional、Z_gap_hot_mix、AB_fusion、AD_markov2、AE_fib_window、AF_gradient、AJ_U_cross、AH_combo_stability、AG_gap_hot_cross、AL_double_repeat、AO_stacked_vote、AP_zone_gap、AQ_vote_repeat、AR_vote_repeat、AS_vote_nonlinear、AT_vote_repeat_back、AU_consensus_repeat、AX_weekday、AY_distance、BD_period5_300、BC_period14_300、BB_period7_500、BE_period_gated、BF_roll500_p7、BG_multi_period、BH_sequence、BI_zone_streak、BJ_zscore、BK_pair_balance、BL_back_cover3、BM_back_repeat_hot、BN_back_anti_repeat、BO_back_cold_hot、BS_zone_balance、BP_U_top28、BQ_joint_conditional、BR_top28_joint、BU_low_crowd_strong、BW_low_crowd_balance、BT_low_crowd_real、BV_low_crowd_weak、BX_prize_weighted、BY_prize_weighted_lc、BZ_prize_weighted_30、CA_chi_shift、CB_chi_gated、CC_lag_corr、CD_chi_lowcrowd、CH_strong_front、CG_joint_cover、CL_knn5_lowcrowd、CK_knn_follow2、CJ_knn_repeat、CI_knn_match、CO_repeat3、CP_entropy、CN_repeat2、CM_repeat1、CQ_repeat3_lc

## 重建验证（1005期库最后100期 25142-26091，与 900/100 留出段同窗口）

| 算法 | 重建 ge4 | 重建 avg | 重建分布(0-7) | 记录 ge4 | 偏差 |
|------|---------|---------|---------------|---------|------|
| v1_cold | 0.040 | 1.360 | [17, 48, 21, 10, 4, 0, 0, 0] | 0.05 | -0.010 |
| v2_hot | 0.030 | 1.180 | [25, 41, 28, 3, 3, 0, 0, 0] | 0.02 | +0.010 |
| v3 | 0.030 | 1.260 | [23, 44, 21, 9, 2, 1, 0, 0] | — | — |
| AI_U_wide | 0.050 | 1.500 | [16, 43, 22, 14, 4, 1, 0, 0] | 0.07 | -0.020 |
| U_repeat_neighbor | 0.050 | 1.460 | [18, 43, 20, 14, 4, 1, 0, 0] | 0.06 | -0.010 |
| AK_U_tuned | 0.040 | 1.440 | [14, 46, 26, 10, 4, 0, 0, 0] | 0.07 | -0.030 |
| AM_back_strong | 0.050 | 1.500 | [16, 43, 22, 14, 4, 1, 0, 0] | 0.07 | -0.020 |
| CE_joint_w15 | 0.030 | 1.400 | [15, 49, 20, 13, 3, 0, 0, 0] | 0.07 | -0.040 |
| CF_joint_w20 | 0.030 | 1.400 | [15, 49, 20, 13, 3, 0, 0, 0] | 0.07 | -0.040 |
| H_dirichlet | 0.010 | 1.310 | [19, 42, 30, 8, 0, 1, 0, 0] | 0.04 | -0.030 |
| I_recency_eb | 0.000 | 1.330 | [20, 38, 31, 11, 0, 0, 0, 0] | 0.03 | -0.030 |
| J_repeat_markov | 0.040 | 1.490 | [18, 36, 29, 13, 4, 0, 0, 0] | 0.04 | +0.000 |
| K_prob_ensemble | 0.000 | 1.450 | [18, 35, 31, 16, 0, 0, 0, 0] | 0.04 | -0.040 |
| M_tail | 0.050 | 1.520 | [14, 39, 34, 8, 4, 1, 0, 0] | 0.03 | +0.020 |
| P_prime | 0.020 | 1.400 | [15, 46, 25, 12, 2, 0, 0, 0] | 0.0 | +0.020 |
| O_span | 0.010 | 1.290 | [24, 33, 34, 8, 1, 0, 0, 0] | 0.03 | -0.020 |
| E_entropy | 0.020 | 1.240 | [26, 38, 24, 10, 2, 0, 0, 0] | 0.03 | -0.010 |
| S_sumreg | 0.010 | 1.330 | [21, 37, 32, 9, 0, 1, 0, 0] | 0.04 | -0.030 |
| AZ_period7 | 0.020 | 1.390 | [16, 40, 35, 7, 2, 0, 0, 0] | 0.07 | -0.050 |
| AV_rolling300 | 0.020 | 1.390 | [22, 34, 29, 13, 2, 0, 0, 0] | 0.07 | -0.050 |
| AW_rolling500 | 0.020 | 1.420 | [21, 37, 24, 16, 1, 1, 0, 0] | 0.07 | -0.050 |

说明：ORIGINAL 公式算法（v1/v2/J/AI_U_wide/U）重建值接近记录；REBUILT 算法（H/I/K/AZ/AV/AW 等）原版公式未保留，重建偏差大，仅供家族近似参考。AI_U_wide 重建 5% vs 记录 7%：正确索引+约束枚举实现显著优于错误重构（2.4%），剩余差距含窗口好运成分与原版实现细节。