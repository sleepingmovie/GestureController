import os
import warnings
warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import mediapipe as mp
import numpy as np
import cv2

class GestureEngine:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.6
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.draw_spec = self.mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2)

    def process_frame(self, frame):
        try:
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(img_rgb)
            return results
        except:
            return None

    def normalize_landmarks(self, landmarks):
        if not landmarks: return []
        base_x, base_y = landmarks[0].x, landmarks[0].y
        coords = np.array([[lm.x - base_x, lm.y - base_y] for lm in landmarks])
        max_value = np.max(np.abs(coords))
        if max_value > 0:
            coords = coords / max_value
        return coords.tolist()

    def find_matching_gesture(self, current_landmarks_obj, saved_gestures, threshold=0.1):
        if not current_landmarks_obj or not current_landmarks_obj.landmark:
            return None, float('inf')

        try:
            curr_norm = np.array(self.normalize_landmarks(current_landmarks_obj.landmark))
            best_match = None
            min_dist = float('inf')

            for name, saved_data in saved_gestures.items():
                if not saved_data or not isinstance(saved_data, list): continue
                
                saved_arr = np.array(saved_data)
                if saved_arr.shape != curr_norm.shape: continue
                
                dist = np.mean(np.linalg.norm(curr_norm - saved_arr, axis=1))
                if dist < min_dist:
                    min_dist = dist
                    best_match = name

            if min_dist < threshold:
                return best_match, min_dist
            return None, min_dist
        except Exception:
            return None, float('inf')