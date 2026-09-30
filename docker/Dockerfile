# Khronos benchmark environment (ROS2 Jazzy / Ubuntu 24.04)
# Khronos officially supports Jazzy; it will NOT build on Humble or older.
FROM osrf/ros:jazzy-desktop

ENV DEBIAN_FRONTEND=noninteractive

# Build toolchain + system deps for Khronos and its source dependencies
# (Hydra, Kimera-PGMO, Spark-DSG, config_utilities, spatial_hash, TEASER++, ianvs, ...).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        wget \
        python3-pip \
        python3-venv \
        python3-vcstool \
        python3-rosdep \
        python3-colcon-common-extensions \
        python3-tk \
        ros-jazzy-gtsam \
        ros-jazzy-cv-bridge \
        ros-jazzy-tf2-ros \
        ros-jazzy-std-srvs \
        ros-jazzy-image-transport \
        libgoogle-glog-dev \
        libgflags-dev \
        nlohmann-json3-dev \
        libeigen3-dev \
        libopencv-dev \
        libpcl-dev \
        liboctomap-dev \
        libcli11-dev \
        libzmq3-dev \
        cppzmq-dev \
        python3-imageio \
        python3-tqdm \
        python3-flask \
        ros-jazzy-image-transport-plugins \
    && rm -rf /var/lib/apt/lists/*

# Initialize rosdep (the osrf image may already have done this).
RUN rosdep init || true && rosdep update || true

# CUDA + TensorRT for closed-set (ADE20k) semantic segmentation.
RUN wget -q https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb -O /tmp/cuda-keyring.deb \
    && dpkg -i /tmp/cuda-keyring.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        libnvinfer-dev libnvonnxparsers-dev libnvinfer-plugin-dev \
        cuda-nvcc-12-6 \
    && rm -rf /var/lib/apt/lists/* /tmp/cuda-keyring.deb

# Allow git to operate on bind-mounted repos owned by the host user, so
# Khronos can record git hash/status at runtime (avoid "dubious ownership").
RUN git config --global --add safe.directory '*'

WORKDIR /root/ros2_ws

CMD ["bash"]
