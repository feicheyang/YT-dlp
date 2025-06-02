import os
import subprocess
import tkinter as tk
from tkinter import filedialog, ttk
import threading
import sys  # 导入sys模块
import json
import requests
import ctypes

CONFIG_DIR = os.path.join(os.getenv("APPDATA"), "YTBDownloader")
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f)

class SimpleDownloader:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1280x720")
        self.root.configure(bg="white")

        config = load_config()
        self.save_path = config.get("save_path", os.getcwd())
        self.cookies_path = config.get("cookies_path", "")

        # 检查是否以管理员身份运行
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except:
            is_admin = False

        # 更新窗口标题
        admin_status = "以管理员身份运行" if is_admin else "非管理员身份运行"
        self.root.title(f"YTB视频下载器-3.0 - {admin_status}")

        self.create_menu()
        self.create_widgets()
        self.cookies_valid = False
        self.current_process = None
        self.download_info = {}  # 用于存储下载信息

        self.check_and_update_yt_dlp()  # 启动时检测并更新 yt-dlp

        self.check_cookies_on_startup()   # 启动时检测 cookies 是否可用

        self.show_home()  # 启动时直接显示主页
        
    def check_cookies_on_startup(self):
        def check():
            self.log("🕒 启动时检测 Cookies 可用性...", category="Cookies")
            valid = self.check_cookies_valid()
            self.cookies_valid = valid
            self.log(f"🍪 Cookies 🔍启动检测结果：{'✅ 可用' if valid else '❌ 不可用'}", category="Cookies")
        threading.Thread(target=check).start()

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        menubar.add_command(label="🏠 主页", command=self.show_home)
        menubar.add_command(label="📝 日志", command=self.show_log)
        menubar.add_command(label="⚙️ 设置", command=self.show_settings)

    def check_cookies_valid(self):
        if not self.cookies_path or not os.path.exists(self.cookies_path):
            return False
        try:
            test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            cmd = ["yt-dlp", "--cookies", self.cookies_path, "--dump-json", test_url]
            creationflags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, creationflags=creationflags)
            return result.returncode == 0 and "LOGIN_REQUIRED" not in result.stderr
        except Exception:
            return False

    def create_widgets(self):
        config = load_config()
        self.settings_frame = tk.Frame(self.root, bg="white")

        # 外层主页容器
        self.main_frame = tk.Frame(self.root, bg="white")
        self.main_frame.pack(fill="both", expand=True)

    # 主下载任务标签页
        self.main_tabs = ttk.Notebook(self.main_frame)
        self.normal_tab = tk.Frame(self.main_tabs, bg="white")
        self.custom_tab = tk.Frame(self.main_tabs, bg="white", height=10)
        self.main_tabs.add(self.normal_tab, text="📥 普通下载")
        self.main_tabs.add(self.custom_tab, text="📥 高级下载")

        # 高级下载内容补全
        custom_frame = tk.Frame(self.custom_tab, bg="white")
        custom_frame.pack(pady=10, padx=10, anchor="center")

        icon_button_frame = tk.Frame(custom_frame, bg="white")
        icon_button_frame.grid(row=0, column=2, rowspan=2, padx=(10, 0), pady=(0, 10))

        search_icon_path = resource_path(os.path.join("icons", "搜索1.png"))
        search_icon = tk.PhotoImage(file=search_icon_path).subsample(12, 12)
        self.search_icon = search_icon

        download2_icon_path = resource_path(os.path.join("icons", "下载2.png"))
        download2_icon = tk.PhotoImage(file=download2_icon_path).subsample(12, 12)
        self.download2_icon = download2_icon

        tk.Label(custom_frame, text="视频链接：", bg="white", font=(None, 10)).grid(row=0, column=0, sticky="e")
        self.custom_url_entry = tk.Entry(custom_frame, width=60, bd=1, relief="solid", bg="white", highlightthickness=1, highlightbackground="#CCCCCC", fg="black", font=(None, 10))
        self.custom_url_entry.grid(row=0, column=1, padx=5)

        tk.Label(custom_frame, text="格式编号：", bg="white", font=(None, 10)).grid(row=1, column=0, sticky="e")
        self.custom_format_entry = tk.Entry(custom_frame, width=60, bd=1, relief="solid", bg="white", highlightthickness=1, highlightbackground="#CCCCCC", fg="black", font=(None, 10))
        self.custom_format_entry.grid(row=1, column=1, padx=5, sticky="w")

        tk.Button(icon_button_frame, image=search_icon, command=self.query_formats, relief="flat", bg="white", activebackground="white", highlightthickness=0, bd=0).pack(pady=(0, 10))
        tk.Button(icon_button_frame, image=download2_icon, command=self.download_selected_format, relief="flat", bg="white", activebackground="white", highlightthickness=0, bd=0).pack()

        self.format_listbox = tk.Listbox(self.custom_tab, font=(None, 10), bg="white", bd=1, relief="solid")
        self.format_listbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.custom_speed_label = tk.Label(self.custom_tab, text="📅 等待下载...", bg="white", font=(None, 10), fg="black")
        self.custom_speed_label.pack(side="bottom", pady=(10, 10), anchor="s")

        # 普通下载区域
        frame = tk.Frame(self.normal_tab, bg="white")
        frame.pack(pady=10)

        tk.Label(frame, text="视频链接：", font=(None, 10), bg="white").grid(row=0, column=0, padx=5)
        self.url_entry = tk.Entry(frame, width=60, bd=1, relief="solid", bg="white", highlightthickness=1, highlightbackground="#CCCCCC", fg="black", font=(None, 10))
        self.url_entry.grid(row=0, column=1, padx=5)

        icon_path = resource_path(os.path.join("icons", "文1.png"))
        download_icon = tk.PhotoImage(file=icon_path).subsample(9, 9)
        tk.Button(frame, image=download_icon, command=self.start_download, relief="flat", bg="white", activebackground="white", highlightthickness=0, bd=0).grid(row=0, column=2, padx=5)
        self.download_icon = download_icon

        icon_path_mp3 = resource_path(os.path.join("icons", "文2.png"))
        download_icon_mp3 = tk.PhotoImage(file=icon_path_mp3).subsample(10, 10)
        self.download_icon_mp3 = download_icon_mp3
        self.extra_download_button = tk.Button(frame, image=download_icon_mp3, command=self.download_as_mp3, relief="flat", bg="white", activebackground="white", highlightthickness=0, bd=0)
        self.extra_download_button.grid(row=0, column=4, padx=5)

        # 📻 画质选择区域，直接放在视频链接下方 frame 内部新一行
        tk.Label(frame, text="📻 选择画质：", font=(None, 10), bg="white").grid(row=1, column=0, padx=5, pady=(10, 0), sticky="e")
        self.format_var = tk.StringVar(value="4K")
        options = ["4K", "2K", "1080P", "720P", "480P"]
        self.quality_combobox = ttk.Combobox(frame, textvariable=self.format_var, values=options, width=10, state="readonly")
        self.quality_combobox.set("4K")
        self.quality_combobox.grid(row=1, column=1, sticky="w", pady=(10, 0))

        self.quality_frame = tk.Frame(self.normal_tab, bg="white", height=0)
        self.quality_frame.pack_forget()

        self.task_listbox = tk.Listbox(self.normal_tab, bd=1, relief="solid", bg="white", highlightthickness=1, highlightbackground="#CCCCCC", fg="black", font=(None, 10))
        self.task_listbox.pack(fill="both", expand=True, padx=10, pady=10)

        # 下载状态标签
        self.download_status_label = tk.Label(self.normal_tab, text="📅 等待下载...", bg="white", font=(None, 10), fg="black")
        self.download_status_label.pack(pady=(0, 10))

        self.log_frame = tk.Frame(self.root, bg="white")

        self.log_notebook = ttk.Notebook(self.log_frame)
        self.log_notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.download_log_text_frame = tk.Frame(self.log_notebook, bg="white")
        self.download_log_text_frame.pack(fill="both", expand=True)

        self.download_log_text = tk.Text(self.download_log_text_frame, height=15, wrap="word", bg="white", font=(None, 10))
        self.download_log_text.pack(side="left", fill="both", expand=True)
        self.download_log_text.bind("<Control-c>", lambda e: self.copy_selected(self.download_log_text))

        download_scroll = tk.Scrollbar(self.download_log_text_frame, command=self.download_log_text.yview)
        download_scroll.pack(side="right", fill="y")
        self.download_log_text.configure(yscrollcommand=download_scroll.set)

        self.download_log_text.config(state="disabled")
        self.custom_log_text = self.download_log_text
        self.log_notebook.add(self.download_log_text_frame, text="📅 运行下载日志")

        self.cookies_log_text = tk.Text(self.log_notebook, height=15, wrap="word", bg="white", font=(None, 10))
        self.cookies_log_text.bind("<Control-c>", lambda e: self.copy_selected(self.cookies_log_text))
        cookies_scroll = tk.Scrollbar(self.cookies_log_text, command=self.cookies_log_text.yview)
        self.cookies_log_text.configure(yscrollcommand=cookies_scroll.set)
        cookies_scroll.pack(side="right", fill="y")
        self.cookies_log_text.config(state="disabled")
        self.log_notebook.add(self.cookies_log_text, text="🍪 Cookies日志")

        clear_frame = tk.Frame(self.log_frame, bg="white")
        clear_frame.pack(pady=5)
        tk.Button(clear_frame, text="🧹 清空下载日志", command=self.clear_download_log).pack(side="left", padx=10)
        tk.Button(clear_frame, text="🧹 清空Cookies日志", command=self.clear_cookies_log).pack(side="left", padx=10)
      
        # 创建右键菜单
        self.task_menu = tk.Menu(self.root, tearoff=0)
        self.task_menu.add_command(label="重新下载", command=self.retry_download)
        self.task_menu.add_command(label="取消下载", command=self.cancel_download)

        # 绑定右键菜单到任务列表框
        self.task_listbox.bind("<Button-3>", self.show_task_menu)

        tk.Label(self.settings_frame, text="📂 yt-dlp 安装路径：", font=(None, 10)).grid(row=2, column=0, sticky="w")
        self.yt_dlp_path_label = tk.Label(self.settings_frame, text="C:\\Windows\\System32\\yt-dlp.exe", font=(None, 10))
        self.yt_dlp_path_label.grid(row=2, column=1, sticky="w")

    def download_as_mp3(self):
        url = self.url_entry.get().strip()
        if not url:
            self.log("请填写视频链接", category="下载")
            return
        self.format_var = tk.StringVar(value="MP3")
        self.confirm_download()

    def log(self, message, category="下载"):
        widget = self.download_log_text if category == "下载" else self.cookies_log_text
        def append():
            widget.config(state="normal")
            widget.insert(tk.END, f"{message}\n")
            widget.see(tk.END)  # 自动滚动到底部
            widget.config(state="disabled")
        self.root.after(0, append)

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            self.log("请填写视频链接,下载视频", category="下载")
            return

        if hasattr(self, 'quality_frame'):
            self.quality_frame.pack_forget()

        self.confirm_download()

    def confirm_download(self):
        urls = self.url_entry.get().split()
        if not urls:
            self.log("请填写链接！", category="下载")
            return

        format_code = self.format_var.get()
        existing_tasks = [self.task_listbox.get(i) for i in range(self.task_listbox.size())]

        for url in urls:
            # 初始显示URL
            filename = url.split("?")[0].split("/")[-1]
            is_downloading = any(
                task.startswith(f"{filename}: 准备下载") or
                task.startswith(f"{filename}: ⬇️ 下载中")
                for task in existing_tasks
            )

            if not is_downloading:
                for i in range(self.task_listbox.size()):
                    task = self.task_listbox.get(i)
                    if task.startswith(f"{filename}:"):
                        self.task_listbox.delete(i)
                        break

                self.task_listbox.insert(tk.END, f"{filename}: 准备下载...")

                # 在后台线程中获取标题并替换
                def update_title():
                    title = self.get_video_title(url, filename)
                    self.root.after(0, lambda: self.replace_task(filename, title, "⬇️ 下载中..."))

                threading.Thread(target=update_title).start()

                self.download_video(url, format_code, filename)
                self.hide_quality_panel()

    def get_video_title(self, url, fallback_name):
        try:
            cmd_title = ["yt-dlp", "--get-title", url]
            if self.cookies_path:
                cmd_title += ["--cookies", self.cookies_path]
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(cmd_title, capture_output=True, text=True, creationflags=creationflags)
            if result.returncode == 0:
                title = result.stdout.strip()
                self.log(f"获取到的标题: {title}", category="下载")
                return title
            else:
                self.log("未能获取标题，使用备用名称", category="下载")
                return fallback_name  # 如果获取标题失败，使用备用名称
        except Exception as e:
            self.log(f"❌ 获取标题失败: {e}", category="下载")
            return fallback_name

    def download_video(self, url, format_code, filename):
        def run():
            # 在子线程中获取标题
            title = self.get_video_title(url, filename)

            # 保存下载信息
            self.download_info[title] = (url, format_code)
            self.root.after(0, lambda: self.update_task(title, "⬇️ 下载中..."))
            self.log(f"存储下载信息：{title}, URL: {url}, Format: {format_code}", category="下载")
            self.log(f"⬇️开始下载：{url}", category="下载")

            format_map = {
                "4K": "bestvideo[height<=2160]+bestaudio/best",
                "2K": "bestvideo[height<=1440]+bestaudio/best",
                "1080P": "bestvideo[height<=1080]+bestaudio/best",
                "720P": "bestvideo[height<=720]+bestaudio/best",
                "480P": "bestvideo[height<=480]+bestaudio/best",
            }

            selected_format = format_map.get(format_code, "bestvideo+bestaudio/best")

            cmd = [
                "yt-dlp",
                "--progress",
                "--newline",
                "-f", selected_format,
                "--merge-output-format", "mp4",
                "--output", os.path.join(self.save_path, "%(title)s.%(ext)s"),
                url
            ]

            if format_code == "MP3":
                cmd = [
                    "yt-dlp",
                    "--progress",
                    "--newline",
                    "-x", "--audio-format", "mp3",
                    "--output", os.path.join(self.save_path, "%(title)s.%(ext)s"),
                    url
                ]

            if self.cookies_path:
                cmd += ["--cookies", self.cookies_path]

            try:
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    creationflags=creationflags
                )
                self.current_process = process

                for line in iter(process.stdout.readline, ''):
                    if line:
                        self.log(line.strip(), category="下载")
                        self.root.after(0, lambda l=line: self.update_download_status(l.strip()))

                process.stdout.close()
                process.wait()
                self.current_process = None

                if process.returncode == 0:
                    self.root.after(0, lambda: self.update_task(title, "✅ 下载完成"))
                    self.log(f"✅ 下载完成")
                else:
                    self.root.after(0, lambda: self.update_task(title, "❌ 下载失败"))
                    self.log(f"❌ 下载失败")        
            except Exception as e:              
                self.root.after(0, lambda: self.update_task(title, "❌ 下载异常"))       
                self.log(str(e), category="下载")
                self.current_process = None

        threading.Thread(target=run).start()

    def update_task(self, title, status):
        for i in range(self.task_listbox.size()):
            if self.task_listbox.get(i).startswith(title + ":"):
                self.task_listbox.delete(i)
                self.task_listbox.insert(i, f"{title}: {status}")
                return
        # 同步到普通下载列表
        for i in range(self.format_listbox.size()):
            if self.format_listbox.get(i).startswith(title + ":"):
                self.format_listbox.delete(i)
                self.format_listbox.insert(i, f"{title}: {status}")
                return

    def show_log(self):
        self.clear_frames()
        self.log_frame.pack(fill="both", expand=True)

    def show_home(self):
        self.clear_frames()
        self.main_frame.pack(fill="both", expand=True)
        self.main_tabs.pack(fill="both", expand=True)
        self.main_tabs.select(self.normal_tab)

    def show_settings(self):
        self.clear_frames()
        self.settings_frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(self.settings_frame, text="📂 保存路径：", font=(None, 10)).grid(row=0, column=0, sticky="w")
        self.save_label = tk.Label(self.settings_frame, text=self.save_path, font=(None, 10))
        self.save_label.grid(row=0, column=1, sticky="w")
        tk.Button(self.settings_frame, text="📂 选择保存路径", command=self.choose_save_path).grid(row=0, column=2, padx=10)

        tk.Label(self.settings_frame, text="🍪 Cookies路径：", font=(None, 10)).grid(row=1, column=0, sticky="w")
        self.cookies_label = tk.Label(self.settings_frame, text=self.cookies_path, font=(None, 10))
        self.cookies_label.grid(row=1, column=1, sticky="w")
        tk.Button(self.settings_frame, text="🍪 选择Cookies文件", command=self.choose_cookies_path).grid(row=1, column=2, padx=10)
        tk.Button(self.settings_frame, text="🔍 点击检测", font=(None, 10), command=self.refresh_cookies_status).grid(row=1, column=3, padx=10)
        if hasattr(self, 'cookies_status_label'):
            self.cookies_status_label.destroy()
        self.cookies_status_label = tk.Label(self.settings_frame,
            text="✅ 可用" if self.cookies_valid else "❌ 不可用",
            fg="green" if self.cookies_valid else "red",
            font=(None, 10))
        self.cookies_status_label.grid(row=1, column=4, padx=10)

    def choose_save_path(self):
        path = filedialog.askdirectory()
        if path:
            threading.Thread(target=lambda: self.update_save_path(path)).start()

    def update_save_path(self, path):
        self.save_path = path
        self.save_label.config(text=path)
        config = load_config()
        config["save_path"] = path
        save_config(config)

    def choose_cookies_path(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            threading.Thread(target=lambda: self.update_cookies_path(path)).start()

    def update_cookies_path(self, path):
        self.cookies_path = path
        self.cookies_label.config(text=path)
        config = load_config()
        config["cookies_path"] = path
        save_config(config)
        self.refresh_cookies_status()

    def copy_selected(self, widget):
        try:
            selected_text = widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
        except tk.TclError:
            pass

    def update_download_status(self, line):
        import re
        match = re.search(r'\[download\]\s+(\d+(?:\.\d+)?)%\s+of\s+(\S+)\s+at\s+(\S+)\s+ETA\s+(\S+)', line)
        if match:
            percent, total_size, speed, eta = match.groups()
            text = f"📥 下载进度：{percent}%，总大小：{total_size}，下载速度：{speed}，剩余时间：{eta}"
            self.download_status_label.config(text=text)
            if hasattr(self, 'custom_speed_label'):
                self.custom_speed_label.config(text=text)
        elif '[download] 100%' in line or 'has already been downloaded' in line:
            self.download_status_label.config(text="✅ 下载完成")
            if hasattr(self, 'custom_speed_label'):
                self.custom_speed_label.config(text="✅ 下载完成")
        elif '[download] Destination:' in line:
            self.download_status_label.config(text="📥 开始下载...")
            if hasattr(self, 'custom_speed_label'):
                self.custom_speed_label.config(text="📥 开始下载...")


    def clear_cookies_log(self):
        self.cookies_log_text.config(state="normal")
        self.cookies_log_text.delete("1.0", tk.END)
        self.cookies_log_text.config(state="disabled")

    def clear_download_log(self):
        self.download_log_text.config(state="normal")
        self.download_log_text.delete("1.0", tk.END)
        self.download_log_text.config(state="disabled")

    def refresh_cookies_status(self):
        self.cookies_status_label.config(
            text="🕒 检测中...",
            fg="orange"
        )
        def check():
            self.log("🕒 开始检测 🍪Cookies 可用性...", category="Cookies")
            valid = self.check_cookies_valid()
            self.cookies_valid = valid
            self.cookies_status_label.config(
                text="✅ 可用" if valid else "❌ 不可用",
                fg="green" if valid else "red"
            )
            self.log(f"🍪 Cookies 🔍 检测完成：{'✅ 可用' if valid else '❌ 不可用'}", category="Cookies")
        threading.Thread(target=check).start()

    def log_custom(self, message):
        def append():
            self.download_log_text.config(state="normal")
            self.download_log_text.insert(tk.END, f"{message}/n")
            self.download_log_text.see(tk.END)
            self.download_log_text.config(state="disabled")
        self.root.after(0, append)

    def download_selected_format(self):
        url = self.custom_url_entry.get().strip()
        format_id = self.custom_format_entry.get().strip()
        if not url or not format_id:
            self.log("请输入链接和格式编号", category="下载")
            return

        # 在下载队列中添加初始任务
        filename = url.split("?")[0].split("/")[-1]
        self.task_listbox.insert(tk.END, f"{filename}: 准备下载...")

        def run():
            # 在子线程中获取标题
            title = self.get_video_title(url, filename)

            # 更新任务为视频标题
            self.root.after(0, lambda: self.replace_task(filename, title, "⬇️ 下载中..."))

            # 保存下载信息
            self.download_info[title] = (url, format_id)
            self.log(f"存储下载信息：{title}, URL: {url}, Format: {format_id}", category="下载")

            self.root.after(0, lambda: self.update_task(title, "⬇️ 下载中..."))
            self.log(f"⬇️ 开始使用格式 {format_id} 下载 {url}", category="下载")
            output_path = os.path.join(self.save_path, "%(title)s.%(ext)s")

            cmd = [
                "yt-dlp",
                "--progress",
                "--newline",
                "-f", format_id,
                "--output", output_path,
                url
            ]

            if format_id.isdigit():
                try:
                    fmt_num = int(format_id)
                    if fmt_num < 200:
                        cmd = [
                            "yt-dlp",
                            "--progress",
                            "--newline",
                            "-f", format_id,
                            "-x", "--audio-format", "mp3",
                            "--ffmpeg-location", "ffmpeg",
                            "--output", output_path,
                            url
                        ]
                except:
                    pass

            if self.cookies_path:
                cmd += ["--cookies", self.cookies_path]

            try:
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=creationflags)
                self.current_process = process

                for line in iter(process.stdout.readline, ''):
                    if line:
                        self.log(line.strip(), category="下载")
                        self.root.after(0, lambda l=line: self.update_download_status(l.strip()))

                process.stdout.close()
                process.wait()
                self.current_process = None

                if process.returncode == 0:
                    self.log("✅ 下载完成", category="下载")
                    self.root.after(0, lambda: self.update_task(title, "✅ 下载完成"))
                else:
                    self.log("❌ 下载失败", category="下载")
                    self.root.after(0, lambda: self.update_task(title, "❌ 下载失败"))
            except Exception as e:
                self.log(f"❌ 下载异常: {e}", category="下载")
                self.root.after(0, lambda: self.update_task(title, "❌ 下载异常"))
                self.current_process = None

        threading.Thread(target=run).start()


    def query_formats(self):
        url = self.custom_url_entry.get().strip()
        if not url:
            self.log("请输入视频链接用于格式查询", category="下载")
            return

        def run():
            self.log(f"🔍 正在获取格式列表：{url}", category="下载")
            cmd = ["yt-dlp", "-F", url]
            if self.cookies_path:
                cmd += ["--cookies", self.cookies_path]
            try:
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                result = subprocess.run(cmd, capture_output=True, text=True, creationflags=creationflags)
                self.format_listbox.delete(0, tk.END)
                if result.returncode == 0:
                    formats = result.stdout.splitlines()
                    for line in formats:
                        self.format_listbox.insert(tk.END, line)
                    self.log("✅ 格式列表获取完成", category="下载")
                else:
                    self.log("❌ 获取格式失败，请检查链接是否正确", category="下载")
            except Exception as e:
                self.log(f"❌ 异常：{e}", category="下载")
        threading.Thread(target=run).start()

    def clear_frames(self):
        for widget in self.root.winfo_children():
            widget.pack_forget()

    def show_task_menu(self, event):
        try:
            self.task_listbox.selection_clear(0, tk.END)
            self.task_listbox.selection_set(self.task_listbox.nearest(event.y))
            self.task_menu.post(event.x_root, event.y_root)
        except tk.TclError:
            pass

    def retry_download(self):
        selected = self.task_listbox.curselection()
        if selected:
            task = self.task_listbox.get(selected[0])
            filename = task.split(":")[0]
            self.log(f"重新下载：{filename}", category="下载")
            url, format_code = self.get_download_info(filename)
            if url is None:
                self.log("无法获取下载信息，URL 为空", category="下载")
                return
            self.download_video(url, format_code, filename)

    def get_download_info(self, filename):
        return self.download_info.get(filename, (None, None))

    def cancel_download(self):
        selected = self.task_listbox.curselection()
        if selected:
            task = self.task_listbox.get(selected[0])
            filename = task.split(":")[0]
            # 停止后台下载进程
            if self.current_process:
                try:
                    import psutil
                    parent = psutil.Process(self.current_process.pid)
                    for child in parent.children(recursive=True):
                        child.kill()
                    parent.kill()
                    self.log(f"⛔ 已经取消下载任务 {filename}", category="下载")
                except Exception as e:
                    self.log(f"❌ 无法取消下载任务: {e}", category="下载")
                self.current_process = None
            # 删除文件
            video_path = os.path.join(self.save_path, f"{filename}.mp4")
            audio_path = os.path.join(self.save_path, f"{filename}.m4a")
            for path in [video_path, audio_path]:
                if os.path.exists(path):
                    os.remove(path)
                    self.log(f"🗑️ 已删除文件 {path}", category="下载")
            # 删除队列
            self.task_listbox.delete(selected[0])
            # 更新底部状态栏
            self.download_status_label.config(text="⛔ 取消下载")
            # 更新高级下载区域的状态栏
            if hasattr(self, 'custom_speed_label'):
                self.custom_speed_label.config(text="⛔ 取消下载")

    def force_cancel_all_downloads(self):
        # 停止所有后台下载进程
        if self.current_process:
            try:
                import psutil
                parent = psutil.Process(self.current_process.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
                self.log("⛔ 已经强制终止所有下载任务", category="下载")
            except Exception as e:
                self.log(f"❌ 无法强制终止下载任务: {e}", category="下载")
            self.current_process = None

        # 清空任务列表
        self.task_listbox.delete(0, tk.END)
        self.log("🗑️ 已强制清空所有下载任务", category="下载")
        # 更新底部状态栏
        self.download_status_label.config(text="⛔ 取消下载")
        self.log("普通下载状态栏更新为取消下载", category="下载")
        # 更新高级下载区域的状态栏
        if hasattr(self, 'custom_speed_label'):
            self.custom_speed_label.config(text="⛔ 取消下载")
            self.log("高级下载状态栏更新为取消下载", category="下载")

    def check_and_update_yt_dlp(self):
        def run_check():
            def check():
                try:
                    self.log("🔍 检测 yt-dlp 版本中...", category="下载")
                    result = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    current_version = result.stdout.strip()

                    response = requests.get("https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest")
                    latest_version = response.json().get("tag_name", "未知版本")

                    if current_version != latest_version:
                        self.root.after(0, lambda: self.log(f"❌ yt-dlp 不是最新版本 (当前: {current_version}, 最新: {latest_version})，正在更新...", category="下载"))
                        self.update_yt_dlp()
                    else:
                        self.root.after(0, lambda: self.log(f"✅ yt-dlp 已是最新版本 ({current_version})", category="下载"))
                except Exception as e:
                    if "[WinError 2]" in str(e):
                        self.root.after(0, lambda: self.log("❌ 检测 yt-dlp 版本失败: 系统找不到指定的文件，正在下载最新的 yt-dlp...", category="下载"))
                        self.update_yt_dlp()
                    else:
                        self.root.after(0, lambda: self.log(f"❌ 检测 yt-dlp 版本失败: {e}", category="下载"))

            threading.Thread(target=check).start()

        threading.Thread(target=run_check).start()

    def update_yt_dlp(self):
        def run_update():
            self.log("⬇️ 正在下载最新的 yt-dlp...", category="下载")
            try:
                # 获取最新的 yt-dlp 可执行文件 URL
                response = requests.get("https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest")
                latest_release = response.json()
                assets = latest_release.get("assets", [])
                yt_dlp_url = None
                for asset in assets:
                    if asset.get("name") == "yt-dlp.exe":
                        yt_dlp_url = asset.get("browser_download_url")
                        break

                if not yt_dlp_url:
                    self.log("❌ 未找到 yt-dlp 可执行文件", category="下载")
                    return

                # 固定 yt-dlp 保存路径为 C:\Windows\System32
                yt_dlp_path = os.path.join("C:\\Windows\\System32", "yt-dlp.exe")

                # 下载 yt-dlp
                yt_dlp_response = requests.get(yt_dlp_url)
                with open(yt_dlp_path, "wb") as f:
                    f.write(yt_dlp_response.content)

                self.log(f"✅ yt-dlp 下载成功，已保存到 {yt_dlp_path}", category="下载")
            except Exception as e:
                self.log(f"❌ 下载 yt-dlp 失败: {e}", category="下载")

        threading.Thread(target=run_update).start()

    def replace_task(self, old_name, new_name, status):
        for i in range(self.task_listbox.size()):
            task = self.task_listbox.get(i)
            if task.startswith(f"{old_name}:"):
                self.task_listbox.delete(i)
                self.task_listbox.insert(i, f"{new_name}: {status}")
                return

import ctypes

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

if __name__ == "__main__":
    root = tk.Tk()
    icon_path = resource_path("icons/文2.ico")
    root.iconbitmap(default=icon_path)
    app = SimpleDownloader(root)
    root.mainloop()
