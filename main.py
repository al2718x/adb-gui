#!/usr/bin/env python3

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
        self.error_var = tk.StringVar()
        self.run_as_var = tk.StringVar()
        self.create_widgets()
        self.list_files()

    def run_adb(self, args):
        self.error_var.set("")
        try:
            result = subprocess.run(["adb"] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                self.error_var.set(result.stderr.strip())
                print(result.stderr.strip())
            return result.stdout
        except Exception as e:
            self.error_var.set(str(e))
            print(str(e))

    def list_files(self):
        self.file_list.delete(*self.file_list.get_children())
        # Use persistent run-as if present
        run_as_val = self.run_as_var.get().strip()
        if run_as_val and self.current_path.startswith("/data/data/"):
            output = self.run_adb(["shell", "run-as", run_as_val, "ls", "-lh", self.current_path])
        else:
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
        name = str(self.file_list.item(selected[0])["values"][0])
        ftype = str(self.file_list.item(selected[0])["values"][1])
        if ftype == "dir":
            # If clicking on /data from root, use persistent run-as value
            if self.current_path == "/" and name == "data":
                run_as = self.run_as_var.get().strip()
                if run_as:
                    self.current_path = f"/data/data/{run_as}"
                    self.path_label.config(text=self.current_path)
                    self.list_files()
                    return
            self.current_path = os.path.join(self.current_path, name)
            self.path_label.config(text=self.current_path)
            self.list_files()
        else:
            # It's a file – prompt user to choose save location and download via adb pull
            remote_path = os.path.join(self.current_path, name)
            local_path = filedialog.asksaveasfilename(initialfile=name, title="Save As")
            if not local_path:
                return  # user cancelled
            self.download_file(remote_path, local_path)

    def go_up(self):
        if self.current_path == "/":
            return
        self.current_path = os.path.dirname(self.current_path)
        self.path_label.config(text=self.current_path)
        self.list_files()

    def download_file(self, remote_path, local_path):
        """Download a single file from the device to the given local path."""
        self.error_var.set("")
        try:
            # Using adb pull is the most straightforward way. If run-as is required we'll try that first
            run_as_val = self.run_as_var.get().strip()
            pull_cmd = ["adb"]
            # When using run-as, we need to execute cat via shell because adb pull does not work with run-as
            if run_as_val and remote_path.startswith(f"/data/data/{run_as_val}"):
                # Use exec-out to stream file contents
                with open(local_path, "wb") as f:
                    cat_result = subprocess.run(
                        [
                            "adb",
                            "exec-out",
                            "run-as",
                            run_as_val,
                            "cat",
                            remote_path,
                        ],
                        stdout=f,
                        stderr=subprocess.PIPE,
                    )
                    if cat_result.returncode != 0:
                        self.error_var.set(cat_result.stderr.decode().strip())
                        messagebox.showerror("Download Error", self.error_var.get())
                        return
            else:
                pull_result = subprocess.run(
                    pull_cmd + ["pull", remote_path, local_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if pull_result.returncode != 0:
                    self.error_var.set(pull_result.stderr.strip())
                    messagebox.showerror("Download Error", self.error_var.get())
                    return
            # messagebox.showinfo("Download Complete", f"Saved to {local_path}")
        except Exception as e:
            self.error_var.set(str(e))
            messagebox.showerror("Download Error", str(e))

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
        # Run-as field under the top buttons
        runas_frame = ttk.Frame(self.root)
        runas_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        runas_label = ttk.Label(runas_frame, text="run-as package:")
        runas_label.pack(side=tk.LEFT)
        runas_entry = ttk.Entry(runas_frame, textvariable=self.run_as_var, width=25)
        runas_entry.pack(side=tk.LEFT, padx=(5, 0))
        columns = ("Name", "Type", "Permissions")
        self.file_list = ttk.Treeview(frame, columns=columns, show="headings")
        for col in columns:
            self.file_list.heading(col, text=col)
        self.file_list.pack(fill=tk.BOTH, expand=True)
        self.file_list.bind("<Double-1>", self.on_item_double_click)
        # Error label at the bottom with fixed height
        error_frame = ttk.Frame(self.root, height=28)
        error_frame.pack_propagate(False)
        error_frame.pack(side=tk.BOTTOM, fill=tk.X)
        error_label = ttk.Label(error_frame, textvariable=self.error_var, foreground="red", anchor="w")
        error_label.pack(fill=tk.BOTH, padx=5, pady=2, expand=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = ADBFileManager(root)
    root.mainloop()
