import cv2
import time
import numpy as np
import pyautogui
import tkinter as tk
from tkinter import ttk
from libs.gesture_engine import GestureEngine
from libs.config_manager import ConfigManager
from libs.action_handler import ActionHandler
import platform
import keyboard
import sys

NO_PREVIEW = "--no-preview" in sys.argv

BG_COLOR = "#1e1e1e"
FG_COLOR = "#ffffff"
ACCENT_COLOR = "#00ff99"
BTN_COLOR = "#333333"
BTN_HOVER = "#444444"
INPUT_BG = "#2d2d2d"
HINT_COLOR = "#aaaaaa"

try:
    import pygetwindow as gw
except ImportError:
    gw = None

def hex_to_bgr(hex_color):
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return (rgb[2], rgb[1], rgb[0])

CV_ACCENT = hex_to_bgr(ACCENT_COLOR)
CV_WHITE = (255, 255, 255)

def draw_ui_text(img, text, pos):
    x, y = pos
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.7
    thickness = 1
    pad = 10
    (w, h), baseline = cv2.getTextSize(text, font, scale, thickness)
    cv2.rectangle(img, (x - pad, y - h - pad), (x + w + pad, y + pad), (0, 0, 0), -1)
    cv2.rectangle(img, (x - pad, y - h - pad), (x + w + pad, y + pad), CV_ACCENT, 1)
    cv2.putText(img, text, (x, y), font, scale, CV_ACCENT, thickness, cv2.LINE_AA)

class ModernUI(tk.Toplevel):
    def __init__(self, parent, title, w=500, h=400):
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{w}x{h}")
        self.configure(bg=BG_COLOR)
        self.resizable(False, False)
        
        self.withdraw()
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.geometry(f"+{x}+{y}")
        self.deiconify()

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TCombobox", fieldbackground=INPUT_BG, background=BTN_COLOR, 
                             foreground=FG_COLOR, arrowcolor=ACCENT_COLOR, borderwidth=0)
        self.style.map("TCombobox", fieldbackground=[("readonly", INPUT_BG)])
        
        self.attributes("-topmost", True)
        self.grab_set()
        self.focus_force()

    def add_btn(self, parent, text, cmd, bg=BTN_COLOR, fg=FG_COLOR):
        btn = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, 
                       font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                       activebackground=ACCENT_COLOR, activeforeground="black", cursor="hand2")
        
        btn.config(highlightbackground=BTN_HOVER, highlightthickness=1)

        def on_enter(e): 
            if btn['state'] != 'disabled': btn['bg'] = BTN_HOVER
        def on_leave(e): 
            if btn['state'] != 'disabled': btn['bg'] = bg
            
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        btn.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        return btn

class InputDialog(ModernUI):
    def __init__(self, parent, title, prompt):
        super().__init__(parent, title, 350, 180) 
        self.result = None
        
        tk.Label(self, text=prompt, bg=BG_COLOR, fg=FG_COLOR, font=("Arial", 11)).pack(pady=(20, 10))
        
        self.entry = tk.Entry(self, bg=INPUT_BG, fg=FG_COLOR, insertbackground=FG_COLOR, 
                              font=("Consolas", 12), relief="flat")
        self.entry.pack(fill=tk.X, padx=20, pady=5, ipady=5)
        self.entry.focus_set()
        self.entry.bind("<Return>", lambda e: self.on_ok())
        
        tk.Label(self, text="Пример: volume_up, open_chrome, peace_sign", 
                 bg=BG_COLOR, fg="gray", font=("Arial", 8)).pack(pady=0)
        
        btn_frame = tk.Frame(self, bg=BG_COLOR)
        btn_frame.pack(fill=tk.X, pady=20, padx=20)
        
        self.add_btn(btn_frame, "OK", self.on_ok, bg=ACCENT_COLOR, fg="black")
        self.add_btn(btn_frame, "Отмена", self.destroy)
        
        self.wait_window()

    def on_ok(self):
        val = self.entry.get().strip()
        if val:
            self.result = val
            self.destroy()

