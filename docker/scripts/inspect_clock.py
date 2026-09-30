import rosbag2_py
from rclpy.serialization import deserialize_message
from rosgraph_msgs.msg import Clock
from tf2_msgs.msg import TFMessage
from sensor_msgs.msg import Image

uri = "/data/bags/isaac_sim"
reader = rosbag2_py.SequentialReader()
reader.open(rosbag2_py.StorageOptions(uri=uri, storage_id="sqlite3"), rosbag2_py.ConverterOptions(input_serialization_format="cdr", output_serialization_format="cdr"))
clocks, tfs, imgs = [], [], []
while reader.has_next():
    topic, data, t = reader.read_next()
    if topic == "/clock" and len(clocks) < 5:
        m = deserialize_message(data, Clock)
        clocks.append(m.clock.sec + m.clock.nanosec*1e-9)
    elif topic == "/tf" and len(tfs) < 5:
        tfs.append(t)
    elif topic == "/isaac/rgb/image_raw" and len(imgs) < 5:
        imgs.append(t)
    if len(clocks) >= 5 and len(tfs) >= 5 and len(imgs) >= 5:
        break
print("CLOCK (sec):", clocks)
print("TF t (sec):", [x/1e9 for x in tfs])
print("IMG t (sec):", [x/1e9 for x in imgs])
