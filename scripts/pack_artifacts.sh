#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ARTIFACT_OUTPUT_DIR:-${ROOT_DIR}/artifacts}"
INCLUDE_OPTIONAL=0
NAME_PREFIX="rl_petoi_artifacts"

usage() {
  cat <<'USAGE'
Usage: bash scripts/pack_artifacts.sh [options]

Create a milestone artifact archive for server migration or manual download.

Options:
  --output-dir DIR       Archive output directory. Default: artifacts/
  --name-prefix NAME     Archive name prefix. Default: rl_petoi_artifacts
  --include-optional     Include logs, all checkpoints, and rebuild caches.
  -h, --help             Show this help.

The default archive intentionally contains the current best policy candidate
and its deployment/evaluation evidence, not every intermediate training file.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --name-prefix)
      NAME_PREFIX="$2"
      shift 2
      ;;
    --include-optional)
      INCLUDE_OPTIONAL=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

cd "${ROOT_DIR}"

timestamp="$(date -u '+%Y%m%dT%H%M%SZ')"
git_sha="nogit"
git_dirty="unknown"
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git_sha="$(git rev-parse --short HEAD)"
  if git diff --quiet --ignore-submodules -- && git diff --cached --quiet --ignore-submodules --; then
    git_dirty="false"
  else
    git_dirty="true"
  fi
fi

required_paths=(
  "training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0/final_model.zip"
  "training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue_10000_steps.zip"
  "training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2_30000_steps.zip"
  "models/onnx/petoi_bittle_v0_deployable_v0_best_actor.onnx"
  "models/reports/petoi_bittle_v0_deployable_v0_best_actor_onnx.json"
  "experiments/reports/checkpoint_eval"
  "experiments/reports/action_analysis"
  "experiments/reports/gait_contact_analysis"
  "experiments/reports/gait_baseline_comparison"
  "assets/videos/petoi_bittle_v0_deployable_v0_10k_rollout.mp4"
  "assets/videos/petoi_bittle_v0_gait_quality_v2_30k_rollout_track.mp4"
  "assets/videos/gait_compare_A_hand_gait_prior_track.mp4"
  "assets/videos/gait_compare_B_deployable_10k_track.mp4"
  "assets/videos/gait_compare_C_gait_quality_v2_30k_track.mp4"
  "firmware/stm32h747_disco/test_vectors/deployable_v0_policy_vector.json"
  "README.md"
  "docs/training_status.md"
  "docs/artifact_backup.md"
  "docs/hardware_bringup_checklist.md"
  "experiments/petoi_bittle_v0_gait_diagnosis.md"
  "experiments/gait_baseline_comparison.md"
)

optional_paths=(
  "training/logs"
  "training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0"
  "training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue"
  "training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v1"
  "training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2"
  "models"
  "assets/videos"
  "build/petoi_bittle"
  "build/stedgeai/generate"
  "build/stm32h747_m7_inference_smoke"
)

archive_paths=()
for path in "${required_paths[@]}"; do
  if [[ ! -e "${path}" ]]; then
    echo "Missing required artifact: ${path}" >&2
    echo "Run the relevant training/export/recording step before packing." >&2
    exit 1
  fi
  archive_paths+=("${path}")
done

if [[ "${INCLUDE_OPTIONAL}" -eq 1 ]]; then
  for path in "${optional_paths[@]}"; do
    if [[ -e "${path}" ]]; then
      archive_paths+=("${path}")
    fi
  done
fi

mkdir -p "${OUTPUT_DIR}"
tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/rl_petoi_artifacts.XXXXXX")"
cleanup() {
  rm -rf "${tmp_dir}"
}
trap cleanup EXIT

manifest="${tmp_dir}/ARTIFACT_MANIFEST.txt"
{
  printf 'created_at_utc=%s\n' "${timestamp}"
  printf 'project_root=%s\n' "${ROOT_DIR}"
  printf 'git_sha=%s\n' "${git_sha}"
  printf 'git_dirty=%s\n' "${git_dirty}"
  printf 'include_optional=%s\n' "${INCLUDE_OPTIONAL}"
  printf 'best_checkpoint=%s\n' "training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue_10000_steps.zip"
  printf 'simulation_candidate=%s\n' "training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2_30000_steps.zip"
  printf 'best_onnx=%s\n' "models/onnx/petoi_bittle_v0_deployable_v0_best_actor.onnx"
  printf 'best_video=%s\n' "assets/videos/petoi_bittle_v0_deployable_v0_10k_rollout.mp4"
  printf 'simulation_candidate_video=%s\n' "assets/videos/petoi_bittle_v0_gait_quality_v2_30k_rollout_track.mp4"
  printf 'baseline_comparison_report=%s\n' "experiments/gait_baseline_comparison.md"
  printf '\n[included_paths]\n'
  printf '%s\n' "${archive_paths[@]}"
  printf '\n[sha256]\n'
  for path in "${archive_paths[@]}"; do
    if [[ -f "${path}" ]]; then
      sha256sum "${path}"
    elif [[ -d "${path}" ]]; then
      find "${path}" -type f -print0 | sort -z | xargs -0 sha256sum
    fi
  done
} > "${manifest}"

if command -v zstd >/dev/null 2>&1; then
  archive="${OUTPUT_DIR}/${NAME_PREFIX}_${timestamp}_${git_sha}.tar.zst"
  tar --zstd -cf "${archive}" -C "${tmp_dir}" "ARTIFACT_MANIFEST.txt" -C "${ROOT_DIR}" "${archive_paths[@]}"
elif gzip --version >/dev/null 2>&1; then
  archive="${OUTPUT_DIR}/${NAME_PREFIX}_${timestamp}_${git_sha}.tar.gz"
  tar -czf "${archive}" -C "${tmp_dir}" "ARTIFACT_MANIFEST.txt" -C "${ROOT_DIR}" "${archive_paths[@]}"
else
  archive="${OUTPUT_DIR}/${NAME_PREFIX}_${timestamp}_${git_sha}.tar"
  tar -cf "${archive}" -C "${tmp_dir}" "ARTIFACT_MANIFEST.txt" -C "${ROOT_DIR}" "${archive_paths[@]}"
fi

printf 'Created artifact archive:\n'
printf '  %s\n' "${archive}"
printf '\nArchive size:\n'
du -h "${archive}"
printf '\nManifest preview:\n'
sed -n '1,40p' "${manifest}"
