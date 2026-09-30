import sys
import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import Image, CameraInfo
from tf2_msgs.msg import TFMessage

uri = "/data/bags/isaac_sim"
reader = rosbag2_py.SequentialReader()
reader.open(rosbag2_py.StorageOptions(uri=uri, storage_id="sqlite3"),
            rosbag2_py.ConverterOptions(input_serialization_format="cdr", output_serialization_format="cdr"))

info = None
tf_poses = []
img_stamps = []
while reader.has_next():
    (topic, data, t) = reader.read_next()
    if topic == "/isaac/camera_info" and info is None:
        m = deserialize_message(data, CameraInfo)
        info = m
    elif topic == "/tf" and len(tf_poses) < 6:
        m = deserialize_message(data, TFMessage)
        for tr in m.transforms:
            tf_poses.append((t, tr.header.frame_id, tr.child_frame_id,
                             round(tr.transform.translation.x,3), round(tr.transform.translation.y,3), round(tr.transform.translation.z,3),
                             round(tr.transform.rotation.w,3), round(tr.transform.rotation.x,3), round(tr.transform.rotation.y,3), round(tr.transform.rotation.z,3)))
    elif topic == "/isaac/rgb/image_raw" and len(img_stamps) < 4:
        m = deserialize_message(data, Image)
        img_stamps.append((t, m.encoding, m.width, m.height))
    if info and len(tf_poses) >= 6 and len(img_stamps) >= 4:
        break

print("CAMERA_INFO:")
if info:
    print("  width", info.width, "height", info.height, "frame", info.header.frame_id)
    print("  K", [round(x,2) for x in info.k])
print("RGB_IMAGES:")
for s in img_stamps:
    print("  t=", s[0], s[1], s[2], "x", s[3])
print("TF_POSES:")
for p in tf_poses:
    print("  t=", p[0], p[1], "->", p[2], "trans", p[3:6], "quat", p[6:10])
