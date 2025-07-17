# === Password Prompt Class ===
class PasswordPrompt:
    def __init__(self, timeout=30):
        self.timeout = timeout
        self.correct = False

        self.root = tk.Tk()
        self.root.title("🔐 Authentication Required")
        self.root.geometry("300x150")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.label = tk.Label(self.root, text="Enter password to stop monitoring:")
        self.label.pack(pady=(10, 0))

        self.entry = tk.Entry(self.root, show="*")
        self.entry.pack(pady=5)
        self.entry.focus()

        self.submit_btn = tk.Button(self.root, text="Submit", command=self.check_password)
        self.submit_btn.pack(pady=(5, 10))

        self.timer_label = tk.Label(self.root, text=f"⏳ Time remaining: {self.timeout}s")
        self.timer_label.pack()

        self.remaining = self.timeout
        self.update_timer()

    def check_password(self):
        if self.entry.get() == correct_password:
            self.correct = True
        self.root.destroy()

    def update_timer(self):
        if self.remaining > 0:
            if self.is_minimized():
                print("❌ Prompt minimized.")
                self.root.destroy()
                return
            self.timer_label.config(text=f"⏳ Time remaining: {self.remaining}s")
            self.remaining -= 1
            self.root.after(1000, self.update_timer)
        else:
            self.root.destroy()

    def is_minimized(self):
        hwnd = win32gui.GetForegroundWindow()
        return win32gui.IsIconic(hwnd)

    def on_close(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()
        return self.correct
    
# === Run Prompt ===
if PasswordPrompt(timeout=30).run():
    print("✅ Password correct. Exiting monitor.")
    sys.exit(0)

# === Password wrong or skipped ===
print("❌ Access denied or skipped. Starting monitoring...")
