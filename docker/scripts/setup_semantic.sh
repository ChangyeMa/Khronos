#!/usr/bin/env bash
# Set up the semantic_inference open-set Python environment (FastSAM + CLIP).
# This is a pip install (not a colcon build). The venv persists under /root/ros2_ws
# (mounted from ~/khronos_data/ros2_ws), so it survives container restarts.
set -eo pipefail

VENV="${SEMANTIC_VENV:-/root/ros2_ws/semantic_venv}"
PKG_DIR="/root/ros2_ws/src/semantic_inference/semantic_inference"

if [ ! -x "$VENV/bin/python" ]; then
    echo "==> Creating virtualenv at $VENV (--system-site-packages so rclpy is visible)"
    python3 -m venv --system-site-packages "$VENV"
fi

source "$VENV/bin/activate"

echo "==> Upgrading pip"
python -m pip install --upgrade pip

echo "==> Installing semantic_inference[openset] (torch, torchvision, ultralytics, clip, ...)"
python -m pip install -e "${PKG_DIR}[openset]"

echo "==> Verifying import"
python -c "import semantic_inference; print('semantic_inference import OK')"

echo "==> Done. Activate with: source $VENV/bin/activate"
