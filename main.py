import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os

class ADBFileManager:
    def __init__(self, root):
        self.root = root
        self.root.title("ADB File Manager")
        self.root.geometry("800x600")
        self.current_path = "/"
        self.create_widgets()
        self.list_files()

    def run_adb(self, args):
        try:
            result = subprocess.run(["adb"] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # if result.returncode != 0:
                # raise Exception(result.stderr)
            return result.stdout
        except Exception as e:
            # messagebox.showerror("ADB Error", str(e))
            print(str(e))
            return ""

    def list_files(self):
        self.file_list.delete(*self.file_list.get_children())
        output = self.run_adb(["shell", "ls", "-lh", self.current_path])
        if not output:
            return
        for line in output.strip().split("\n"):
            if line:
                parts = line.split()
                if len(parts) < 6:
                    continue
                perms = parts[0]
                name = parts[-1]
                ftype = "dir" if perms.startswith("d") else "file"
                self.file_list.insert("", "end", values=(name, ftype, perms))

    def on_item_double_click(self, event):
        selected = self.file_list.selection()
        if not selected:
            return
        name = self.file_list.item(selected[0])["values"][0]
        ftype = self.file_list.item(selected[0])["values"][1]
        if ftype == "dir":
            self.current_path = os.path.join(self.current_path, name)
            self.path_label.config(text=self.current_path)
            self.list_files()

    def go_up(self):
        if self.current_path == "/":
            return
        self.current_path = os.path.dirname(self.current_path)
        self.path_label.config(text=self.current_path)
        self.list_files()

    def create_widgets(self):
        frame = ttk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True)
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X)
        up_btn = ttk.Button(toolbar, text="Up", command=self.go_up)
        up_btn.pack(side=tk.LEFT)
        refresh_btn = ttk.Button(toolbar, text="Refresh", command=self.list_files)
        refresh_btn.pack(side=tk.LEFT)
        self.path_label = ttk.Label(toolbar, text=self.current_path)
        self.path_label.pack(side=tk.LEFT, padx=10)
        columns = ("Name", "Type", "Permissions")
        self.file_list = ttk.Treeview(frame, columns=columns, show="headings")
        for col in columns:
            self.file_list.heading(col, text=col)
        self.file_list.pack(fill=tk.BOTH, expand=True)
        self.file_list.bind("<Double-1>", self.on_item_double_click)

if __name__ == "__main__":
    root = tk.Tk()
    app = ADBFileManager(root)
    root.mainloop()