class MacroEditor(ModernUI):
    def __init__(self, parent, initial_chain=""):
        super().__init__(parent, "Конструктор Действий", 700, 550) 
        self.result = None
        self.steps = []

        left_p = tk.Frame(self, bg=BG_COLOR)
        left_p.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(left_p, text="Список команд (Chain):", bg=BG_COLOR, fg=ACCENT_COLOR, font=("Arial", 11, "bold")).pack(anchor="w")
        
        self.lb = tk.Listbox(left_p, bg=INPUT_BG, fg=FG_COLOR, font=("Consolas", 10), 
                             selectbackground=ACCENT_COLOR, selectforeground="black", 
                             relief="flat", highlightthickness=0)
        self.lb.pack(fill=tk.BOTH, expand=True, pady=5)
        
        btn_f = tk.Frame(left_p, bg=BG_COLOR)
        btn_f.pack(fill=tk.X)
        self.add_btn(btn_f, "▲", self.move_up)
        self.add_btn(btn_f, "▼", self.move_down)
        self.add_btn(btn_f, "Удалить", self.delete_step, bg="#ff4444")

        right_p = tk.Frame(self, bg=BG_COLOR, width=300)
        right_p.pack(side=tk.RIGHT, fill=tk.BOTH, padx=10, pady=10)
        right_p.pack_propagate(False)

        tk.Label(right_p, text="Добавить действие:", bg=BG_COLOR, fg=FG_COLOR, font=("Arial", 10, "bold")).pack(anchor="w")
        
        self.types = {
            "Клавиши (Hotkey)": "hotkey",
            "Запуск (Shell/App)": "shell",
            "Текст (Type)": "type",
            "Сайт (Web)": "web",
            "Мышь (Mouse)": "mouse",
            "Ждать (Wait ms)": "wait",
            "Спец (Special)": "special"
        }
        
        self.hints = {
            "hotkey": "Нажимает сочетание клавиш.\n• Примеры: ctrl+c, alt+f4, win+d, enter\n• Клавиши разделять плюсом (+).\n• ctrl+alt+delete работать НЕ будет (защита ОС).",
            "shell": "Запускает программу или файл.\n• Windows: calc, notepad, explorer\n• Полный путь: C:\\Games\\game.exe",
            "type": "Печатает текст.\n• Примеры: Hello World, Привет\n• Использует эмуляцию клавиатуры.\n• Для русского текста переключает через буфер.",
            "web": "Открывает сайт в браузере по умолчанию.\n• Примеры: google.com, youtube.com\n• Можно писать без http://",
            "mouse": "Кликает мышью.\n• Варианты: left (ЛКМ), right (ПКМ),\n  middle (Колесо), double (Двойной)",
            "wait": "Пауза между действиями (в миллисекундах).\n• 1000 = 1 секунда\n• 500 = полсекунды.",
            "special": "Специальные команды программы.\n• toggle_follow: Вкл/Выкл режим мыши"
        }

        self.type_var = tk.StringVar(value="⌨ Клавиши (Hotkey)")
        cb = ttk.Combobox(right_p, textvariable=self.type_var, values=list(self.types.keys()), state="readonly")
        cb.pack(fill=tk.X, pady=5)
        cb.bind("<<ComboboxSelected>>", self.update_hint)
        
        tk.Label(right_p, text="Значение:", bg=BG_COLOR, fg="gray", font=("Arial", 9)).pack(anchor="w", pady=(10,0))
        self.val_entry = tk.Entry(right_p, bg=INPUT_BG, fg=FG_COLOR, insertbackground=FG_COLOR, relief="flat", font=("Consolas", 10))
        self.val_entry.pack(fill=tk.X, pady=5, ipady=4)
        self.val_entry.bind("<Return>", lambda e: self.add_step())

        self.hint_label = tk.Label(right_p, text="", bg=INPUT_BG, fg=HINT_COLOR, font=("Segoe UI", 9), 
                                   justify=tk.LEFT, anchor="nw", padx=10, pady=10, wraplength=280)
        self.hint_label.pack(fill=tk.X, pady=10)
        
        tk.Button(right_p, text="➕ ДОБАВИТЬ В ЦЕПОЧКУ", command=self.add_step, bg="#444444", fg="white", 
                  relief="flat", font=("Arial", 9, "bold")).pack(fill=tk.X, pady=10)
        
        tk.Button(self, text="💾 СОХРАНИТЬ ЖЕСТ", command=self.save, bg=ACCENT_COLOR, fg="black", 
                  font=("Arial", 12, "bold"), relief="flat").pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=20)

        self.update_hint() 
        if initial_chain: self.parse(initial_chain)

    def update_hint(self, event=None):
        code = self.types[self.type_var.get()]
        hint_text = self.hints.get(code, "Нет описания")
        self.hint_label.config(text=hint_text)

    def add_step(self):
        code = self.types[self.type_var.get()]
        val = self.val_entry.get().strip()
        if not val and code != "mouse": return
        
        full_cmd = f"{code}:{val}"
        self.steps.append(full_cmd)
        self.lb.insert(tk.END, f"[{code}] {val}")
        self.val_entry.delete(0, tk.END)

    def parse(self, chain):
        if chain.startswith("chain:"): chain = chain[6:]
        for p in chain.split("|"):
            if ":" in p:
                self.steps.append(p)
                self.lb.insert(tk.END, p)

    def delete_step(self):
        s = self.lb.curselection()
        if s:
            self.lb.delete(s[0])
            self.steps.pop(s[0])

    def move_up(self):
        s = self.lb.curselection()
        if s and s[0] > 0:
            i = s[0]
            self.steps[i], self.steps[i-1] = self.steps[i-1], self.steps[i]
            t = self.lb.get(i)
            self.lb.delete(i)
            self.lb.insert(i-1, t)
            self.lb.selection_set(i-1)

    def move_down(self):
        s = self.lb.curselection()
        if s and s[0] < len(self.steps)-1:
            i = s[0]
            self.steps[i], self.steps[i+1] = self.steps[i+1], self.steps[i]
            t = self.lb.get(i)
            self.lb.delete(i)
            self.lb.insert(i+1, t)
            self.lb.selection_set(i+1)

    def save(self):
        if not self.steps: self.result = None
        elif len(self.steps) == 1: self.result = self.steps[0]
        else: self.result = "chain:" + "|".join(self.steps)
        self.destroy()

