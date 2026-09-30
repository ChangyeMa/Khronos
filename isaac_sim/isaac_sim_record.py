#!/usr/bin/env python3
# Record RGB + depth + GT semantic labels + camera_info + TF from Isaac Sim to
# ROS2 topics. Run from the Isaac Sim python environment (host), and record the
# topics with `ros2 bag record` in parallel (see README.md).
#
# Topics published (node namespace default "/isaac"):
#   /isaac/rgb/image_raw          sensor_msgs/Image (rgb8)
#   /isaac/depth/image_raw        sensor_msgs/Image (32FC1 meters)
#   /isaac/semantic/image_raw     sensor_msgs/Image (semantic ids)
#   /isaac/camera_info            sensor_msgs/CameraInfo
#   /tf                           tf2_msgs/TFMessage (world -> camera)

import argparse
import math

from isaacsim import SimulationApp

CAMERA_STAGE_PATH = "/World/carter_v1/chassis_link/camera_mount/carter_camera_first_person"
ROS_CAMERA_GRAPH_PATH = "/ROS_Camera"
# User-created world (warehouse + Carter robot).
USER_WORLD_PATH = "/home/jiaming/AMR/isaac_tutorials/isaac_world_test.usd"

parser = argparse.ArgumentParser(description="Record Isaac Sim RGB-D + semantic to ROS2")
parser.add_argument("--headless", action="store_true", help="Run without the GUI")
parser.add_argument("--test", action="store_true", help="Drive a fixed non-circular path and exit (verification)")
parser.add_argument("--frames", type=int, default=120, help="Number of frames in --test mode")
args = parser.parse_args()

CONFIG = {"renderer": "RaytracedLighting", "headless": args.headless}

simulation_app = SimulationApp(CONFIG)
import omni
import omni.graph.core as og
import usdrt.Sdf
from isaacsim.core.api import SimulationContext
from isaacsim.core.utils import extensions
from isaacsim.core.utils.stage import is_stage_loading
from pxr import Gf, Usd, UsdGeom

# ROS2 (bundled with isaacsim.ros2.bridge; NOT the system rclpy).
import rclpy
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from tf2_msgs.msg import TFMessage

import numpy as np
from isaacsim.core.utils.types import ArticulationAction
from isaacsim.robot.wheeled_robots.robots import WheeledRobot

extensions.enable_extension("isaacsim.ros2.bridge")
simulation_app.update()

# Open the user-created warehouse + Carter robot world FIRST, then create the
# SimulationContext: open_stage invalidates any pre-existing World/context.
omni.usd.get_context().open_stage(USER_WORLD_PATH)
# Wait for the stage (warehouse + Carter payloads) to finish loading.
while is_stage_loading():
    simulation_app.update()

simulation_context = SimulationContext(stage_units_in_meters=1.0)

# Use the Carter's built-in first-person camera (already mounted + oriented).
camera_prim = UsdGeom.Camera(
    omni.usd.get_context().get_stage().GetPrimAtPath(CAMERA_STAGE_PATH)
)
camera_xformable = UsdGeom.Xformable(camera_prim)
camera_prim.GetClippingRangeAttr().Set(Gf.Vec2f(0.1, 100.0))

simulation_app.update()

