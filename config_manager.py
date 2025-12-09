import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "gestures": {},
    "actions": {
        "my_gesture": "hotkey:ctrl+s" 
    },
    "settings": {
        "hold_time": 0.5,
        "threshold": 0.07,
        "frame_reduction": 150 
    }
}

class ConfigManager:
    def __init__(self):
        self.config = self.load_config()

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'w') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            return DEFAULT_CONFIG
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                if "settings" not in data:
                    data["settings"] = DEFAULT_CONFIG["settings"]
                if "actions" not in data:
                    data["actions"] = DEFAULT_CONFIG["actions"]
                if "gestures" not in data:
                    data["gestures"] = {}
                
                if "frame_reduction" not in data["settings"]:
                    data["settings"]["frame_reduction"] = DEFAULT_CONFIG["settings"]["frame_reduction"]
                
                return data
        except:
            return DEFAULT_CONFIG

    def save_to_file(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=4)

    def save_gesture(self, name, landmarks, action_cmd=None):
        self.config["gestures"][name] = landmarks
        if action_cmd:
             self.config["actions"][name] = action_cmd
        elif name not in self.config["actions"]:
            self.config["actions"][name] = "print:Жест настроен без действия"
        self.save_to_file()

    def update_action(self, name, new_action):
        """Обновляет только действие для существующего жеста"""
        self.config["actions"][name] = new_action
        self.save_to_file()

    def delete_gesture(self, name):
        if name in self.config["gestures"]:
            del self.config["gestures"][name]
        if name in self.config["actions"]:
            del self.config["actions"][name]
        self.save_to_file()

    def save_setting(self, key, value):
        self.config["settings"][key] = value
        self.save_to_file()

    def get_action(self, name):
        return self.config["actions"].get(name)

    def get_gestures(self):
        return self.config["gestures"]
    
    def get_setting(self, key):
        val = self.config.get("settings", {}).get(key)
        if val is None:
            return DEFAULT_CONFIG["settings"].get(key)
        return val