class AppController:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.cfg = ConfigManager()
        self.ui_blocked = False

    def get_windows(self):
        titles = ["GLOBAL"]
        if gw:
            try:
                for w in gw.getAllWindows():
                    if w.title and w.visible and w.title != "GestureCam":
                        titles.append(w.title)
            except: pass
        return sorted(list(set(titles)))

    def save_sequence(self, current_app, landmarks):
        self.ui_blocked = True
        self.root.update()
        
        inp = InputDialog(self.root, "Создание жеста", "Введите уникальное имя жеста (англ):")
        if not inp.result:
            self.ui_blocked = False
            return

        name = inp.result

        prof_win = ModernUI(self.root, "Выбор профиля", 400, 200)
        tk.Label(prof_win, text=f"Где должен работать жест '{name}'?", bg=BG_COLOR, fg="white", font=("Arial", 10)).pack(pady=10)
        
        c_var = tk.StringVar(value="GLOBAL")
        vals = self.get_windows()
        cb = ttk.Combobox(prof_win, textvariable=c_var, values=vals, state="readonly")
        if current_app in vals: cb.set(current_app)
        cb.pack(fill=tk.X, padx=30, pady=5)
        
        tk.Label(prof_win, text="GLOBAL = Работает везде\nИначе = Только когда окно активно", 
                 bg=BG_COLOR, fg="gray", font=("Arial", 8)).pack(pady=5)

        tk.Button(prof_win, text="ПРОДОЛЖИТЬ НАСТРОЙКУ ->", command=prof_win.destroy, 
                  bg=ACCENT_COLOR, fg="black", font=("Arial", 10, "bold"), relief="flat").pack(pady=15)
        
        self.root.wait_window(prof_win)
        target_prof = c_var.get()

        ed = MacroEditor(self.root)
        self.root.wait_window(ed)
        
        if ed.result:
            self.cfg.save_gesture(name, landmarks, ed.result, target_prof)
            print(f"[SUCCESS] Жест '{name}' сохранен для {target_prof}")
        
        self.ui_blocked = False

    def open_manager(self):
        self.ui_blocked = True
        time.sleep(0.1)
        win = ModernUI(self.root, "Менеджер Жестов", 600, 450)
        
        nb = ttk.Notebook(win)
        nb.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        lists = {}
        for prof_name, data in self.cfg.config["profiles"].items():
            f = tk.Frame(nb, bg=BG_COLOR)
            nb.add(f, text=prof_name)
            
            lb = tk.Listbox(f, bg=INPUT_BG, fg=FG_COLOR, font=("Consolas", 10), selectbackground=ACCENT_COLOR, borderwidth=0)
            lb.pack(fill=tk.BOTH, expand=True)
            
            scrollbar = tk.Scrollbar(f)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            lb.config(yscrollcommand=scrollbar.set)
            scrollbar.config(command=lb.yview)

            for k, v in data["actions"].items():
                lb.insert(tk.END, f"{k}  ->  {v}")
            lists[prof_name] = lb

        def edit():
            try:
                prof = nb.tab(nb.select(), "text")
                lb = lists[prof]
                sel = lb.curselection()
                if not sel: return
                
                raw = lb.get(sel[0])
                gname = raw.split("  ->  ")[0]
                old_act = self.cfg.config["profiles"][prof]["actions"][gname]
                
                ed = MacroEditor(win, old_act)
                win.wait_window(ed)
                
                if ed.result:
                    self.cfg.save_gesture(gname, None, ed.result, prof)
                    lb.delete(sel[0])
                    lb.insert(sel[0], f"{gname}  ->  {ed.result}")
            except: pass

        def delete():
            try:
                prof = nb.tab(nb.select(), "text")
                lb = lists[prof]
                sel = lb.curselection()
                if not sel: return
                
                raw = lb.get(sel[0])
                gname = raw.split("  ->  ")[0]
                
                self.cfg.delete_gesture(gname, prof)
                lb.delete(sel[0])
            except: pass

        bf = tk.Frame(win, bg=BG_COLOR)
        bf.pack(fill=tk.X, pady=10)
        win.add_btn(bf, "Изменить действие", edit)
        win.add_btn(bf, "Удалить жест", delete, bg="#ff4444")
        
        self.root.wait_window(win)
        self.ui_blocked = False

    def open_settings(self):
        self.ui_blocked = True
        time.sleep(0.1)
        win = ModernUI(self.root, "Настройки", 350, 250)
        
        def mk_scale(txt, key, min_v, max_v):
            tk.Label(win, text=txt, bg=BG_COLOR, fg="gray").pack(pady=(10,0))
            s = tk.Scale(win, from_=min_v, to=max_v, orient=tk.HORIZONTAL, 
                         bg=BG_COLOR, fg=ACCENT_COLOR, troughcolor=INPUT_BG, 
                         highlightthickness=0, resolution=0.1)
            s.set(self.cfg.config["settings"].get(key, 0))
            s.pack(fill=tk.X, padx=20)
            return s
            
        s_sens = mk_scale("Чувствительность мыши (Speed)", "trackpad_sensitivity", 1, 10)
        s_hold = mk_scale("Время удержания жеста (сек)", "hold_time", 0.1, 2.0)
        
        def save():
            self.cfg.save_setting("trackpad_sensitivity", s_sens.get())
            self.cfg.save_setting("hold_time", s_hold.get())
            win.destroy()
            
        tk.Button(win, text="ПРИМЕНИТЬ", command=save, bg=ACCENT_COLOR, fg="black", font=("Arial", 10, "bold"), relief="flat").pack(pady=20)
        
        self.root.wait_window(win)
        self.ui_blocked = False

