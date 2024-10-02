import os
import time
import threading
import numpy as np
from collections import deque
from hero.naima import Naima
from game_control import GameControl
from utils.action_utils import calculate_bottom_center, calculate_box_center, calculate_distance, find_closest_or_second_closest_box_to_point, calculate_iou, find_close_box_to_point, find_farthest_box_to_box, calculate_point_to_box_angle, calculate_point_to_gate_angle, calculate_angle, is_image_almost_black, calculate_point_to_box_angle, find_farthest_box_to_box
from utils.cv2_matcher import CV2Matcher


class GameAction:
    def __init__(self, ctrl: GameControl, queue):
        self.queue = queue
        self.ctrl = ctrl
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

        self.last_door_time = 0
        self.special_command = 'update_room'
        self.use_diamond = False  # 用黑砖来判断hero的位置
        self.diamond_to_hero_offset = None  # 黑砖到hero的偏移
        self.last_closest_door = None  # 上一帧最近的门以防止走错

    def reset(self):
        self.thread_run = False
        time.sleep(0.1)
        self.room_num = -1
        self.last_door_time = 0
        self.special_command = 'update_room'
        self.thread_run = True
        self.thread = threading.Thread(target=self.control)  # 创建线程，并指定目标函数
        self.thread.daemon = True  # 设置为守护线程（可选）
        self.thread.start()

    def control(self):
        self.buwanjia_control()

    def street_control(self, image, boxs):
        pass

    def buwanjia_control(self):
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
                this_door_time = time.time()
                if this_door_time-self.last_door_time > 1.2:
                    print("过图")
                    last_room_pos = hero_track[0]
                    hero_track = deque()
                    hero_track.appendleft(
                        [1-last_room_pos[0], 1-last_room_pos[1]])
                    self.ctrl.reset()
                    self.last_door_time = this_door_time
                    self.special_command = 'update_room'
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
            pet = boxs[boxs[:, 5] == 12][:, :4]
            diamond = boxs[boxs[:, 5] == 13][:, :4]

            # 更新房间，目标门
            angle = 0
            outprint = ''
            if self.special_command == 'update_room':
                if len(hero) > 0:  # 记录房间号
                    self.room_num += 1
                    self.special_command = None
                    print("房间号：", self.room_num)
                    print("目标", self.buwanjia[self.room_num])
                else:
                    continue

            # 计算英雄位置
            self.calculate_hero_pos(hero_track, hero, diamond)
            self.last_closest_door = None  # 重写门逻辑
            # 过滤和英雄/宠物IoU大于0.8的monster(误检)
            filter_monster = [hero, pet]
            delete_index = []
            for obj in filter_monster:
                if len(obj) == 0 or len(monster) == 0:
                    continue
                for i in range(len(monster)):
                    if calculate_iou(monster[i], obj[0]) > 0.8:
                        delete_index.append(i)
                        break
            monster = np.delete(monster, delete_index, axis=0)

            # 计算时间间隔
            current_time = time.time()
            interval = current_time - self.last_time
            self.last_time = current_time

            # 过图逻辑
            if len(card) >= 8:
                time.sleep(1+np.random.rand())
                self.ctrl.click(0.25*image.shape[0], 0.25*image.shape[1])
                self.special_command = 'finish'
                time.sleep(2.)
            elif len(monster) > 0:
                outprint = '有怪物'
                angle = self.control_attack.control(
                    hero_track[0], image, boxs, self.room_num)
            elif len(equipment) > 0:
                outprint = '有材料'
                if len(gate) > 0:
                    close_gate, distance = find_close_box_to_point(
                        gate, hero_track[0])  # 找到最近的门
                    target_item, distance = find_farthest_box_to_box(
                        equipment, close_gate)  # 找到离最近门最远的材料
                    angle = calculate_point_to_box_angle(
                        hero_track[0], target_item)
                else:
                    target_item, distance = find_close_box_to_point(
                        equipment, hero_track[0])  # 找到最近的材料
                    angle = calculate_point_to_box_angle(
                        hero_track[0], target_item)
                self.ctrl.attack(False)
                self.ctrl.move(angle)

            elif len(gate) > 0:
                outprint = '有门'

                close_gate, distance = find_close_box_to_point(
                    gate, hero_track[0])
                if self.buwanjia[self.room_num] == 9 and distance < 0.4:
                    angle = calculate_point_to_gate_angle(  # 左门位置偏高
                        hero_track[0], close_gate)
                    self.ctrl.attack(False)
                    self.ctrl.move(angle)
                else:
                    angle = calculate_point_to_box_angle(
                        hero_track[0], close_gate)
                    self.ctrl.attack(False)
                    self.ctrl.move(angle)

            elif len(arrow) > 0 and self.room_num != 4:
                outprint = '有箭头'
                close_arrow, distance = find_closest_or_second_closest_box_to_point(
                    arrow, hero_track[0])
                angle = calculate_point_to_box_angle(
                    hero_track[0], close_arrow)
                self.ctrl.attack(False)
                self.ctrl.move(angle)

            elif self.special_command == 'finish':
                if self.find_and_click(image, "repair", check_until_disappear=False):
                    self.special_command = 'repair_ok'
                    time.sleep(1.+np.random.normal(0, 0.3))
                elif self.find_and_click(image, "retry", check_until_disappear=False):
                    self.special_command = 'retry_ok'
                    time.sleep(1.5+np.random.normal(0, 0.3))

            elif self.special_command == 'repair_ok':
                self.find_and_click(image, "repair_ok")
                self.special_command = 'repair_cancel'
            elif self.special_command == 'repair_cancel':
                self.find_and_click(image, "repair_cancel")
                self.special_command = 'finish'
            elif self.special_command == 'retry_ok':
                self.find_and_click(image, "ok")
                self.ctrl.reset()
                self.room_num = 0
                hero_track = deque()
                hero_track.appendleft([0, 0])
                self.special_command = None
            else:
                outprint = "无目标"
                if self.room_num == 4:
                    angle = calculate_angle(
                        hero_track[0], [0.25, 0.6])
                else:
                    angle = calculate_angle(
                        hero_track[0], [0.5, 0.75])
                self.ctrl.move(angle)
                self.ctrl.attack(False)
            print(
                f"\r当前进度:{outprint},角度{angle}，位置{hero_track[0]}, 耗时{interval},特定命令:{self.special_command}", end="")

    def find(self, image, target):
        # 找2次
        for _ in range(2):
            target_box = self.matcher.match(image, target)
            if target_box is not None:
                break
            time.sleep(0.2)
        if target_box is None:
            return None
        return calculate_box_center(target_box)

    def find_and_click(self, image, target, random_r=4, check_until_disappear=True):
        target_point = self.find(image, target)
        if target_point is None:
            return False
        self.ctrl.click(target_point[0], target_point[1], random_r)

        if not check_until_disappear:
            return True
        # 确认消失
        for _ in range(4):
            time.sleep(0.5)
            target_box = self.matcher.match(image, target)
            if target_box is None:
                return True
            self.ctrl.click(target_point[0], target_point[1], random_r)
        return False

    def calculate_hero_pos(self, hero_track, hero_boxs, diamond_boxs):

        if self.use_diamond:
            # 当有一个hero和一个diamond的时候更新offset
            if len(hero_boxs) == 1 and len(diamond_boxs) == 1:
                diamond_center = calculate_bottom_center(diamond_boxs[0])
                hero_center = calculate_bottom_center(hero_boxs[0])
                if self.diamond_to_hero_offset is None:
                    self.diamond_to_hero_offset = [
                        hero_center[0] - diamond_center[0], hero_center[1] - diamond_center[1]]
                else:
                    self.diamond_to_hero_offset = [
                        0.9 * self.diamond_to_hero_offset[0] +
                        0.1 * (hero_center[0] - diamond_center[0]),
                        0.9 * self.diamond_to_hero_offset[1] +
                        0.1 * (hero_center[1] - diamond_center[1])]

            if len(diamond_boxs) == 0:
                pass
            elif len(diamond_boxs) == 1:
                diamond_center = calculate_bottom_center(diamond_boxs[0])
                hero_center = (diamond_center[0] + self.diamond_to_hero_offset[0],
                               diamond_center[1] + self.diamond_to_hero_offset[1])
                hero_track.appendleft(hero_center)
            elif len(diamond_boxs) > 1:
                ori_diamond_center = (hero_track[0]-self.diamond_to_hero_offset[0],
                                      hero_track[0]-self.diamond_to_hero_offset[1])
                for box in diamond_boxs:
                    box_center = calculate_bottom_center(box)
                    if calculate_distance(box_center, ori_diamond_center) < 0.1:
                        hero_track.appendleft(box)
                        return
                hero_track.appendleft(hero_track[0])

        else:
            if len(hero_boxs) == 0:
                pass
            elif len(hero_boxs) == 1:
                hero_track.appendleft(calculate_bottom_center(hero_boxs[0]))
            elif len(hero_boxs) > 1:
                for box in hero_boxs:
                    box_center = calculate_bottom_center(box)
                    if calculate_distance(box_center, hero_track[0]) < 0.1:
                        hero_track.appendleft(box)
                        return
                hero_track.appendleft(hero_track[0])

    def move_to(self, cur_pos, target_pos, distance_pre_second=0.35):
        # distance_pre_second速度越大，相对的位移时间越短，实际位移距离越短
        distance = calculate_distance(cur_pos, target_pos)
        angle = calculate_angle(cur_pos, target_pos)
        self.ctrl.move(angle)
        time.sleep(max(distance/distance_pre_second,
                   0.1+np.random.uniform(0, 0.05)))
        self.ctrl.move(0)
        return angle
