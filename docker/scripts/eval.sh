#!/usr/bin/env bash
# Run the offline accuracy evaluation on a completed Khronos experiment.
# Usage (inside container): ./eval.sh /root/output/<timestamp> [office.yaml]
set -eo pipefail

source /root/ros2_ws/install/setup.bash

EXPERIMENT_DIR="${1:?usage: eval.sh <experiment_output_dir> [config]}"
CONFIG="${2:-office.yaml}"   # office.yaml | apartment.yaml

pkg_path=$(ros2 pkg prefix khronos_eval)
exec_dir="$pkg_path/lib/khronos_eval"
config_path="$pkg_path/share/khronos_eval/config/pipeline/$CONFIG"

echo "==> Evaluating '${EXPERIMENT_DIR}' with '${CONFIG}'"
exec "$exec_dir/exp_pipeline" "$config_path" "$EXPERIMENT_DIR" true true false

echo "==> Evaluation done. Results in: ${EXPERIMENT_DIR}/results"
