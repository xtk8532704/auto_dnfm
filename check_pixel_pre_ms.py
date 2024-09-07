import cv2
import numpy as np

# 读取视频
cap = cv2.VideoCapture('./test/Record_2024-09-08-03-37-03.mp4')

# 获取视频的帧率
fps = cap.get(cv2.CAP_PROP_FPS)
frame_time = 1 / fps

start_time = 2  # 开始时间
end_time = 4    # 结束时间

# 计算开始帧和结束帧
start_frame = int(start_time * fps)
end_frame = int(end_time * fps)
cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

# 读取第一帧并转换为灰度图像
ret, prev_frame = cap.read()
prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)

# 设定一个位移阈值
displacement_threshold = 10.0

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
        avg_speed = np.mean(magnitude[moving_pixels]) / frame_time
        current_time = current_frame / fps
        print(
            f'Average speed of moving pixels at {current_time:.2f} seconds: {avg_speed} pixels/second')
    else:
        current_time = current_frame / fps
        print(f'No moving pixels detected at {current_time:.2f} seconds')

    # 更新上一帧
    prev_gray = gray
    current_frame += 1

cap.release()
cv2.destroyAllWindows()
