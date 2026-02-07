import tkinter as tk
from tkinter import filedialog, simpledialog, ttk
from PIL import Image, ImageGrab, ImageDraw, ImageTk
import os
import threading
import pystray
import time
import keyboard 

class ScreenshotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ScreenIvy")
        self.root.geometry("450x400")
        self.root.resizable(False, False)

        # Папка сохранения
        self.settings = {'save_dir': os.path.expanduser("~/Pictures/Screenshots")}
        os.makedirs(self.settings['save_dir'], exist_ok=True)

        self.status_var = tk.StringVar(value="Готов к работе")

        self.setup_style()
        self.create_interface()

        self.tray_icon = None
        self.overlay = None

        # Глобальный PrintScreen через keyboard
        threading.Thread(target=self.register_hotkey, daemon=True).start()

    # ---------- STYLE ----------
    def setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        self.root.configure(bg="#1e1e1e")
        style.configure("TFrame", background="#1e1e1e")
        style.configure("TLabel", background="#1e1e1e", foreground="#e5e5e5")
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("TButton", font=("Segoe UI", 11), padding=10)

    # ---------- UI ----------
    def create_interface(self):
        ttk.Label(self.root, text="Скриншот-менеджер", style="Title.TLabel").pack(pady=20)
        ttk.Label(self.root, textvariable=self.status_var).pack(pady=5)

        frame = ttk.Frame(self.root)
        frame.pack(pady=20, padx=30, fill=tk.X)

        ttk.Button(frame, text="📸 Сделать скриншот", command=self.start_capture).pack(fill=tk.X, pady=6)
        ttk.Button(frame, text="📁 Папка сохранения", command=self.choose_dir).pack(fill=tk.X, pady=6)
        ttk.Button(frame, text="🧷 Свернуть в трей", command=self.minimize_to_tray).pack(fill=tk.X, pady=6)
        ttk.Button(frame, text="❌ Выход", command=self.quit_app).pack(fill=tk.X, pady=6)

    # ---------- Глобальный PrintScreen ----------
    def register_hotkey(self):
        keyboard.add_hotkey("print_screen", lambda: self.start_capture())

    # ---------- SCREENSHOT ----------
    def start_capture(self):
        self.status_var.set("Выделите область...")
        self.show_overlay()

    def show_overlay(self):
        w = self.root.winfo_screenwidth()
        h = self.root.winfo_screenheight()

        # Cкриншот всего экрана
        try:
            self.fullscreen_image = ImageGrab.grab()
        except Exception as ex:
            self.status_var.set(f"Ошибка скриншота: {ex}")
            return

        # Конвертирование скриншота в PhotoImage
        self.tk_fullscreen = ImageTk.PhotoImage(self.fullscreen_image)

        # Скрытый overlay
        self.overlay = tk.Toplevel(self.root)
        self.overlay.withdraw()
        self.overlay.overrideredirect(True)
        self.overlay.attributes("-topmost", True)
        self.overlay.geometry(f"{w}x{h}+0+0")
        self.overlay.focus_set()

        # 4. Canvas и фон скриншота
        self.canvas = tk.Canvas(self.overlay, width=w, height=h, highlightthickness=0, cursor="cross")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_fullscreen)

        self.dark_rects = [
            self.canvas.create_rectangle(0,0,w,h, fill="black", stipple="gray25", outline="")
            for _ in range(4)
        ]

        self.start_x = self.start_y = 0
        self.rect = None

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.overlay.bind("<Escape>", self.cancel_capture)

        self.overlay.deiconify()

    def on_press(self, e):
        self.start_x, self.start_y = e.x, e.y
        self.rect = self.canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="#3b82f6", width=2, dash=(6,4))

    def on_drag(self, e):
        x1, y1 = self.start_x, self.start_y
        x2, y2 = e.x, e.y
        self.canvas.coords(self.rect, x1, y1, x2, y2)

        w, h = self.overlay.winfo_width(), self.overlay.winfo_height()
        x1s, x2s = sorted([x1, x2])
        y1s, y2s = sorted([y1, y2])
        self.canvas.coords(self.dark_rects[0], 0, 0, w, y1s)     
        self.canvas.coords(self.dark_rects[1], 0, y2s, w, h)     
        self.canvas.coords(self.dark_rects[2], 0, y1s, x1s, y2s) 
        self.canvas.coords(self.dark_rects[3], x2s, y1s, w, y2s) 

    def on_release(self, e):
        x1, x2 = sorted([self.start_x, e.x])
        y1, y2 = sorted([self.start_y, e.y])

        if x2 - x1 < 10 or y2 - y1 < 10:
            self.cancel_capture()
            return

        if self.overlay:
            self.overlay.destroy()
            self.overlay = None

        # Используем сделанный скриншот
        cropped = self.fullscreen_image.crop((x1, y1, x2, y2))

        name = simpledialog.askstring("Сохранение", "Имя файла:",
                                      initialvalue=time.strftime("Screenshot_%Y-%m-%d_%H-%M-%S"),
                                      parent=self.root)
        if not name or not name.strip():
            name = time.strftime("Screenshot_%Y-%m-%d_%H-%M-%S")

        name = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).strip()
        path = os.path.join(self.settings['save_dir'], f"{name}.png")
        cropped.save(path)

        self.status_var.set(f"Сохранено: {name}.png")

    def cancel_capture(self, event=None):
        if self.overlay:
            self.overlay.destroy()
            self.overlay = None
        self.status_var.set("Отменено")

    # ---------- SYSTEM ----------
    def choose_dir(self):
        path = filedialog.askdirectory(initialdir=self.settings['save_dir'])
        if path:
            self.settings['save_dir'] = path

    def minimize_to_tray(self):
        self.root.withdraw()
        self.create_tray()

    def create_tray(self):
        img = Image.new("RGBA", (64, 64))
        draw = ImageDraw.Draw(img)
        draw.rectangle((14,18,50,46), outline="black", width=3)

        menu = pystray.Menu(
            pystray.MenuItem("Открыть", lambda *_: self.restore()),
            pystray.MenuItem("Выход", lambda *_: self.quit_app())
        )

        self.tray_icon = pystray.Icon("screenshot", img, "Скриншот-менеджер", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def restore(self):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.root.after(0, self.root.deiconify)

    def quit_app(self):
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenshotApp(root)
    root.mainloop()