# ---------------------------------------------------------------------------
# ROS2 graph: publish RGB + depth + semantic + camera_info.
# ---------------------------------------------------------------------------
keys = og.Controller.Keys
(ros_camera_graph, _, _, _) = og.Controller.edit(
    {
        "graph_path": ROS_CAMERA_GRAPH_PATH,
        "evaluator_name": "push",
        "pipeline_stage": og.GraphPipelineStage.GRAPH_PIPELINE_STAGE_ONDEMAND,
    },
    {
        keys.CREATE_NODES: [
            ("OnTick", "omni.graph.action.OnTick"),
            ("createViewport", "isaacsim.core.nodes.IsaacCreateViewport"),
            ("getRenderProduct", "isaacsim.core.nodes.IsaacGetViewportRenderProduct"),
            ("setCamera", "isaacsim.core.nodes.IsaacSetCameraOnRenderProduct"),
            ("cameraHelperRgb", "isaacsim.ros2.bridge.ROS2CameraHelper"),
            ("cameraHelperInfo", "isaacsim.ros2.bridge.ROS2CameraHelper"),
            ("cameraHelperDepth", "isaacsim.ros2.bridge.ROS2CameraHelper"),
            ("cameraHelperSemantic", "isaacsim.ros2.bridge.ROS2CameraHelper"),
        ],
        keys.CONNECT: [
            ("OnTick.outputs:tick", "createViewport.inputs:execIn"),
            ("createViewport.outputs:execOut", "getRenderProduct.inputs:execIn"),
            ("createViewport.outputs:viewport", "getRenderProduct.inputs:viewport"),
            ("getRenderProduct.outputs:execOut", "setCamera.inputs:execIn"),
            ("getRenderProduct.outputs:renderProductPath", "setCamera.inputs:renderProductPath"),
            ("getRenderProduct.outputs:renderProductPath", "cameraHelperRgb.inputs:renderProductPath"),
            ("getRenderProduct.outputs:renderProductPath", "cameraHelperInfo.inputs:renderProductPath"),
            ("getRenderProduct.outputs:renderProductPath", "cameraHelperDepth.inputs:renderProductPath"),
            ("getRenderProduct.outputs:renderProductPath", "cameraHelperSemantic.inputs:renderProductPath"),
        ],
        keys.SET_VALUES: [
            ("createViewport.inputs:viewportId", 0),
            ("cameraHelperRgb.inputs:frameId", "camera"),
            ("cameraHelperRgb.inputs:topicName", "rgb/image_raw"),
            ("cameraHelperRgb.inputs:type", "rgb"),
            ("cameraHelperRgb.inputs:nodeNamespace", "isaac"),
            ("cameraHelperInfo.inputs:frameId", "camera"),
            ("cameraHelperInfo.inputs:topicName", "camera_info"),
            ("cameraHelperInfo.inputs:type", "camera_info"),
            ("cameraHelperInfo.inputs:nodeNamespace", "isaac"),
            ("cameraHelperDepth.inputs:frameId", "camera"),
            ("cameraHelperDepth.inputs:topicName", "depth/image_raw"),
            ("cameraHelperDepth.inputs:type", "depth"),
            ("cameraHelperDepth.inputs:nodeNamespace", "isaac"),
            ("cameraHelperSemantic.inputs:frameId", "camera"),
            ("cameraHelperSemantic.inputs:topicName", "semantic/image_raw"),
            ("cameraHelperSemantic.inputs:type", "semantic_segmentation"),
            ("cameraHelperSemantic.inputs:nodeNamespace", "isaac"),
            # Publish every other frame (~30 Hz at 60 FPS); requirement is >= 25 Hz.
            ("cameraHelperRgb.inputs:frameSkipCount", 1),
            ("cameraHelperInfo.inputs:frameSkipCount", 1),
            ("cameraHelperDepth.inputs:frameSkipCount", 1),
            ("cameraHelperSemantic.inputs:frameSkipCount", 1),
            ("setCamera.inputs:cameraPrim", [usdrt.Sdf.Path(CAMERA_STAGE_PATH)]),
        ],
    },
)

og.Controller.evaluate_sync(ros_camera_graph)
simulation_app.update()

# ---------------------------------------------------------------------------
# Clock publisher: publish /clock (sim time) so downstream nodes can use
# use_sim_time (Khronos relies on sim time for pose/TF lookups).
# ---------------------------------------------------------------------------
og.Controller.edit(
    {"graph_path": "/ClockGraph", "evaluator_name": "execution"},
    {
        keys.CREATE_NODES: [
            ("ReadSimTime", "isaacsim.core.nodes.IsaacReadSimulationTime"),
            ("OnPlaybackTick", "omni.graph.action.OnPlaybackTick"),
            ("PublishClock", "isaacsim.ros2.bridge.ROS2PublishClock"),
        ],
        keys.CONNECT: [
            ("OnPlaybackTick.outputs:tick", "PublishClock.inputs:execIn"),
            ("ReadSimTime.outputs:simulationTime", "PublishClock.inputs:timeStamp"),
        ],
        keys.SET_VALUES: [
            ("PublishClock.inputs:topicName", "/clock"),
        ],
    },
)

# ---------------------------------------------------------------------------
# TF publisher: world -> camera (GT pose) and camera -> camera (identity).
# ---------------------------------------------------------------------------
from rclpy.parameter import Parameter

rclpy.init()
tf_node = rclpy.create_node("isaac_sim_tf")
# Use sim time to match the images (ROS2CameraHelper stamps sim time).
tf_node.set_parameters([Parameter("use_sim_time", value=True)])
tf_pub = tf_node.create_publisher(TFMessage, "/tf", 10)
odom_pub = tf_node.create_publisher(Odometry, "/odom", 10)

# Carter robot control: subscribe to /cmd_vel (teleop_twist_keyboard) and drive
# the differential-drive robot.
CARTER_PRIM_PATH = "/World/carter_v1"
# Exact values read from the Carter_v1 USD geometry:
#   wheel cylinder base radius = 0.5, radial scale = 0.48  ->  0.5 * 0.48 = 0.24 m
#   left/right wheel cylinder centers at Y = +/-0.269206 m -> track width = 0.538412 m
CARTER_WHEEL_RADIUS = 0.24  # m
CARTER_TRACK_WIDTH = 0.538  # m

