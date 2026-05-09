# assets

项目展示素材目录，用于保存架构图、截图、演示视频和阶段性成果图片。

- `videos/`：保存生成的 rollout 视频，默认不纳入 Git 跟踪。
- 训练后可运行 `bash scripts/record_eval.sh training/configs/ppo_simple_quadruped.yaml --output assets/videos/simple_quadruped_rollout.mp4` 生成演示素材。
