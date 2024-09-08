import cv2
import numpy as np
from collections import deque
# 读取视频
# x轴
# cap = cv2.VideoCapture('./test/Record_2024-09-08-03-37-03.mp4')
# start_time = 2
# end_time = 4
cap = cv2.VideoCapture('./test/Record_2024-09-08-20-03-33.mp4')  # y轴
start_time = 5  # 1.5
end_time = 8  # 4

# 获取视频的帧率
fps = cap.get(cv2.CAP_PROP_FPS)
frame_time = 1 / fps

# 获取视频帧的宽度和高度
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# 计算开始帧和结束帧
start_frame = int(start_time * fps)
end_frame = int(end_time * fps)
cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

# 读取第一帧并转换为灰度图像
ret, prev_frame = cap.read()
if not ret:
    raise ValueError("无法读取视频的第一帧")
prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)

# 设定一个位移阈值
displacement_threshold = 10.0

# 滑动窗口队列
window_size = 6
speed_queue = deque(maxlen=window_size)

current_frame = start_frame
while cap.isOpened() and current_frame <= end_frame:
    ret, frame = cap.read()
    if not ret:
        break

    # 转换为灰度图像
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # 计算光流
    flow = cv2.calcOpticalFlowFarneback(
        prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)

    # 计算光流的幅度和方向
    magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])

    # 过滤出移动的像素
    moving_pixels = magnitude > displacement_threshold

    # 计算移动像素的平均速度
    if np.any(moving_pixels):
        avg_speed_x = np.mean(flow[..., 0][moving_pixels])
        avg_speed_y = np.mean(flow[..., 1][moving_pixels])

        # 归一化速度
        normalized_speed_x = avg_speed_x / frame_width
        normalized_speed_y = avg_speed_y / frame_height

        # 计算总速度
        total_speed = np.sqrt(normalized_speed_x**2 + normalized_speed_y**2)

        # 将总速度添加到滑动窗口队列
        speed_queue.append(total_speed)

        # 计算滑动窗口的平均总速度
        if len(speed_queue) == window_size:
            avg_total_speed = np.mean(speed_queue)
            avg_total_speed_per_sec = avg_total_speed * fps
            print(
                f"帧 {current_frame}: 平均速度 = {avg_total_speed:.4f} ({avg_total_speed_per_sec:.4f} /s)")

    # 更新前一帧
    prev_gray = gray
    current_frame += 1

cap.release()
