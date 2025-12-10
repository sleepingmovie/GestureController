import pyautogui
import webbrowser
import os
import subprocess
import platform

class ActionHandler:
    def execute(self, action_string):
        if not action_string:
            return

        if action_string.startswith("special:"):
            return

        print(f"--> ВЫПОЛНЯЮ: {action_string}")
        
        try:
            if action_string.startswith("mouse:"):
                btn = action_string.split(":", 1)[1].strip().lower()
                if btn == "left":
                    pyautogui.click()
                elif btn == "right":
                    pyautogui.click(button='right')
                elif btn == "middle":
                    pyautogui.click(button='middle')
                elif btn == "double":
                    pyautogui.doubleClick()
                elif btn == "side1":
                    pyautogui.click(button='mouse4')
                elif btn == "side2":
                    pyautogui.click(button='mouse5')
            
            elif action_string.startswith("hotkey:"):
                keys_part = action_string.split(":", 1)[1]
                keys = keys_part.split("+")
                keys = [k.strip().lower() for k in keys]
                pyautogui.hotkey(*keys)

            elif action_string.startswith("press:"):
                key = action_string.split(":", 1)[1].strip()
                pyautogui.press(key)

            elif action_string.startswith("app:"):
                cmd = action_string.split(":", 1)[1].strip()
                if platform.system() == "Windows":
                    os.startfile(cmd)
                else:
                    subprocess.Popen([cmd], shell=True)

            elif action_string.startswith("web:"):
                url = action_string.split(":", 1)[1].strip()
                if not url.startswith("http"):
                    url = "https://" + url
                webbrowser.open(url)
            
            elif action_string.startswith("type:"):
                pyautogui.FAILSAFE = False
                text = action_string.split(":", 1)[1]
                pyautogui.write(text, interval=0.1)

            elif action_string.startswith("print:"):
                msg = action_string.split(":", 1)[1]
                print(f"СООБЩЕНИЕ: {msg}")

        except Exception as e:
            print(f"!!! ОШИБКА выполнения действия '{action_string}': {e}")