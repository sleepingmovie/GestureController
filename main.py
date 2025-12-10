import cv2
import argparse
import time
import numpy as np
import pyautogui
import math
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk
from gesture_engine import GestureEngine
from config_manager import ConfigManager
from action_handler import ActionHandler
import keyboard

class Smoother:
    def __init__(self, alpha=0.5, start_val=0.0):
        self.alpha = alpha
        self.val = start_val

    def update(self, new_val):
        self.val = self.val * (1 - self.alpha) + new_val * self.alpha
        return self.val

    def update_point(self, x, y):
        if isinstance(self.val, (list, tuple)) and len(self.val) == 2:
            cur_x, cur_y = self.val
        else:
            cur_x, cur_y = x, y 
            
        new_x = cur_x * (1 - self.alpha) + x * self.alpha
        new_y = cur_y * (1 - self.alpha) + y * self.alpha
        self.val = (new_x, new_y)
        return int(new_x), int(new_y)

class ActionDialog:
    def __init__(self, parent, title="Настройка действия", initial_val=""):
        self.result = None
        self.win = tk.Toplevel(parent)
        self.win.title(title)
        self.win.geometry("400x300")
        
        self.types = {
            "Горячие клавиши (hotkey)": "hotkey",
            "Запуск приложения (app)": "app",
            "Открыть сайт (web)": "web",
            "Напечатать текст (type)": "type",
            "Спец. команды (special)": "special",
            "Клик мышью (mouse)": "mouse"
        }
        
        tk.Label(self.win, text="Тип действия:").pack(pady=5)
        
        self.type_var = tk.StringVar(value="Горячие клавиши (hotkey)")
        cb = ttk.Combobox(self.win, textvariable=self.type_var, values=list(self.types.keys()), state="readonly")
        cb.pack(fill=tk.X, padx=20)
        cb.bind("<<ComboboxSelected>>", self.update_hint)

        tk.Label(self.win, text="Значение / Команда:").pack(pady=5)
        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(self.win, textvariable=self.entry_var)
        self.entry.pack(fill=tk.X, padx=20)
        
        self.hint_lbl = tk.Label(self.win, text="Пример: ctrl+c", fg="gray", font=("Arial", 9))
        self.hint_lbl.pack(pady=5)

        if initial_val and ":" in initial_val:
            prefix, val = initial_val.split(":", 1)
            for k, v in self.types.items():
                if v == prefix:
                    self.type_var.set(k)
                    self.entry_var.set(val)
                    break
        
        self.update_hint()

        btn_frame = tk.Frame(self.win)
        btn_frame.pack(pady=20)
        tk.Button(btn_frame, text="ОК", command=self.on_ok, width=10, bg="#dddddd").pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Отмена", command=self.win.destroy, width=10).pack(side=tk.LEFT)
        
        self.win.wait_window()

    def update_hint(self, event=None):
        t = self.types[self.type_var.get()]
        if t == "hotkey": txt = "Пример: ctrl+c или alt+tab"
        elif t == "app": txt = "Пример: calc.exe или notepad"
        elif t == "web": txt = "Пример: youtube.com"
        elif t == "type": txt = "Пример: Hello World"
        elif t == "special": txt = "Пример: toggle_follow (вкл/выкл мышь)"
        elif t == "mouse": txt = "Пример: left, right, double"
        else: txt = ""
        self.hint_lbl.config(text=txt)

    def on_ok(self):
        prefix = self.types[self.type_var.get()]
        val = self.entry_var.get().strip()
        if not val:
            messagebox.showwarning("Ошибка", "Введите значение!")
            return
        self.result = f"{prefix}:{val}"
        self.win.destroy()

