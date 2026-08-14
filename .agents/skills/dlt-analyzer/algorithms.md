# 大乐透算法池全量记录（88 个算法）

> 自动生成自 `model.json.algorithmBenchmarks`（v29）。每个算法含 900/100 回测结果；部分含 1900/1000 长窗口验证。
> 实现状态：**ORIGINAL**=原版公式已保留；**REBUILT**=按家族描述重建，可能有细节偏差；**变体**=基于 AI_U_wide 的参数变体；**未实现**=原公式未保留，仅记录结果。

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
| 20 | Y_back_conditional | back_conditional | 0.02 | 1.35 | 0.01 | — | REBUILT |
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
| 33 | AO_stacked_vote | stacked_vote | 0.05 | 1.52 | 0.02 | — | REBUILT |
| 34 | AP_zone_gap | zone_gap_joint | 0.05 | 1.31 | 0.0 | — | 未实现 |
| 35 | AQ_vote_repeat | vote_repeat_mix | 0.03 | 1.43 | 0.0 | — | 未实现 |
| 36 | AR_vote_repeat | stacked_vote_repeat | 0.04 | 1.5 | 0.01 | — | REBUILT |
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
| 59 | BS_zone_balance | zone_balance | 0.07 | 1.52 | 0.01 | — | REBUILT |
| 60 | BP_U_top28 | repeat_neighbor_top28 | 0.06 | 1.5 | 0.0 | — | 未实现 |
| 61 | BQ_joint_conditional | front_back_joint_conditional | 0.04 | 1.47 | 0.0 | — | 未实现 |
| 62 | BR_top28_joint | top28_joint_conditional | 0.04 | 1.45 | 0.0 | — | 未实现 |
| 63 | BU_low_crowd_strong | real_betting_heat_low_crowd | 0.07 | 1.52 | 0.02 | — | REBUILT |
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
| 76 | CH_strong_front | strong_front_back_repeat | 0.06 | 1.51 | 0.01 | — | REBUILT |
| 77 | CG_joint_cover | joint_back_cover | 0.01 | 1.35 | 0.0 | — | 未实现 |
| 78 | CL_knn5_lowcrowd | knn_history_match | 0.05 | 1.54 | 0.01 | — | 未实现 |
| 79 | CK_knn_follow2 | knn_follow2 | 0.04 | 1.56 | 0.0 | — | 未实现 |
| 80 | CJ_knn_repeat | knn_repeat | 0.05 | 1.48 | 0.0 | — | 未实现 |
| 81 | CI_knn_match | knn_basic | 0.05 | 1.46 | 0.0 | — | 未实现 |
| 82 | CO_repeat3 | fixed_repeat3 | 0.03 | 1.48 | 0.02 | — | REBUILT |
| 83 | CP_entropy | entropy_max | 0.05 | 1.47 | 0.0 | — | 未实现 |
| 84 | CN_repeat2 | fixed_repeat2 | 0.04 | 1.42 | 0.0 | — | REBUILT |
| 85 | CM_repeat1 | fixed_repeat1 | 0.03 | 1.37 | 0.0 | — | REBUILT |
| 86 | CQ_repeat3_lc | fixed_repeat3_lowcrowd | 0.03 | 1.52 | 0.0 | — | 未实现 |
| 87 | ML_RandomForest | machine_learning | 0.02 | 1.45 | 0.0 | 0.021 | 未实现 |
| 88 | ML_GBDT | machine_learning | 0.02 | 1.42 | 0.0 | — | 未实现 |

## 已实现算法验证（900/100 窗口 25142-26091，与记录对比）

