# experiments

实验记录目录，用于保存训练曲线、参数对比、阶段性报告和可复现实验配置。

- `reward_baselines.md`：记录最小四足环境的 reward shaping 迭代和指标对比。
- `milestone_01_minimal_stable_gait.md`：记录第一个可稳定演示的最小 gait 里程碑。
- `bittle_like_v0_sanity.md`：记录 Bittle-like v0 模型的首次训练、评估、录制和导出结果。
- `bittle_like_v0_stand.md`：记录 Bittle-like v0 的站立稳定任务和低探索噪声结论。
- `bittle_like_v0_slow_forward.md`：记录从站立策略 warm-start 到慢速前进 curriculum 的首次结果。
- `bittle_like_v1_visual.md`：记录更接近 Bittle 外观的 v1 visual 模型和站立 smoke test。
- `petoi_bittle_v0_stand_calibration.md`：记录官方 Petoi MJCF 的站姿扫描、stand policy 训练和评估结果。
- `petoi_bittle_v0_stand_milestone.md`：记录 Petoi stand policy 的视频录制、ONNX 导出和 parity 验证闭环。
- `petoi_bittle_v0_slow_forward.md`：记录 Petoi stand warm-start 后加入弱前进奖励的首次 slow-forward baseline。
- `petoi_bittle_v0_open_loop_trot.md`：记录 Petoi phase-based trot reference 的首次 open-loop 扫描。
- `petoi_bittle_v0_trot_residual.md`：记录 Petoi trot reference 上的第一版 PPO residual baseline。
- `petoi_bittle_v0_trot_residual_v2.md`：记录加入 per-step progress reward 后的 residual trot v2 baseline。
- `petoi_bittle_v0_zero_action_residual_trot.md`：记录 Gym 环境中 zero-action residual trot 的 phase timing 诊断。
- `petoi_bittle_v0_trot_residual_v3_phase_fixed.md`：记录修正 phase timing 后的 PPO residual trot 前进基线。
- `petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue.md`：记录 v3 phase-fixed 策略继续训练 100k 后的当前最佳前进基线。
- `reports/`：保存生成的评估 JSON，默认不纳入 Git 跟踪。
