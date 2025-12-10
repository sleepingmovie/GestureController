import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "profiles": {
        "GLOBAL": {
            "actions": {} 
        }
    },
    "gestures": {}, 
    "settings": {
        "hold_time": 0.5,
        "threshold": 0.07,
        "frame_reduction": 100,
        "trackpad_sensitivity": 3.0,
        "trackpad_mode": False
    }
}

class ConfigManager:
    def __init__(self):
        self.config = self.load_config()

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            self._create_default()
            return DEFAULT_CONFIG
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "profiles" not in data: data["profiles"] = DEFAULT_CONFIG["profiles"]
                if "gestures" not in data: data["gestures"] = {}
                if "settings" not in data: data["settings"] = DEFAULT_CONFIG["settings"]
                return data
        except Exception as e:
            print(f"[Config] Ошибка загрузки ({e}). Сброс к заводским.")
            return DEFAULT_CONFIG

    def _create_default(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)

    def save_to_file(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Config] Ошибка сохранения: {e}")

    def save_gesture(self, name, landmarks, action_cmd=None, profile="GLOBAL"):
        if landmarks:
            self.config["gestures"][name] = landmarks
        
        if profile not in self.config["profiles"]:
            self.config["profiles"][profile] = {"actions": {}}
            
        if action_cmd:
             self.config["profiles"][profile]["actions"][name] = action_cmd
        self.save_to_file()

    def delete_gesture(self, name, profile="GLOBAL"):
        if profile in self.config["profiles"]:
            if name in self.config["profiles"][profile]["actions"]:
                del self.config["profiles"][profile]["actions"][name]
        
        is_used = any(name in p["actions"] for p in self.config["profiles"].values())
        if not is_used and name in self.config["gestures"]:
             del self.config["gestures"][name]
        self.save_to_file()

    def get_action(self, gesture_name, active_app=None):
        if active_app and active_app in self.config["profiles"]:
            act = self.config["profiles"][active_app]["actions"].get(gesture_name)
            if act: return act
        return self.config["profiles"]["GLOBAL"]["actions"].get(gesture_name)

    def get_gestures(self):
        return self.config["gestures"]
    
    def save_setting(self, key, value):
        self.config["settings"][key] = value
        self.save_to_file()