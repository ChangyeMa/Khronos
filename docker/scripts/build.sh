#!/usr/bin/env bash
# Build Khronos + all source dependencies inside the container.
# Re-runnable: skips clone if already present.
set -euo pipefail

WS="${WS:-/root/ros2_ws}"
KHRONOS_URI="${KHRONOS_URI:-https://github.com/ChangyeMa/Khronos.git}"
KHRONOS_BRANCH="${KHRONOS_BRANCH:-main}"

mkdir -p "$WS/src"
cd "$WS"

if [ ! -d "$WS/src/khronos/.git" ]; then
    echo "==> Cloning Khronos (${KHRONOS_URI} @ ${KHRONOS_BRANCH})"
    git clone -b "$KHRONOS_BRANCH" "$KHRONOS_URI" "$WS/src/khronos"
fi

echo "==> Importing source dependencies (vcs)"
vcs import "$WS/src" < "$WS/src/khronos/install/https.rosinstall"

echo "==> rosdep update"
rosdep update || true

echo "==> Refreshing apt package lists"
apt-get update || true

echo "==> Installing system dependencies via rosdep"
# --ignore-src : don't try to resolve our source packages
# -r           : continue on errors (custom MIT-SPARK deps are not rosdep keys)
rosdep install --from-paths "$WS/src" --ignore-src -r -y || true

echo "==> colcon build (Release)"
cd "$WS"
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

echo "==> Build finished. Source with: source $WS/install/setup.bash"
