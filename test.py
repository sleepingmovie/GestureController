import pyautogui
import time

pyautogui.FAILSAFE = False
print('switch to active window!!')
time.sleep(2)
pyautogui.write('suka pizdec', interval=0.1)