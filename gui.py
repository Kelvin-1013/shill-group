import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yaml
import os
import asyncio
import csv
from datetime import datetime
from telethon.errors import FloodWaitError
from tg_shill_bot import TelegramBot
from spintax import SpinTax

class ShillBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Group Messenger")
        self.root.geometry("800x600")
        
        # Initialize variables
        self.bots = []
        self.is_logged_in = False
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Setup UI
        self.setup_ui()
        
        # Load settings
        self.load_settings()

    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Login section
        login_frame = ttk.LabelFrame(main_frame, text="Account")
        login_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.login_button = ttk.Button(login_frame, text="Login", command=self.start_login)
        self.login_button.grid(row=0, column=0, padx=5)
        
        self.load_session_button = ttk.Button(login_frame, text="Load Session", command=self.load_session)
        self.load_session_button.grid(row=0, column=1, padx=5)
        
        # Message section
        message_frame = ttk.LabelFrame(main_frame, text="Message")
        message_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.message_text = tk.Text(message_frame, height=6, width=70)
        self.message_text.grid(row=0, column=0, padx=5, pady=5)
        
        # SpinTax checkbox
        self.use_spintax = tk.BooleanVar()
        ttk.Checkbutton(message_frame, text="Use SpinTax", variable=self.use_spintax).grid(row=1, column=0)
        
        # Buttons
        button_frame = ttk.Frame(message_frame)
        button_frame.grid(row=2, column=0, pady=5)
        
        ttk.Button(button_frame, text="Send to Group", command=self.send_to_group).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Save Groups", command=self.save_groups).grid(row=0, column=1, padx=5)
        
        # Log section
        log_frame = ttk.LabelFrame(main_frame, text="Log")
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.log_text = tk.Text(log_frame, height=10, width=70)
        self.log_text.grid(row=0, column=0, padx=5, pady=5)

    def load_settings(self):
        try:
            with open('settings.yml', 'r') as f:
                self.settings = yaml.safe_load(f)
        except Exception as e:
            self.log_message(f"Error loading settings: {str(e)}")
            self.settings = {}

    def log_message(self, message):
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)

    def start_login(self):
        dialog = AccountDialog(self.root)
        if dialog.result:
            self.loop.run_until_complete(self.process_login(dialog.result))

    async def process_login(self, credentials):
        try:
            api_id, api_hash, phone = credentials
            bot = TelegramBot()
            success, message = await bot.connect(api_id, api_hash, phone)
            
            if not success and message == "Code requested":
                code_dialog = CodeDialog(self.root)
                if code_dialog.result:
                    success, message = await bot.sign_in(phone, code_dialog.result)
            
            if success:
                self.bots.append(bot)
                self.is_logged_in = True
                self.log_message(f"Successfully logged in with {phone}")
            else:
                messagebox.showerror("Error", message)
                
        except Exception as e:
            messagebox.showerror("Error", f"Login failed: {str(e)}")

    def save_groups(self):
        dialog = GroupsDialog(self.root)
        if dialog.result:
            try:
                groups = dialog.result.split('\n')
                groups = [g.strip() for g in groups if g.strip()]
                
                os.makedirs('./data', exist_ok=True)
                with open('./data/groups.csv', 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['group_name'])
                    for group in groups:
                        writer.writerow([group])
                
                self.log_message(f"Saved {len(groups)} groups")
                messagebox.showinfo("Success", f"Saved {len(groups)} groups")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save groups: {str(e)}")

    async def send_to_group_async(self):
        if not self.bots:
            raise ValueError("Please login first")

        message = self.message_text.get("1.0", tk.END).strip()
        if not message:
            raise ValueError("Please enter a message")

        if not os.path.exists('./data/groups.csv'):
            raise ValueError("No groups found. Please save groups first.")

        # Read groups
        groups = []
        with open('./data/groups.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            groups = [row['group_name'] for row in reader]

        if not groups:
            raise ValueError("No groups found in groups.csv")

        # Process SpinTax if enabled
        if self.use_spintax.get():
            message = SpinTax.parse(message)

        # Send message to each group
        for group in groups:
            try:
                entity = await self.bots[0].client.get_entity(group)
                await self.bots[0].client.send_message(entity, message)
                self.log_message(f"Sent message to {group}")
                await asyncio.sleep(60)  # Wait 1 minute between groups
            except FloodWaitError as e:
                self.log_message(f"Rate limit hit, waiting {e.seconds} seconds")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                self.log_message(f"Error sending to {group}: {str(e)}")

    def send_to_group(self):
        try:
            self.loop.run_until_complete(self.send_to_group_async())
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_session(self):
        try:
            filename = filedialog.askopenfilename(
                title="Select Session File",
                filetypes=[("Telethon Session", "*.session")],
                initialdir="./sessions"
            )
            
            if not filename:
                return
                
            with open('settings.yml', 'r') as f:
                settings = yaml.safe_load(f)
            
            api_id = settings.get('api_id')
            api_hash = settings.get('api_hash')
            
            if not api_id or not api_hash:
                raise ValueError("API credentials not found in settings.yml")
            
            phone = os.path.splitext(os.path.basename(filename))[0]
            
            bot = TelegramBot()
            success, message = self.loop.run_until_complete(
                bot.connect(api_id, api_hash, phone)
            )
            
            if success:
                self.bots.append(bot)
                self.is_logged_in = True
                self.log_message(f"Successfully loaded session for {phone}")
                messagebox.showinfo("Success", "Session loaded successfully")
            else:
                messagebox.showerror("Error", message)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load session: {str(e)}")

class AccountDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Login")
        self.result = None
        
        ttk.Label(self, text="API ID:").grid(row=0, column=0, padx=5, pady=5)
        self.api_id = ttk.Entry(self)
        self.api_id.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(self, text="API Hash:").grid(row=1, column=0, padx=5, pady=5)
        self.api_hash = ttk.Entry(self)
        self.api_hash.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(self, text="Phone:").grid(row=2, column=0, padx=5, pady=5)
        self.phone = ttk.Entry(self)
        self.phone.grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Button(self, text="OK", command=self.ok).grid(row=3, column=0, padx=5, pady=5)
        ttk.Button(self, text="Cancel", command=self.cancel).grid(row=3, column=1, padx=5, pady=5)

    def ok(self):
        try:
            api_id = int(self.api_id.get())
            api_hash = self.api_hash.get()
            phone = self.phone.get()
            if api_hash and phone:
                self.result = (api_id, api_hash, phone)
                self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Invalid API ID")

    def cancel(self):
        self.destroy()

class CodeDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Enter Code")
        self.result = None
        
        ttk.Label(self, text="Enter the code sent to your phone:").grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        self.code = ttk.Entry(self)
        self.code.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        
        ttk.Button(self, text="OK", command=self.ok).grid(row=2, column=0, padx=5, pady=5)
        ttk.Button(self, text="Cancel", command=self.cancel).grid(row=2, column=1, padx=5, pady=5)

    def ok(self):
        code = self.code.get()
        if code:
            self.result = code
            self.destroy()

    def cancel(self):
        self.destroy()

class GroupsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Save Groups")
        self.result = None
        
        ttk.Label(self, text="Enter group names (one per line):").grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        
        self.text = tk.Text(self, height=10, width=40)
        self.text.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        
        ttk.Button(self, text="Save", command=self.save).grid(row=2, column=0, padx=5, pady=5)
        ttk.Button(self, text="Cancel", command=self.cancel).grid(row=2, column=1, padx=5, pady=5)

    def save(self):
        self.result = self.text.get("1.0", tk.END).strip()
        self.destroy()

    def cancel(self):
        self.destroy()

def launch_gui():
    root = tk.Tk()
    app = ShillBotGUI(root)
    root.mainloop() 