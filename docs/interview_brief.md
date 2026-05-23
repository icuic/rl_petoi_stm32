# Interview Brief



## 2-Minute Project Pitch

I built a Petoi Bittle X V2 quadruped project that connects reinforcement
learning, model deployment, and embedded control on STM32H747.

The training side uses MuJoCo and PPO to learn a lightweight residual gait
policy. The selected actor is a small MLP with input dimension 23, two hidden
layers of 64 neurons, and output dimension 8. The output is not a high-level
command; it is an 8-joint residual action used to generate leg target angles.

For deployment, I exported the actor to ONNX, verified numerical parity against
the PyTorch/SB3 model, generated C code with ST Edge AI, and built a smoke ELF
for the STM32H747 M7 core. The current generated network is small enough for MCU
deployment: about 6,216 float parameters, 24.28 KiB weights, 512 B activations,
and about 7,512 MACC per inference.

On the robot side, I patched Petoi OpenCatEsp32 firmware with a binary RL serial
extension. The first commands are `RL_GET_STATE` for telemetry and
`RL_SET_TARGETS` for safe 8-joint target writes. This has already been flashed
onto a real Bittle X V2. `RL_GET_STATE` returns valid telemetry, and the first
conservative neutral target was accepted by the robot.

The current project value is the full engineering chain: simulation policy,
ONNX export, ST Edge AI code generation, STM32 smoke integration, binary robot
protocol, and safety-first real-machine bring-up.

## 5-Minute Version

The project starts from a practical constraint: I wanted the final control loop
to live on an STM32H747 rather than on a PC. That shaped the policy design. The
actor network is deliberately small:

```text
input: 23
hidden: 64, 64
output: 8
```

The 23 inputs are:

```text
0:2    roll, pitch
2:5    angular velocity x/y/z
5:13   8 current joint angles
13:21  previous_action[8]
21:23  sin(2*pi*phase), cos(2*pi*phase)
```

The output is 8 normalized residual actions. Deployment must reconstruct the
actual joint targets with the same semantics as training: gait reference plus
limited residual action. This makes the policy compact and helps keep MCU
runtime predictable.

I selected the current model by evaluation rather than by the last training
checkpoint. The deployable candidate is the gait_quality_v2 30k checkpoint. It
passed deterministic simulation evaluation, visual rollout review, ONNX parity
checking, ST Edge AI generation, policy-vector verification, and STM32H747 M7
smoke ELF build. I explicitly do not use the later `final_model.zip` because it
regressed after 30k.

The deployment path is:

```text
SB3/PyTorch actor
-> ONNX actor
-> ONNX parity report and fixed test vector
-> ST Edge AI C generation
-> STM32H747 M7 smoke ELF
-> runtime observation/action interface
-> OpenCat/Bittle command bridge
```

For the robot side, I patched OpenCatEsp32 rather than sending ad hoc text
commands. The binary protocol has a frame header, message type, sequence id,
payload length, payload, and CRC. The first two commands are intentionally
minimal:

```text
RL_GET_STATE: read telemetry and joint cache
RL_SET_TARGETS: write one 8-joint absolute target packet
```

I flashed this firmware to a Bittle X V2 and verified that `RL_GET_STATE`
returns decoded telemetry. I also verified the first conservative neutral target
with `RL_SET_TARGETS`; the command was accepted. The next hardware step is
single-joint mapping, not learned walking. This is important because joint
order, sign convention, servo limits, and emergency fallback must be validated
before closing the learned control loop.

## Current Status To Say Clearly

Done:

```text
- MuJoCo training and deployable v2_30k candidate selection
- ONNX export and parity checking
- ST Edge AI generation
- STM32H747 M7 smoke ELF build
- OpenCatEsp32 RL protocol patch
- Bittle X V2 firmware flash
- RL_GET_STATE telemetry verification
- first neutral RL_SET_TARGETS command accepted
```

Not done yet:

```text
- complete single-joint mapping on real Bittle
- low-amplitude scripted gait on real Bittle
- learned policy walking on real Bittle
- final STM32-to-Bittle closed-loop hardware demo
```

This distinction is useful in an interview. It shows engineering honesty and a
clear next-step plan.

## Why A Small MLP

Use this answer:

```text
I chose a small MLP because the deployment target is an STM32H747. For a
real-time control loop, deterministic latency, small RAM, and easy numerical
verification matter more than model size. The policy input is structured
low-dimensional telemetry, not images or language, so a two-layer 64-unit MLP is
reasonable. It keeps weights around 24 KiB and activations around 512 B after ST
Edge AI generation, which is comfortable for an H7-class MCU.
```

Key numbers:

```text
parameters: 6,216 float32 items
weights: 24,864 B
activations: 512 B
MACC: 7,512
estimated total flash: 27,794 B
estimated total RAM: 512 B
```

## ONNX Export And Validation

Answer shape:

```text
I export only the actor, not the full PPO training object. Then I run the same
fixed observation vector through the original actor and the ONNX Runtime model.
The report checks output shape, max absolute error, and representative output
values. The same policy vector is reused later for STM32-side verification, so
the test follows the model across the deployment pipeline.
```

Useful commands:

```bash
bash scripts/export_policy.sh training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2.yaml \
  --model training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2_30000_steps.zip \
  --output models/onnx/petoi_bittle_v0_gait_quality_v2_30k_actor.onnx \
  --report models/reports/petoi_bittle_v0_gait_quality_v2_30k_actor_onnx.json \
  --vector-output firmware/stm32h747_disco/test_vectors/gait_quality_v2_30k_policy_vector.json
```