cmd_vel = [0.0, 0.0]  # [linear_x (m/s), angular_z (rad/s)]


def cmd_vel_callback(msg):
    global cmd_vel
    cmd_vel = [msg.linear.x, msg.angular.z]


tf_node.create_subscription(Twist, "/cmd_vel", cmd_vel_callback, 10)


def publish_tf(translate, quat):
    """Publish the world -> camera transform with the camera's full pose."""
    msg = TFMessage()
    now = tf_node.get_clock().now().to_msg()

    t = TransformStamped()
    t.header.frame_id = "world"
    t.header.stamp = now
    t.child_frame_id = "camera"
    t.transform.translation.x = float(translate[0])
    t.transform.translation.y = float(translate[1])
    t.transform.translation.z = float(translate[2])
    t.transform.rotation.w = float(quat.GetReal())
    t.transform.rotation.x = float(quat.GetImaginary()[0])
    t.transform.rotation.y = float(quat.GetImaginary()[1])
    t.transform.rotation.z = float(quat.GetImaginary()[2])
    msg.transforms.append(t)

    tf_pub.publish(msg)

    # Also publish /odom (nav_msgs/Odometry), which Khronos's pose-graph
    # tracker consumes (the Isaac Sim bag otherwise has no odometry source).
    odom = Odometry()
    odom.header.stamp = now
    odom.header.frame_id = "world"
    odom.child_frame_id = "camera"
    odom.pose.pose.position.x = float(translate[0])
    odom.pose.pose.position.y = float(translate[1])
    odom.pose.pose.position.z = float(translate[2])
    odom.pose.pose.orientation.w = float(quat.GetReal())
    odom.pose.pose.orientation.x = float(quat.GetImaginary()[0])
    odom.pose.pose.orientation.y = float(quat.GetImaginary()[1])
    odom.pose.pose.orientation.z = float(quat.GetImaginary()[2])
    odom_pub.publish(odom)


simulation_context.initialize_physics()

# Create + initialize the Carter robot for /cmd_vel control.
carter = WheeledRobot(
    prim_path=CARTER_PRIM_PATH,
    name="carter",
    wheel_dof_names=["left_wheel", "right_wheel"],
)
carter.initialize()

simulation_context.play()

frame = 0

while simulation_app.is_running():
    simulation_context.step(render=True)
    rclpy.spin_once(tf_node, timeout_sec=0.0)

    if simulation_context.is_playing():
        if args.test:
            # Fixed non-circular test path: straight, then turn in place.
            cmd_vel = [0.5, 0.0] if frame < args.frames * 0.5 else [0.0, 0.5]

        # Drive the Carter robot from the latest /cmd_vel.
        linear_x = cmd_vel[0]
        angular_z = cmd_vel[1]
        v_left = (linear_x - angular_z * CARTER_TRACK_WIDTH / 2.0) / CARTER_WHEEL_RADIUS
        v_right = (linear_x + angular_z * CARTER_TRACK_WIDTH / 2.0) / CARTER_WHEEL_RADIUS
        carter.apply_wheel_actions(
            ArticulationAction(joint_velocities=np.array([v_left, v_right]))
        )

        # The Carter's first-person camera already follows the robot; read its pose.
        cam_mat = camera_xformable.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        camera_pos = cam_mat.ExtractTranslation()
        camera_usd_rot = cam_mat.ExtractRotation()

        # ROS camera frame is +Z forward / +Y down, i.e. the USD frame rotated
        # 180 deg about X. Publish that pose so Khronos sees yaw as yaw, not roll.
        ros_conv = Gf.Rotation(Gf.Quatd(0.0, 1.0, 0.0, 0.0))
        camera_ros_rot = ros_conv * camera_usd_rot
        camera_quat = camera_ros_rot.GetQuat()

        publish_tf(camera_pos, camera_quat)
        frame += 1

        if args.test:
            if frame % 10 == 0:
                _, carter_quat = carter.get_world_pose()
                carter_yaw = math.atan2(
                    2.0 * (carter_quat[0] * carter_quat[3] + carter_quat[1] * carter_quat[2]),
                    1.0 - 2.0 * (carter_quat[2] * carter_quat[2] + carter_quat[3] * carter_quat[3]),
                )
                with open("/tmp/camera_test.log", "a") as f:
                    f.write(
                        f"frame={frame} pos=({camera_pos[0]:.3f}, {camera_pos[1]:.3f}, {camera_pos[2]:.3f}) "
                        f"yaw={math.degrees(carter_yaw):.1f}\n"
                    )
            if frame >= args.frames:
                break

simulation_context.stop()
tf_node.destroy_node()
rclpy.shutdown()
simulation_app.close()
