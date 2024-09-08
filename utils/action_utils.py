import cv2
import math
import numpy as np


def calculate_box_center(box):  # 计算矩形框的中心点坐标
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)


def calculate_center(box):  # 计算矩形框的底边中心点坐标
    return ((box[0] + box[2]) / 2, box[3])


def calculate_distance(center1, center2):  # 计算两个底边中心点之间的欧几里得距离
    return math.sqrt((center1[0] - center2[0]) ** 2 + (center1[1] - center2[1]) ** 2)


def find_closest_box(boxes, target_box):  # 计算目标框的中心点
    target_center = calculate_center(target_box)  # 初始化最小距离和最近的box
    min_distance = float('inf')
    closest_box = None  # 遍历所有box，找出最近的box
    for box in boxes:
        center = calculate_center(box)
        distance = calculate_distance(center, target_center)
        if distance < min_distance:
            min_distance = distance
            closest_box = box
    return closest_box, min_distance


def find_farthest_box(boxes, target_box):
    target_center = calculate_center(target_box)  # 计算目标框的中心点
    max_distance = -float('inf')  # 初始化最大距离和最远的box
    farthest_box = None
    for box in boxes:  # 遍历所有box，找出最远的box
        center = calculate_center(box)
        distance = calculate_distance(center, target_center)
        if distance > max_distance:
            max_distance = distance
            farthest_box = box
    return farthest_box, max_distance


def find_closest_or_second_closest_box(boxes, point):
    """找到离目标框最近的框或第二近的框"""
    if len(boxes) < 2:
        # 如果框的数量少于两个，直接返回最近的框
        target_center = point
        closest_box = None
        min_distance = float('inf')
        for box in boxes:
            center = calculate_center(box)
            distance = calculate_distance(center, target_center)
            if distance < min_distance:
                min_distance = distance
                closest_box = box
        return closest_box, distance
    # 如果框的数量不少于两个
    target_center = point
    # 初始化最小距离和最近的框
    min_distance_1 = float('inf')
    closest_box_1 = None
    # 初始化第二近的框
    min_distance_2 = float('inf')
    closest_box_2 = None
    for box in boxes:
        center = calculate_center(box)
        distance = calculate_distance(center, target_center)
        if distance < min_distance_1:
            # 更新第二近的框
            min_distance_2 = min_distance_1
            closest_box_2 = closest_box_1
            # 更新最近的框
            min_distance_1 = distance
            closest_box_1 = box
        elif distance < min_distance_2:
            # 更新第二近的框
            min_distance_2 = distance
            closest_box_2 = box
    # 返回第二近的框
    return closest_box_2, min_distance_2


def find_close_point_to_box(boxes, point):  # 找距离点最近的框
    target_center = point  # 初始化最小距离和最近的box
    min_distance = float('inf')
    closest_box = None  # 遍历所有box，找出最近的box
    for box in boxes:
        center = calculate_center(box)
        distance = calculate_distance(center, target_center)
        if distance < min_distance:
            min_distance = distance
            closest_box = box
    return closest_box, min_distance


def calculate_point_to_box_angle(point, box):  # 计算点到框的角度
    center1 = point
    center2 = calculate_center(box)
    delta_x = center2[0] - center1[0]  # 计算相对角度（以水平轴为基准）
    delta_y = center2[1] - center1[1]
    angle = math.atan2(delta_y, delta_x)
    angle_degrees = math.degrees(angle)  # 将角度转换为度数
    adjusted_angle = - angle_degrees
    return adjusted_angle


def calculate_angle(box1, box2):
    center1 = calculate_center(box1)
    center2 = calculate_center(box2)
    delta_x = center2[0] - center1[0]  # 计算相对角度（以水平轴为基准）
    delta_y = center2[1] - center1[1]
    angle = math.atan2(delta_y, delta_x)
    angle_degrees = math.degrees(angle)  # 将角度转换为度数
    adjusted_angle = - angle_degrees
    return adjusted_angle


def calculate_gate_angle(point, gate):
    center1 = point
    center2 = ((gate[0]+gate[2])/2, (gate[3]-gate[1])*0.65+gate[1])
    delta_x = center2[0] - center1[0]  # 计算相对角度（以水平轴为基准）
    delta_y = center2[1] - center1[1]
    angle = math.atan2(delta_y, delta_x)
    angle_degrees = math.degrees(angle)  # 将角度转换为度数
    adjusted_angle = - angle_degrees
    return adjusted_angle


def calculate_angle_to_box(point1, point2):  # 计算点到点的角度
    # 计算从点 (x, y) 到中心点的角度
    angle = math.atan2(point2[1] - point1[1], point2[0] - point1[0])
    angle_degrees = math.degrees(angle)  # 将角度转换为度数
    adjusted_angle = - angle_degrees
    return adjusted_angle


def calculate_iou(box1, box2):
    # 计算相交区域的坐标
    inter_x_min = max(box1[0], box2[0])
    inter_y_min = max(box1[1], box2[1])
    inter_x_max = min(box1[2], box2[2])
    inter_y_max = min(box1[3], box2[3])
    # 计算相交区域的面积
    inter_area = max(0, inter_x_max - inter_x_min) * \
        max(0, inter_y_max - inter_y_min)
    # 计算每个矩形的面积和并集面积
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union_area = box1_area + box2_area - inter_area
    # 计算并返回IoU
    return inter_area / union_area if union_area > 0 else 0


def normalize_angle(angle):  # 将角度规范化到 [-180, 180) 的范围内
    angle = angle % 360
    if angle >= 180:
        angle -= 360
    return angle


def are_angles_on_same_side_of_y(angle1, angle2):  # 规范化角度
    norm_angle1 = normalize_angle(angle1)
    norm_angle2 = normalize_angle(angle2)  # 检查是否在 y 轴的同侧
    return (norm_angle1 >= 0 and norm_angle2 >= 0) or (norm_angle1 < 0 and norm_angle2 < 0)


def is_image_almost_black(image, threshold=30):  # 读取图片
    image = cv2.cvtColor(image, cv2.IMREAD_GRAYSCALE)  # 检查图片是否成功读取
    num_black_pixels = np.sum(image < threshold)
    total_pixels = image.size
    black_pixel_ratio = num_black_pixels / total_pixels  # 定义一个比例阈值来判断图片是否接近黑色
    return black_pixel_ratio > 0.7


names = ['Monster',  # 0
         'Monster_ds',  # 1
         'Monster_szt',  # 2
         'card',  # 3
         'equipment',  # 4
         'go',  # 5
         'hero',  # 6
         'map',  # 7
         'opendoor_d',  # 8
         'opendoor_l',  # 9
         'opendoor_r',  # 10
         'opendoor_u',  # 11
         'pet',  # 12
         'Diamond']  # 13