## ST Edge AI Generation

Answer shape:

```text
After ONNX export, I use ST Edge AI to generate C inference code for STM32H7.
The important part is not just generation, but checking the generated report:
weights, activations, MACC, and target compatibility. Then I link a smoke
application for STM32H747 M7 to prove the generated runtime can be built in the
embedded toolchain.
```

Useful commands:

```bash
bash scripts/generate_stedgeai.sh models/onnx/petoi_bittle_v0_gait_quality_v2_30k_actor.onnx
bash scripts/build_stm32_m7_smoke.sh
```

Current M7 smoke ELF:

```text
build/stm32h747_m7_inference_smoke/m7_inference_smoke.elf
text: 30616
data: 1072
bss: 5944
```

## How MCU Output Becomes Robot Control

The policy does not directly drive PWM. The intended runtime chain is:

```text
Bittle telemetry
-> STM32 observation[23]
-> actor inference output action[8]
-> clamp and reconstruct joint targets
-> binary command packet
-> OpenCat RL_SET_TARGETS
-> OpenCat calibratedPWM / servo layer
```

Safety logic belongs at multiple layers:

```text
STM32:
  observation freshness check
  action clamp
  target step limit
  roll/pitch abort gate
  fallback to neutral/zero action

OpenCat/Bittle:
  CRC and payload validation
  finite-value check
  angleLimit[] rejection
  command_accepted/internal_fault status response
```

## Why Reinforcement Learning Is Still Useful

A hand gait prior can make the robot move, but it does not automatically optimize
stability, slip, body motion, or robustness under the chosen observation/action
interface. In this project the RL policy is residual around a gait prior, so it
does not start from nothing. The point is to learn corrections that improve the
motion under simulation metrics and then deploy the compact correction policy to
an MCU.

Current simulation evidence:

```text
hand gait prior: distance_x_mean=0.4250
deployable 10k:  distance_x_mean=1.2671
gait v2 30k:     distance_x_mean=1.4290
fall_rate:       0.0 for all three comparison runs
```

This does not prove final real-world superiority over mature Petoi/OpenCat
official gait. The honest next step is hardware joint mapping, then low-amplitude
scripted gait, then learned policy trials.

## Safety Story

Use this in interviews:

```text
I treat learned control as the last step, not the first. The hardware sequence is
read-only telemetry, neutral target, one-joint tests, low-amplitude scripted
motion, then learned policy. Every motion command requires explicit
--allow-motion. The OpenCat side rejects invalid target packets and out-of-limit
angles. The STM32 side is designed to add freshness checks, clamps, step limits,
and roll/pitch aborts before connecting policy output to the robot.
```

Concrete current hardware result:

```text
RL_GET_STATE: telemetry_valid
first neutral RL_SET_TARGETS: command_accepted
next step: single-joint mapping, index 1 onward
```

## Likely Interview Questions

Q: Why use `sin(phase)` and `cos(phase)` instead of raw phase?

A:

```text
Raw phase jumps discontinuously from 1 back to 0 at the cycle boundary.
sin/cos gives a continuous circular representation, so the network sees nearby
values at the wrap-around point. It also lets the network infer phase angle
without learning the discontinuity.
```

Q: What exactly are the 23 inputs?

A:

```text
roll, pitch, angular velocity x/y/z, 8 joint angles, previous_action[8],
sin(2*pi*phase), cos(2*pi*phase).
```

Q: Why not a bigger model?

A:

```text
The input is low-dimensional robot telemetry, and the target is an MCU real-time
loop. A small MLP gives deterministic latency, easy memory budgeting, and easy
test-vector verification. Bigger is not automatically better for this control
interface.
```

Q: How do you prove generated C is consistent?

A:

```text
Use fixed test vectors. Compare original actor, ONNX output, and generated
runtime output within tolerance. Keep the same vector in the repo so regressions
are easy to catch.
```

Q: What if the model outputs unsafe values?

A:

```text
The model output is not trusted directly. It is clamped, rate-limited, converted
to joint targets, checked against safety gates, and the OpenCat side also rejects
out-of-range targets. The fallback is neutral/zero action.
```

Q: What remains before a final demo?

A:

```text
Complete real-machine joint mapping, verify low-amplitude scripted gait, connect
STM32 output to OpenCat command path, then test the learned policy under strict
safety limits.
```

## Files To Review Before Interview

```text
README.md
docs/handoff.md
docs/training_status.md
docs/deployable_v0_interface.md
docs/bittle_flash_bringup.md
firmware/stm32h747_disco/test_vectors/gait_quality_v2_30k_policy_vector.json
models/reports/petoi_bittle_v0_gait_quality_v2_30k_actor_onnx.json
```

## Suggested Prep Plan

Before 2026-05-27:

```text
Day 1:
  Read the 2-minute pitch, 5-minute version, and current-status section aloud.
  Make sure every claim is something already done in the repo.

Day 2:
  Review ONNX export, ST Edge AI generation, resource usage, and test-vector
  verification. Be ready to explain why the deployment chain is trustworthy.

Day 3:
  Review safety, OpenCat protocol, and remaining hardware work. Practice saying
  what is done and what is not done without sounding defensive.

Interview day:
  Rehearse the 2-minute pitch once.
  Keep the numbers in mind: 23 inputs, 8 outputs, 64/64 MLP, 6,216 parameters,
  24.28 KiB weights, 512 B activations, 7,512 MACC.
```
