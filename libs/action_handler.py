import pyautogui
import webbrowser
import os
import subprocess
import platform
import time
import pyperclip

class ActionHandler:
    def __init__(self):
        self.os_type = platform.system() 
        pyautogui.FAILSAFE = False

    def execute(self, action_string):
        if not action_string: return

        if action_string.startswith("chain:"):
            steps = action_string.split(":", 1)[1].split("|")
            for step in steps:
                if step.strip(): self.execute_single(step.strip())
            return

        self.execute_single(action_string)

    def execute_single(self, action_string):
        try:
            print(f"--> ACTION: {action_string}")
            
            if action_string.startswith("wait:"):
                val = action_string.split(":")[1]
                time.sleep(int(val) / 1000.0)

            elif action_string.startswith("mouse:"):
                btn = action_string.split(":")[1].strip().lower()
                if btn == "left": pyautogui.click()
                elif btn == "right": pyautogui.rightClick()
                elif btn == "middle": pyautogui.middleClick()
                elif btn == "double": pyautogui.doubleClick()

            elif action_string.startswith("hotkey:"):
                keys = action_string.split(":")[1].lower().split("+")
                time.sleep(0.1)
                pyautogui.hotkey(*keys)

            elif action_string.startswith("shell:") or action_string.startswith("app:"):
                cmd = action_string.split(":", 1)[1].strip()
                if self.os_type == "Windows":
                    os.startfile(cmd)
                else:
                    subprocess.Popen(cmd, shell=True, start_new_session=True)

            elif action_string.startswith("web:"):
                url = action_string.split(":", 1)[1].strip()
                webbrowser.open(url if url.startswith("http") else "https://" + url)
            
            elif action_string.startswith("type:"):
                text = action_string.split(":", 1)[1]
                self._paste_text(text)

            elif action_string.startswith("paste:"):
                 text = action_string.split(":", 1)[1]
                 self._paste_text(text)

        except Exception as e:
            print(f"!!! Error: {e}")

    def _paste_text(self, text):
        try:
            pyperclip.copy(text)
            time.sleep(0.1) 
            
            ctrl_key = 'command' if self.os_type == "Darwin" else 'ctrl'
            
            pyautogui.keyDown(ctrl_key)
            pyautogui.press('v')
            pyautogui.keyUp(ctrl_key)
        except Exception as e:
            print(f"Paste Error: {e}")