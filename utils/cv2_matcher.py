import cv2
import json
import os


class CV2Matcher:
    def __init__(self, template_config):
        with open(template_config, 'r', encoding='utf-8') as file:
            self.template_config = json.load(file)

        self.templates = {}
        current_dir = os.path.dirname(os.path.abspath(__file__))
        for key, img_path in self.template_config.items():
            img_path = os.path.join(current_dir, 'templates', img_path)
            self.templates[key] = cv2.imread(img_path, cv2.IMREAD_COLOR)

    def match(self, image, target, threshold=0.8):
        '''find the template box in the image with the max value and it should be larger than threshold'''
        template = self.templates[target]
        res = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        if max_val < threshold:
            return None
        x1, y1 = max_loc
        x2, y2 = x1 + template.shape[1], y1 + template.shape[0]
        return (x1, y1, x2, y2)

    def match_all(self, image, threshold=0.8):
        '''find all the template box in the image with the max value and it should be larger than threshold'''
        results = {}
        for key in self.templates:
            results[key] = self.match(image, key, threshold)

        return results
