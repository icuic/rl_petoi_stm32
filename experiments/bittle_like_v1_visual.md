# Bittle-like v1 Visual Model

This note records the first visual/proportion update after comparing the simulated robot against Petoi Bittle/Bittle X references.

## Motivation

`bittle_like_v0.xml` was a dynamics proxy. It preserved the 8-DoF leg-control interface, but it looked too much like a generic quadruped:

- no dog-like head,
- no tail,
- no visible servo housings,
- no Bittle-style black/yellow/blue/red color blocking,
- simplified body proportions.

The v1 visual model is still not CAD-accurate, but it is meant to make demo videos recognizably closer to Bittle while keeping the current RL interface stable.

## Reference

Petoi's current Bittle X technical specification lists:

- standing dimensions around `190 x 153 x 107 mm`,
- robot weight around `269-353 g`,
- `9` servo-powered joints,
- colors including `Black+Yellow+Blue+Red`.

Legacy Bittle material and common product images often show roughly `200 x 100 x 110 mm`, `265-290 g`, and `9` servo-powered joints. The v1 visual model uses these as rough proportion guides, not as exact mechanical measurements.

Sources:

- Petoi Bittle X technical specifications: `https://www.petoi.com/pages/bittle-x-robot-dog-with-arm-specifications`
- Petoi Bittle X V2 guide: `https://guide.petoi.com/product/bittle-x-v2`
- Legacy Bittle technical specifications: `https://www.petoi.com/pages/bittle-robot-dog-specifications`

## Model

File:

```bash
sim/robots/bittle_like_v1_visual.xml
```

Changes versus v0:

- Added fixed visual head, snout, ears, neck-side disks, and tail.
- Added black top shell, yellow chassis/chest, blue lower legs/feet, and red upper-leg covers.
- Added visible servo-box geoms near hips and knees.
- Adjusted stance width and body proportions toward Bittle-like dimensions.
- Kept the same 8 actuated leg joints and action order.

Important limitation:

```text
The 9th neck/head servo is not yet part of the RL action space.
```

The current policy interface remains:

```text
observation[29] -> action[8]
```

## Stand Smoke Test

Config:

```bash
training/configs/ppo_bittle_like_v1_visual_stand.yaml
```

Training command:

```bash
bash scripts/train.sh training/configs/ppo_bittle_like_v1_visual_stand.yaml --total-timesteps 10000 --check-env
```

Evaluation command:

```bash
bash scripts/evaluate.sh training/configs/ppo_bittle_like_v1_visual_stand.yaml --episodes 5 --output experiments/reports/bittle_like_v1_visual_stand_eval.json
```

Recording command:

```bash
bash scripts/record_eval.sh training/configs/ppo_bittle_like_v1_visual_stand.yaml --max-steps 200 --output assets/videos/bittle_like_v1_visual_stand.mp4
```

Evaluation summary:

| Metric | Value |
| --- | ---: |
| reward_mean | 374.92 |
| reward_std | 0.02 |
| steps_mean | 1000.0 |
| distance_x_mean | -0.069 |
| fall_rate | 0.0 |
| final_torso_height_mean | 0.114 |
| final_roll_abs_mean | 0.0039 |
| final_pitch_abs_mean | 0.461 |

Termination reasons:

```json
{"timeout": 5}
```

## Next Model Work

- Compare v1 video side-by-side with real Bittle X V2 photos and adjust link positions.
- Add a proper optional neck joint as the 9th servo, but keep it out of locomotion actions until the policy interface is versioned.
- Replace primitive geoms with URDF/MJCF imported geometry if Petoi/OpenCat assets provide usable meshes.
- Separate collision geoms from visual geoms so visual fidelity can improve without destabilizing training.
