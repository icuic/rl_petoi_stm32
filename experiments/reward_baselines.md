# Reward Baseline Log

This document records the first reward-shaping iterations for the minimal MuJoCo quadruped. The goal is not to declare a final gait controller, but to keep the engineering trail clear enough for resume discussion, demos, and future ablation work.

## Setup

- Environment: `SimpleQuadrupedEnv`
- Robot model: `sim/robots/simple_quadruped.xml`
- Algorithm: PPO from Stable-Baselines3
- Training budget: 100k timesteps unless noted
- Evaluation: deterministic policy, 10 episodes, 1000-step episode limit
- Hardware observed during these runs: Tesla T4, CUDA enabled

## Results

| Run | Reward Design | Steps Mean | Distance X Mean | Fall Rate | Termination Reasons | Notes |
| --- | --- | ---: | ---: | ---: | --- | --- |
| Baseline | Forward + survival + upright - action - height | 281.9 | 1.28 | 1.0 | `roll_too_large: 10` | Learns forward motion, but every deterministic evaluation ends in roll fall. |
| Stability v1 | Strong roll/pitch/angular/joint/action-delta/fall penalties | 49.3 | 0.72 | 1.0 | `roll_too_large: 9`, `pitch_too_large: 1` | Penalties were too aggressive and suppressed useful locomotion. |
| Stability v2 | Gentle stability penalties with action smoothing | 1000.0 | 5.75 | 0.0 | `timeout: 10` | First stable demo baseline. All episodes reached the time limit. |

## Stability v2 Weights

```yaml
env:
  reward:
    survival: 0.1
    forward: 1.0
    upright: 0.2
    height: 0.5
    roll: 0.15
    pitch: 0.05
    angular_velocity: 0.005
    joint_velocity: 0.0005
    action: 0.002
    action_delta: 0.001
    fall: 0.2
```

## Interpretation

The original reward gave the policy a clear forward objective, but did not make lateral stability valuable enough. The v1 shaping tried to fix that by adding strong penalties, but the policy mostly learned to terminate early or failed to discover usable motion.

The v2 reward keeps forward progress dominant and makes stability a light regularizer. This produced a practical first milestone: stable 1000-step deterministic rollouts in the minimal model. The next useful experiments should focus on whether this behavior remains stable under longer training, randomized initial states, and a robot model closer to Petoi Bittle.

## Reproduction

Train:

```bash
bash scripts/train.sh training/configs/ppo_simple_quadruped.yaml --total-timesteps 100000
```

Evaluate:

```bash
bash scripts/evaluate.sh training/configs/ppo_simple_quadruped.yaml --episodes 10 --output experiments/reports/simple_quadruped_eval_stability_v2.json
```

Record a rollout:

```bash
bash scripts/record_eval.sh training/configs/ppo_simple_quadruped.yaml --output assets/videos/simple_quadruped_stability_v2.mp4
```