class HudOverlay:
    def __init__(self):
        self.win = tk.Toplevel()
        self.win.overrideredirect(True)
        self.win.wm_attributes("-topmost", True)
        
        if platform.system() == "Windows":
            self.win.wm_attributes("-alpha", 0.7)
            self.win.configure(bg="black")
        else:
            self.win.configure(bg="#111111")
            
        self.label = tk.Label(self.win, text="INIT", font=("Consolas", 11), fg=ACCENT_COLOR, bg=self.win["bg"], justify=tk.LEFT)
        self.label.pack(padx=10, pady=5, anchor="w")
        
        h = self.win.winfo_screenheight()
        self.win.geometry(f"250x60+20+{h-150}")

    def update(self, mode, gesture, app_title):
        app_short = (app_title[:18] + '..') if len(app_title) > 18 else app_title
        txt = f"[{mode}]\nGesture: {gesture or '--'}\nScope: {app_short}"
        self.label.config(text=txt)
        self.win.update()

def is_cam_window_active():
    if gw:
        try:
            w = gw.getActiveWindow()
            if w and "GestureCam" in w.title: return True
        except: pass
    return True 

def main():
    app = AppController()
    engine = GestureEngine()
    actor = ActionHandler()
    hud = HudOverlay()
    
    cap = cv2.VideoCapture(0)
    if not NO_PREVIEW:
        cv2.namedWindow("GestureCam", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("GestureCam", 640, 480)

    is_following = False
    is_dragging = False
    prev_x, prev_y = None, None
    curr_gest = None
    gest_time = 0
    triggered = False
    btn_cooldown = 0
    
    pending_save_landmarks = None
    pending_save_frame = None

    print("--- SYSTEM READY ---")

    while True:
        if pending_save_landmarks and pending_save_frame is not None:
            paused_view = pending_save_frame.copy()
            draw_ui_text(paused_view, "FROZEN: SAVING...", (20, 50))
            cv2.imshow("GestureCam", paused_view)
            cv2.waitKey(1) 
            
            while keyboard.is_pressed('s'):
                app.root.update()
                time.sleep(0.01)

            app.root.update()
            app.save_sequence("GLOBAL", pending_save_landmarks)
            
            pending_save_landmarks = None
            pending_save_frame = None
            continue

        if app.ui_blocked:
            hud.update("MENU OPEN", None, "System")
            app.root.update()
            time.sleep(0.05)
            continue

        success, frame = cap.read()
        if not success: break
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        
        results = engine.process_frame(frame)
        
        active_app_title = "GLOBAL"
        if gw:
            try:
                w_obj = gw.getActiveWindow()
                if w_obj and w_obj.title: active_app_title = w_obj.title
            except: pass

        detected_name = None
        
        if results.multi_hand_landmarks:
            lm = results.multi_hand_landmarks[0]
            engine.mp_draw.draw_landmarks(frame, lm, engine.mp_hands.HAND_CONNECTIONS, landmark_drawing_spec=engine.draw_spec)
            
            detected_name, _ = engine.find_matching_gesture(lm, app.cfg.get_gestures())
            
            if is_following:
                ix, iy = lm.landmark[8].x, lm.landmark[8].y
                if prev_x is None: prev_x, prev_y = ix, iy
                sens = app.cfg.config["settings"]["trackpad_sensitivity"]
                dx = (ix - prev_x) * w * sens
                dy = (iy - prev_y) * h * sens
                if abs(dx) > 1 or abs(dy) > 1:
                    pyautogui.moveRel(dx, dy)
                prev_x, prev_y = ix, iy
                dist = np.hypot(lm.landmark[4].x - lm.landmark[8].x, lm.landmark[4].y - lm.landmark[8].y)
                cx, cy = int(lm.landmark[8].x * w), int(lm.landmark[8].y * h)
                if dist < 0.04:
                    cv2.circle(frame, (cx, cy), 15, (0, 0, 255), -1)
                    if not is_dragging:
                        pyautogui.mouseDown()
                        is_dragging = True
                else:
                    cv2.circle(frame, (cx, cy), 10, (0, 255, 255), -1)
                    if is_dragging:
                        pyautogui.mouseUp()
                        is_dragging = False
        else:
            prev_x = None

        if detected_name and not is_dragging:
            if detected_name == curr_gest:
                dur = time.time() - gest_time
                hold = app.cfg.config["settings"]["hold_time"]
                progress_ratio = min(dur / hold, 1.0)
                bw = int(progress_ratio * 200)
                if not NO_PREVIEW:
                    cv2.rectangle(frame, (20, h-40), (220, h-30), (50, 50, 50), -1)
                    cv2.rectangle(frame, (20, h-40), (20+bw, h-30), (0, 255, 0), -1)
                if dur >= hold and not triggered:
                    act = app.cfg.get_action(detected_name, active_app_title)
                    if act == "special:toggle_follow":
                        is_following = not is_following
                        prev_x = None
                        if not is_following: 
                            is_dragging = False
                            pyautogui.mouseUp()
                    elif act:
                        actor.execute(act)
                        cv2.rectangle(frame, (0,0), (w,h), (0,255,0), 10)
                    triggered = True
            else:
                curr_gest = detected_name
                gest_time = time.time()
                triggered = False
        else:
            curr_gest = None
            triggered = False

        if is_cam_window_active() and time.time() - btn_cooldown > 0.5:
            if not NO_PREVIEW and is_cam_window_active() and time.time() - btn_cooldown > 0.5:
                if keyboard.is_pressed('q'):
                    break
                elif keyboard.is_pressed('l'):
                    btn_cooldown = time.time()
                    app.open_manager()
                elif keyboard.is_pressed('o'):
                    btn_cooldown = time.time()
                    app.open_settings()
                elif keyboard.is_pressed('s'):
                    btn_cooldown = time.time()
                    if results.multi_hand_landmarks:
                        pending_save_landmarks = engine.normalize_landmarks(results.multi_hand_landmarks[0].landmark)
                        pending_save_frame = frame.copy()
                    else:
                        print("!!! НЕТ РУКИ В КАДРЕ !!!")

        mode_txt = "MOUSE: ON" if is_following else "GESTURE"
        hud.update(mode_txt, curr_gest, active_app_title)
        if not NO_PREVIEW:
            if results.multi_hand_landmarks:
                lm = results.multi_hand_landmarks[0]
                engine.mp_draw.draw_landmarks(frame, lm, engine.mp_hands.HAND_CONNECTIONS, landmark_drawing_spec=engine.draw_spec)
            draw_ui_text(frame, "KEYS: S(Save) L(List) O(Opts) Q(Quit)", (10, 30))
            cv2.imshow("GestureCam", frame)
        try:
            app.root.update()
        except: pass
        cv2.waitKey(1)

    cap.release()
    cv2.destroyAllWindows()
    hud.win.destroy()
    app.root.destroy()

if __name__ == "__main__":
    main()