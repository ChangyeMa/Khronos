#!/usr/bin/env bash
# Run Khronos on the real Jackal (mezzanine) dataset.
# Usage (inside container): BAG_DIR=/data/bags DATASET=khronos_mezzanine_long2_w_semantics ./run_jackal.sh
set -eo pipefail

source /root/ros2_ws/install/setup.bash

BAG_DIR="${BAG_DIR:-/data/bags}"
DATASET="${DATASET:-khronos_mezzanine_long2_w_semantics}"
RUN_ID="${RUN_ID:-$(date +%Y_%m_%d-%H_%M_%S)}"

echo "Playing dataset '${DATASET}' from '${BAG_DIR}'"
echo "Output dir: /root/output/${RUN_ID}  (host: ~/khronos_data/output/${RUN_ID})"
ros2 launch khronos_ros jackal_khronos.launch.yaml \
    bag_dir:="$BAG_DIR" \
    dataset:="$DATASET" \
    output_dir:=/root/output/"$RUN_ID" \
    use_prerecorded_semantics:=true
