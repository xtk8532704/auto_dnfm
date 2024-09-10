import pdb
import time
from main import *
from utils.action_utils import calculate_distance, calculate_angle

current_dir = os.path.dirname(os.path.abspath(__file__))
image_queue = AutoCleaningQueue(maxsize=3)
client = ScrcpyADB(image_queue, max_fps=15)
ctrl = GameControl(client, os.path.join(
    current_dir, "./skill.json"), os.path.join(current_dir, "./personal.json"))


def move_to(cur_pos, target_pos, distance_pre_second=0.4):
    distance = calculate_distance(cur_pos, target_pos)
    angle = calculate_angle(cur_pos, target_pos)
    ctrl.move(angle)
    time.sleep(distance/distance_pre_second)
    ctrl.reset()


# 走一个菱形回到原地
move_to([0.5, 0.5], [0.6, 0.6])
move_to([0.6, 0.6], [0.5, 0.7])
move_to([0.5, 0.7], [0.4, 0.6])
move_to([0.4, 0.6], [0.5, 0.5])
pdb.set_trace()