| 算法 | 重建 ge4 | 重建 ge5 | avg | 记录 ge4 | 记录 ge5 | 偏差 |
|------|---------|---------|-----|---------|---------|------|
| v1_cold | 0.040 | 0.000 | 1.360 | 0.05 | 0.0 | -0.010 |
| v2_hot | 0.020 | 0.020 | 1.230 | 0.02 | — | +0.000 |
| v3 | 0.030 | 0.010 | 1.240 | — | — | — |
| AI_U_wide | 0.080 | 0.000 | 1.540 | 0.07 | 0.0 | +0.010 |
| AI_U_wide_orig | 0.050 | 0.010 | 1.460 | — | — | — |
| U_repeat_neighbor | 0.050 | 0.000 | 1.490 | 0.06 | 0.0 | -0.010 |
| AK_U_tuned | 0.040 | 0.000 | 1.400 | 0.07 | 0.0 | -0.030 |
| AM_back_strong | 0.050 | 0.010 | 1.460 | 0.07 | 0.0 | -0.020 |
| CE_joint_w15 | 0.030 | 0.000 | 1.430 | 0.07 | 0.0 | -0.040 |
| CF_joint_w20 | 0.030 | 0.000 | 1.430 | 0.07 | 0.0 | -0.040 |
| H_dirichlet | 0.010 | 0.010 | 1.310 | 0.04 | — | -0.030 |
| I_recency_eb | 0.000 | 0.000 | 1.330 | 0.03 | 0.01 | -0.030 |
| J_repeat_markov | 0.040 | 0.000 | 1.490 | 0.04 | — | +0.000 |
| K_prob_ensemble | 0.000 | 0.000 | 1.450 | 0.04 | 0.0 | -0.040 |
| M_tail | 0.050 | 0.010 | 1.520 | 0.03 | — | +0.020 |
| P_prime | 0.020 | 0.000 | 1.400 | 0.0 | — | +0.020 |
| O_span | 0.010 | 0.000 | 1.340 | 0.03 | — | -0.020 |
| E_entropy | 0.020 | 0.000 | 1.240 | 0.03 | — | -0.010 |
| S_sumreg | 0.010 | 0.010 | 1.330 | 0.04 | — | -0.030 |
| AZ_period7 | 0.020 | 0.000 | 1.390 | 0.07 | 0.0 | -0.050 |
| AV_rolling300 | 0.020 | 0.000 | 1.390 | 0.07 | 0.0 | -0.050 |
| AW_rolling500 | 0.020 | 0.010 | 1.420 | 0.07 | 0.0 | -0.050 |
| CO_repeat3 | 0.030 | 0.000 | 1.470 | 0.03 | 0.02 | +0.000 |
| CN_repeat2 | 0.020 | 0.010 | 1.520 | 0.04 | 0.0 | -0.020 |
| CM_repeat1 | 0.020 | 0.010 | 1.450 | 0.03 | 0.0 | -0.010 |
| AO_stacked_vote | 0.030 | 0.000 | 1.430 | 0.05 | 0.02 | -0.020 |
| AR_vote_repeat | 0.040 | 0.000 | 1.460 | 0.04 | 0.01 | +0.000 |
| BS_zone_balance | 0.060 | 0.010 | 1.510 | 0.07 | 0.01 | -0.010 |
| BU_low_crowd_strong | 0.070 | 0.010 | 1.530 | 0.07 | 0.02 | +0.000 |
| CH_strong_front | 0.060 | 0.000 | 1.490 | 0.06 | 0.01 | +0.000 |
| Y_back_conditional | 0.010 | 0.000 | 1.310 | 0.02 | 0.01 | -0.010 |

### AI_U_wide 还原说明（round-25）

- **还原版** `AI_U_wide`：`norm(freq_all) + 0.5×重号 + 0.2×邻域(r3) + topk8 6+3约束枚举` → 900/100 窗口 ge4=**8%**（记录 7%，指纹 dist 每级差 ≤1），avg=1.54；**1000 期段 ge4=3.5%、ge5=3 期**（原参数版 2.8%/ge5=1）
- 记录参数 `{repeatWeight:0.18, neighborRadius:2, neighborWeight:0.02}` 无法复现 7%（该参数+约束枚举在窗口仅 5-6%）——记录参数疑为简化值，原版实现细节未留存，还原版参数为窗口指纹拟合
- 诚实口径：还原版 1000 期段真实水平 3.5%（vs 随机 2.4%），仍远低于窗口 8%；`AI_U_wide_orig` 保留记录参数版作对照

## 未实现算法（公式未保留，仅记录结果）

Q_joint_prob、R_span_sum、T_multi_window、V_tail_balance、AA_combo_advanced、X_gap_segment、W_second_order、Z_gap_hot_mix、AB_fusion、AD_markov2、AE_fib_window、AF_gradient、AJ_U_cross、AH_combo_stability、AG_gap_hot_cross、AL_double_repeat、AP_zone_gap、AQ_vote_repeat、AS_vote_nonlinear、AT_vote_repeat_back、AU_consensus_repeat、AX_weekday、AY_distance、BD_period5_300、BC_period14_300、BB_period7_500、BE_period_gated、BF_roll500_p7、BG_multi_period、BH_sequence、BI_zone_streak、BJ_zscore、BK_pair_balance、BL_back_cover3、BM_back_repeat_hot、BN_back_anti_repeat、BO_back_cold_hot、BP_U_top28、BQ_joint_conditional、BR_top28_joint、BW_low_crowd_balance、BT_low_crowd_real、BV_low_crowd_weak、BX_prize_weighted、BY_prize_weighted_lc、BZ_prize_weighted_30、CA_chi_shift、CB_chi_gated、CC_lag_corr、CD_chi_lowcrowd、CG_joint_cover、CL_knn5_lowcrowd、CK_knn_follow2、CJ_knn_repeat、CI_knn_match、CP_entropy、CQ_repeat3_lc、ML_RandomForest、ML_GBDT

## 备注

- ge5 家族（命中5个号码潜力）已重建：AO_stacked_vote/AR_vote_repeat（多算法投票）、CO_repeat3（固定3重号）、BS_zone_balance（区间均衡）、BU_low_crowd_strong（少人买特征）、CH_strong_front、Y_back_conditional 等
- BU_low_crowd_strong 重建 7% 与记录一致（组合特征筛选，无需一等奖注数数据）；BS_zone_balance 重建 6%（记录 7%）
- 训练段调权重/重校准无效（见 SKILL.md）；本文件验证表仅反映 900/100 窗口，长窗口以 1900/1000 字段为准
