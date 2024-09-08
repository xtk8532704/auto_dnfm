import os
import time
import threading
import numpy as np
from collections import deque
from hero.naima import Naima
from game_control import GameControl
from utils.action_utils import calculate_center, calculate_box_center, calculate_distance, find_closest_or_second_closest_box, find_close_point_to_box, find_farthest_box, calculate_point_to_box_angle, calculate_gate_angle, calculate_angle_to_box, is_image_almost_black, calculate_point_to_box_angle, find_farthest_box
from utils.cv2_matcher import CV2Matcher


class GameAction:
    def __init__(self, ctrl: GameControl, queue):
        self.queue = queue
        self.ctrl = ctrl
        self.pre_state = True
        self.stop_event = True
        self.reset_event = False
        self.control_attack = Naima(ctrl)
        self.room_num = -1
        self.buwanjia = [8, 10, 10, 11, 9, 10, 10, 10, 10, 10, 10, 10, 10, 10]
        self.thread_run = True
        self.thread = threading.Thread(target=self.control)  # 创建线程，并指定目标函数
        self.thread.daemon = True  # 设置为守护线程（可选）
        self.thread.start()
        self.last_time = 0

        self.matcher = CV2Matcher(os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "./template.json"))

        self.special_command = None

    def reset(self):
        self.thread_run = False
        time.sleep(0.1)
        self.room_num = -1
        self.special_command = None
        self.pre_state = True
        self.thread_run = True
        self.thread = threading.Thread(target=self.control)  # 创建线程，并指定目标函数
        self.thread.daemon = True  # 设置为守护线程（可选）
        self.thread.start()

    def control(self):
        last_room_pos = []
        hero_track = deque()
        hero_track.appendleft([0, 0])

        while self.thread_run:
            # 等待数据
            if self.stop_event:
                time.sleep(0.001)
                self.ctrl.reset()
                continue
            if self.queue.empty():
                time.sleep(0.001)
                continue

            # 等待过图黑屏
            image, boxs = self.queue.get()
            if is_image_almost_black(image):
                if self.pre_state == False:
                    print("过图")
                    last_room_pos = hero_track[0]
                    hero_track = deque()
                    hero_track.appendleft(
                        [1-last_room_pos[0], 1-last_room_pos[1]])
                    self.ctrl.reset()
                    self.pre_state = True
                else:
                    continue

            # 预处理检测结果
            hero = boxs[boxs[:, 5] == 6][:, :4]
            gate = boxs[boxs[:, 5] == self.buwanjia[self.room_num]][:, :4]
            arrow = boxs[boxs[:, 5] == 5][:, :4]
            equipment = [[detection[0], detection[1] + (detection[3] - detection[1]), detection[2], detection[3] + (detection[3] - detection[1]), detection[4], detection[5]]
                         for detection in boxs if detection[5] == 4 and detection[4] > 0.3]
            monster = boxs[boxs[:, 5] <= 2][:, :4]
            card = boxs[boxs[:, 5] == 3][:, :4]
            Diamond = boxs[boxs[:, 5] == 13][:, :4]

            # 更新房间，目标门
            angle = 0
            outprint = ''
            if self.pre_state == True:
                if len(hero) > 0:  # 记录房间号
                    self.room_num += 1
                    self.pre_state = False
                    print("房间号：", self.room_num)
                    print("目标", self.buwanjia[self.room_num])
                else:
                    continue

            # 计算英雄位置
            self.calculate_hero_pos(hero_track, hero)

            # 计算时间间隔
            current_time = time.time()
            interval = current_time - self.last_time
            self.last_time = current_time

            # 过图逻辑
            if len(card) >= 8:
                time.sleep(1+np.random.rand())
                self.ctrl.click(0.25*image.shape[0], 0.25*image.shape[1])
                self.special_command = 'retry'
                time.sleep(2.5)
            if len(monster) > 0:
                outprint = '有怪物'
                angle = self.control_attack.control(
                    hero_track[0], image, boxs, self.room_num)
            elif len(equipment) > 0:
                outprint = '有材料'
                if len(gate) > 0:
                    close_gate, distance = find_close_point_to_box(
                        gate, hero_track[0])  # 找到最近的门
                    farthest_item, distance = find_farthest_box(
                        equipment, close_gate)  # 找到离最近门最远的材料
                    angle = calculate_point_to_box_angle(
                        hero_track[0], farthest_item)
                else:
                    close_item, distance = find_close_point_to_box(
                        equipment, hero_track[0])  # 找到最近的材料
                    angle = calculate_point_to_box_angle(
                        hero_track[0], close_item)
                self.ctrl.attack(False)
                self.ctrl.move(angle)

            elif len(gate) > 0:
                outprint = '有门'
                if self.buwanjia[self.room_num] == 9:  # 左门
                    close_gate, distance = find_close_point_to_box(
                        gate, hero_track[0])
                    angle = calculate_gate_angle(hero_track[0], close_gate)
                    self.ctrl.attack(False)
                    self.ctrl.move(angle)
                else:
                    close_gate, distance = find_close_point_to_box(
                        gate, hero_track[0])
                    angle = calculate_point_to_box_angle(
                        hero_track[0], close_gate)
                    self.ctrl.attack(False)
                    self.ctrl.move(angle)
            elif len(arrow) > 0 and self.room_num != 4:
                outprint = '有箭头'
                close_arrow, distance = find_closest_or_second_closest_box(
                    arrow, hero_track[0])
                angle = calculate_point_to_box_angle(
                    hero_track[0], close_arrow)
                self.ctrl.move(angle)
                self.ctrl.attack(False)
            elif self.special_command == 'retry':
                if self.find_and_click(image, "retry"):
                    self.special_command = 'ok'
            elif self.special_command == 'ok':
                if self.find_and_click(image, "ok"):
                    self.ctrl.move(0)
                    self.room_num = -1
                    hero_track = deque()
                    hero_track.appendleft([0, 0])
                    self.special_command = None
            else:
                outprint = "无目标"
                if self.room_num == 4:
                    angle = calculate_angle_to_box(hero_track[0], [0.25, 0.6])
                else:
                    angle = calculate_angle_to_box(hero_track[0], [0.5, 0.75])
                self.ctrl.move(angle)
                self.ctrl.attack(False)
            print(
                f"\r当前进度:{outprint},角度{angle}，位置{hero_track[0]}, 耗时{interval},特殊命令:{self.special_command}", end="")

    def find_and_click(self, image, target):
        for _ in range(2):
            target_box = self.matcher.match(image, target)
            if target_box is not None:
                break
            time.sleep(0.1)
        if target_box is None:
            return False
        target_point = calculate_box_center(target_box)
        print(f"click '{target}'")
        self.ctrl.click(target_point[0]+np.random.randint(-6, 6),
                        target_point[1]+np.random.randint(-6, 6))
        return True

    def calculate_hero_pos(self, hero_track, boxs):
        if len(boxs) == 0:
            None
        elif len(boxs) == 1:
            hero_track.appendleft(calculate_center(boxs[0]))
        elif len(boxs) > 1:
            for box in boxs:
                if calculate_distance(box, hero_track[0]) < 0.1:
                    hero_track.appendleft(box)
                    return
                hero_track.appendleft(hero_track[0])
