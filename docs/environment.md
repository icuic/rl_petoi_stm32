# Environment Bootstrap

服务器租期较短时，项目环境必须可以快速重建。本项目把环境重建分为两层：

1. `install_codex.sh`：安装 Codex CLI 和远程连接配置。
2. `scripts/setup_env.sh`：创建项目目录、安装 Ubuntu 依赖、创建 Python 虚拟环境、安装 MuJoCo / Gymnasium / Stable-Baselines3 等训练依赖。
3. `scripts/setup_stedgeai.sh`：检查或接入本地 ST Edge AI Core / `stedgeai` CLI。

## 新服务器初始化流程

```bash
git clone git@github.com:icuic/rl_petoi_stm32.git
cd rl_petoi_stm32
bash install_codex.sh
bash scripts/setup_env.sh
bash scripts/setup_stedgeai.sh
source .venv/bin/activate
bash scripts/check_env.sh
```

## 设计原则

- 新机器上不手工点选环境，尽量只执行脚本。
- 训练日志、checkpoint、导出模型和视频素材要及时同步到远程仓库、网盘或对象存储。
- 大文件不直接提交到 Git；后续可接入 Git LFS、Hugging Face Hub、S3 或网盘。
- 每次新增依赖后同步更新 `requirements.txt` 和本文件。
- 每次换新服务器后运行 `bash scripts/check_env.sh`，确认 CPU、内存、磁盘、GPU、Python、MuJoCo、Stable-Baselines3 和 `stedgeai` 状态。

## 后续可增强项

- 增加 Dockerfile，锁定 CUDA / MuJoCo / Python 版本。
- 增加 `scripts/sync_artifacts.sh`，统一备份 checkpoint、日志和模型。
- 增加更完整的 MuJoCo 渲染检查，区分 headless EGL、OSMesa 和本地桌面渲染。