class GestureUI:
    def __init__(self, config_manager):
        self.cfg = config_manager
        self.root = tk.Tk()
        self.root.withdraw() 

    def prompt_save_gesture(self):
        name = simpledialog.askstring("Новый жест", "Название жеста (англ):")
        if not name: return None, None
        
        dlg = ActionDialog(self.root, title=f"Действие для '{name}'")
        return name, dlg.result

    def show_settings(self, current_reduction):
        win = tk.Toplevel(self.root)
        win.title("Настройки чувствительности")
        win.geometry("350x200")
        
        tk.Label(win, text="Зона захвата (меньше = выше сенса):", font=("Arial", 10)).pack(pady=10)
        
        scale = tk.Scale(win, from_=50, to=200, orient=tk.HORIZONTAL, length=250)
        scale.set(current_reduction)
        scale.pack(pady=5)
        
        tk.Label(win, text="50 = Плавнее/Шире\n200 = Быстрее/Короче", fg="gray").pack()

        def save():
            val = scale.get()
            self.cfg.save_setting("frame_reduction", val)
            messagebox.showinfo("Успех", "Чувствительность сохранена!")
            win.destroy()

        tk.Button(win, text="Сохранить", bg="#dddddd", command=save).pack(pady=15)
        win.wait_window()

    def show_manager(self):
        win = tk.Toplevel(self.root)
        win.title("Менеджер жестов")
        win.geometry("500x400")
        
        frame_list = tk.Frame(win)
        frame_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        lb = tk.Listbox(frame_list, font=("Arial", 11))
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(frame_list)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        lb.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=lb.yview)

        def refresh():
            lb.delete(0, tk.END)
            gestures = self.cfg.get_gestures()
            actions = self.cfg.config["actions"]
            for g in gestures:
                act = actions.get(g, '<нет действия>')
                lb.insert(tk.END, f"{g}  ->  {act}")

        refresh()

        btn_frame = tk.Frame(win)
        btn_frame.pack(fill=tk.X, pady=5)

        def delete_cur():
            sel = lb.curselection()
            if not sel: return
            text = lb.get(sel[0])
            name = text.split("  ->  ")[0]
            if messagebox.askyesno("Удалить?", f"Удалить жест '{name}'?"):
                self.cfg.delete_gesture(name)
                refresh()

        def edit_cur():
            sel = lb.curselection()
            if not sel: return
            text = lb.get(sel[0])
            name = text.split("  ->  ")[0]
            old_act = self.cfg.get_action(name)
            
            dlg = ActionDialog(win, title=f"Изменить: {name}", initial_val=old_act)
            if dlg.result:
                self.cfg.update_action(name, dlg.result)
                refresh()

        tk.Button(btn_frame, text="Изменить действие", command=edit_cur).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Удалить жест", bg="#ffcccc", command=delete_cur).pack(side=tk.RIGHT, padx=10)
        
        win.wait_window()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-preview", action="store_true")
    args = parser.parse_args()

    engine = GestureEngine()
    config = ConfigManager()
    actor = ActionHandler()
    ui = GestureUI(config)

    pyautogui.FAILSAFE = False
    SCREEN_W, SCREEN_H = pyautogui.size()
    
    cap = cv2.VideoCapture(0)
    CAM_W, CAM_H = 640, 480
    cap.set(3, CAM_W)
    cap.set(4, CAM_H)

    curr_gest = None
    gest_time = 0
    triggered = False
    
    is_following = False
    is_dragging = False 
    
    mouse_smoother = Smoother(alpha=0.2, start_val=(SCREEN_W//2, SCREEN_H//2)) 

    print("--- READY ---")
    if not args.no_preview:
        print("S - Сохранить | L - Менеджер | O - Настройки (Сенса) | Q - Выход")

    while True:
        HOLD_TIME = config.get_setting("hold_time")
        THRESHOLD = config.get_setting("threshold")
        FRAME_REDUCTION = config.get_setting("frame_reduction")

        success, frame = cap.read()
        if not success: break
        frame = cv2.flip(frame, 1)
        
        results = engine.process_frame(frame)
        
        detected_name = None
        status_txt = "OFF"
        status_col = (100, 100, 100)

        if results.multi_hand_landmarks:
            for hn in results.multi_hand_landmarks:
                lm = hn.landmark
                
                if not args.no_preview:
                    engine.mp_draw.draw_landmarks(frame, hn, engine.mp_hands.HAND_CONNECTIONS)
                    cv2.rectangle(frame, (FRAME_REDUCTION, FRAME_REDUCTION), 
                                 (CAM_W - FRAME_REDUCTION, CAM_H - FRAME_REDUCTION), 
                                 (0, 255, 0), 1)

                detected_name, _ = engine.find_matching_gesture(hn, config.get_gestures(), THRESHOLD)

                if is_following:
                    x_point, y_point = lm[8].x, lm[8].y
                    
                    x3 = np.interp(x_point * CAM_W, (FRAME_REDUCTION, CAM_W - FRAME_REDUCTION), (0, SCREEN_W))
                    y3 = np.interp(y_point * CAM_H, (FRAME_REDUCTION, CAM_H - FRAME_REDUCTION), (0, SCREEN_H))
                    
                    clocX, clocY = mouse_smoother.update_point(x3, y3)
                    clocX = max(0, min(SCREEN_W, clocX))
                    clocY = max(0, min(SCREEN_H, clocY))
                    
                    pyautogui.moveTo(clocX, clocY)
                    
                    thumb_tip_y = lm[4].y
                    index_mcp_y = lm[5].y 

                    is_thumb_up = (index_mcp_y - thumb_tip_y) > 0.02

                    if is_thumb_up:
                        if not is_dragging:
                            pyautogui.mouseDown()
                            is_dragging = True
                    else:
                        if is_dragging:
                            pyautogui.mouseUp()
                            is_dragging = False
                    
                    if not args.no_preview:
                        status_col = (0, 0, 255) if is_dragging else (0, 255, 0)
                        status_txt = "DRAGGING" if is_dragging else "MOVE"
                        
                        cx, cy = int(lm[4].x * CAM_W), int(lm[4].y * CAM_H)
                        cv2.circle(frame, (cx, cy), 10, status_col, -1)
                        
                        iy = int(lm[5].y * CAM_H)
                        cv2.line(frame, (cx-20, iy), (cx+20, iy), (200,200,200), 1)

                if not args.no_preview:
                    key = cv2.waitKey(1) & 0xFF
                    if keyboard.is_pressed('s'):
                        name, action = ui.prompt_save_gesture()
                        if name and action:
                            norm = engine.normalize_landmarks(hn.landmark)
                            config.save_gesture(name, norm, action)
                    elif keyboard.is_pressed('l'):
                         ui.show_manager()
                    elif keyboard.is_pressed('o'):
                        ui.show_settings(FRAME_REDUCTION)

        if detected_name and not is_dragging:
            if detected_name == curr_gest:
                dur = time.time() - gest_time
                if not args.no_preview:
                    max_w = 200
                    bw = int((dur / HOLD_TIME) * max_w)
                    bw = min(bw, max_w)
                    cv2.rectangle(frame, (10, 450), (10 + max_w, 460), (50, 50, 50), -1)
                    cv2.rectangle(frame, (10, 450), (10 + bw, 460), (0, 255, 255), -1)
                    cv2.putText(frame, detected_name, (10, 440), 1, 1, (0, 255, 255), 2)

                if dur >= HOLD_TIME and not triggered:
                    act = config.get_action(detected_name)
                    if act == "special:toggle_follow":
                        is_following = not is_following
                        if not is_following and is_dragging:
                            pyautogui.mouseUp()
                            is_dragging = False
                        mouse_smoother.val = (SCREEN_W//2, SCREEN_H//2)
                    elif act and not is_following:
                        actor.execute(act)
                    triggered = True
            else:
                curr_gest = detected_name
                gest_time = time.time()
                triggered = False
        else:
            curr_gest = None
            triggered = False

        if is_following and not args.no_preview:
            cv2.putText(frame, f"MOUSE: {status_txt}", (10, 50), 1, 1, status_col, 2)

        if not args.no_preview:
            cv2.imshow("Gesture Control", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()