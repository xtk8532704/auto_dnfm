import time
import math
import numpy as np
from utils.action_utils import calculate_bottom_center, find_close_box_to_point, calculate_angle, are_angles_on_same_side_of_y, calculate_distance


class Naima:
    def __init__(self, ctrl):
        self.ctrl = ctrl
        self.pre_room_num = -1
        self.last_angle = 0
        import os
        import json
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, "naima.json")
        with open(file_path, 'r', encoding='utf-8') as file:
            self.dict = json.load(file)  # 解析 JSON 文件

        self.close_skills = ["光芒烬盾", "洁净之光", "胜利之矛"]
        self.middle_skills = ["沐天之光", "光明锁环", "领悟之雷"]

    def skill(self, name, wait_time=0, ignore_cd=False):
        if not ignore_cd and "last_used" in self.dict[name] and self.dict[name]["last_used"] > time.time()-self.dict[name]["cd"]:
            return False
        self.dict[name]["last_used"] = time.time()
        self.ctrl.skill(self.dict[name]["pos"])
        time.sleep(np.random.uniform(0, 0.15))
        self.ctrl.move(0)  # 如果点不动技能也要保证停止身位
        if wait_time != 0:
            time.sleep(wait_time)
        print("shifang:" + name)
        return True

    def control(self, hero_pos, image, boxs, MapNumber):

        # 布万家固定步骤
        if self.pre_room_num != MapNumber:
            wait = 0.1
            if MapNumber == 0:
                self.ctrl.reset()
                time.sleep(wait)
                self.skill("勇气祝福", 1.2)
                self.move_and_keep(335, 0.3)
                self.skill("光芒烬盾", 0.9)
                self.skill("沐天之光", 0.4)
            elif MapNumber == 1:
                time.sleep(wait)
                self.move_and_stop(295, 0.4)
                self.skill("胜利之矛", 1)
            elif MapNumber == 2:
                time.sleep(wait)
                self.move_and_stop(340, 0.6)
                self.skill("光明惩戒", 0.8)
            elif MapNumber == 3:
                time.sleep(wait)
                self.move_and_stop(345, 0.5)
                self.skill("勇气颂歌", 2.5)
            elif MapNumber == 4:
                time.sleep(wait)
                self.move_and_stop(145, 0.65)
                self.move_a_little(1)
                self.skill("胜利之矛", 0.5)
                self.move_and_keep(1, 0.2)
                self.skill("光芒烬盾", 0.5)
            elif MapNumber == 5:
                time.sleep(wait)
                self.move_and_stop(180, 0.4)
                self.skill("觉醒", 0.4, True)
                self.skill("觉醒", 0.4, True)
                self.skill("觉醒", 0.4, True)
                self.skill("觉醒", 2.5, True)
            elif MapNumber == 6:
                None
            elif MapNumber == 7:
                time.sleep(wait)
                self.move_and_stop(335, 0.4)
                self.skill("光芒烬盾", 1)
                self.skill("沐天之光", 0.4)
            elif MapNumber == 8:
                time.sleep(wait)
                self.move_and_stop(340, 0.4)
                self.skill("胜利之矛", 0.6)
                self.move_and_keep(1, 0.5)
                self.skill("光明惩戒", 0.8)
            elif MapNumber == 9:
                time.sleep(wait)
                self.move_and_stop(330, 0.4)
                self.skill("光明之杖", 0.7)
                self.skill("沐天之光", 0.8)
                self.skill("光芒烬盾", 0.6)
            self.pre_room_num = MapNumber
            return self.last_angle
        self.pre_room_num = MapNumber

        # 自由战斗逻辑 # TODO 优化逻辑
        monster = boxs[boxs[:, 5] <= 2][:, :4]
        close_monster, distance = find_close_box_to_point(monster, hero_pos)
        close_monster_point = calculate_bottom_center(close_monster)
        angle = calculate_angle(hero_pos, close_monster_point)

        # 微调身位
        if not are_angles_on_same_side_of_y(self.last_angle, angle):
            self.move_a_little(angle)
            return self.last_angle

        # 范围内自由技能
        distance_x = abs(hero_pos[0]-close_monster_point[0])
        distance_y = abs(hero_pos[1]-close_monster_point[1])
        if distance_y < 0.15 and distance_x < 0.5:
            if distance_x < 0.25:
                skilled = self.random_skill(self.close_skills)
            elif distance_x < 0.5:
                skilled = self.random_skill(self.middle_skills)
            if not skilled:
                self.ctrl.attack(True)
        else:
            # 远距离怪物:非阻塞位移至怪物靠角色这一侧偏移0.1
            self.move_to_monster(hero_pos, close_monster_point)
        return self.last_angle

    def random_skill(self, skill_list):
        np.random.shuffle(skill_list)
        for skill in skill_list:
            if self.skill(skill):
                return True
        return False

    def move_a_little(self, angle):
        self.ctrl.move(angle)
        time.sleep(self.ctrl._random_click_duration()+0.1)
        self.ctrl.move(0)
        self.last_angle = angle

    def move_to_monster(self, hero_pos, monster_pos, pos_offset=0.1):
        # 非阻塞位移至怪物靠角色这一侧偏移0.05
        target_point = [monster_pos[0], monster_pos[1]]
        target_point[0] += pos_offset if target_point[0] < hero_pos[0] else -pos_offset
        angle = calculate_angle(hero_pos, target_point)
        self.ctrl.attack(False)
        self.ctrl.move(angle)
        self.last_angle = angle

    def move_and_stop(self, angle, t):
        assert t > 0.15, "所给的移动时间太短"
        t = t + np.random.uniform(-0.07, 0.07)
        self.ctrl.move(angle)
        time.sleep(t)
        self.ctrl.move(0)
        self.last_angle = angle

    def move_and_keep(self, angle, t):
        t = t + np.random.uniform(-0.05, 0.05)
        self.ctrl.move(angle)
        time.sleep(t)
        self.last_angle = angle
