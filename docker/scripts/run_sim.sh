#!/usr/bin/env bash
# Run Khronos on a simulated dataset (uHumans2 / tesse_cd).
# Usage (inside container): BAG_DIR=/data/bags DATASET=tesse_cd_office ./run_sim.sh
set -eo pipefail

source /root/ros2_ws/install/setup.bash

BAG_DIR="${BAG_DIR:-/data/bags}"
DATASET="${DATASET:-tesse_cd_office}"   # tesse_cd_office | tesse_cd_apartment
RUN_ID="${RUN_ID:-$(date +%Y_%m_%d-%H_%M_%S)}"

echo "Playing dataset '${DATASET}' from '${BAG_DIR}'"
echo "Output dir: /root/output/${RUN_ID}  (host: ~/khronos_data/output/${RUN_ID})"
ros2 launch khronos_ros uhumans2_khronos.launch.yaml \
    bag_dir:="$BAG_DIR" \
    dataset:="$DATASET" \
    output_dir:=/root/output/"$RUN_ID"
