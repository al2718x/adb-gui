#!/usr/bin/env python3

import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkfont
import os

class ADBFileManager:
    def __init__(self, root):
        self.root = root
        self.root.title("ADB File Manager")
        self.root.geometry("900x600")
        self.current_path = "/"
        self.error_var = tk.StringVar()
        self.run_as_var = tk.StringVar()
        self.device_id = None  # selected ADB device serial number
        self.devices = []  # list of connected device serials
        self.detect_devices()
        self.create_widgets()
        self.list_files()

    def adb_base(self):
        """Return base adb command with selected device option."""
        base = ["adb"]
        if self.device_id:
            base += ["-s", self.device_id]
        return base

    def run_adb(self, args):
        """Run an adb command with the currently selected device (if any)."""
        self.error_var.set("")
        try:
            cmd = ["adb"]
            if self.device_id:
                cmd += ["-s", self.device_id]
            cmd += args
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                self.error_var.set(result.stderr.strip())
                print(result.stderr.strip())
            return result.stdout
        except Exception as e:
            self.error_var.set(str(e))
            print(str(e))

    def detect_devices(self):
        """Populate self.devices and default device selection."""
        try:
            res = subprocess.run(["adb", "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode != 0:
                messagebox.showerror("ADB Error", res.stderr.strip())
                self.root.destroy()
                return
            lines = [l.strip() for l in res.stdout.splitlines()[1:] if l.strip()]
            self.devices = [l.split()[0] for l in lines if "device" in l]
            if not self.devices:
                messagebox.showerror("No Devices", "No connected Android devices detected.")
                self.root.destroy()
                return
            self.device_id = self.devices[0]
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.root.destroy()

    def refresh_devices(self):
        """Refresh list of connected devices and update combobox."""
        prev = self.device_id
        self.detect_devices()
        # update combobox values and selection
        if hasattr(self, "device_combo"):
            self.device_combo["values"] = self.devices
            if prev in self.devices:
                self.device_var.set(prev)
                self.device_id = prev
            else:
                self.device_var.set(self.device_id)
        self.list_files()

    def on_device_change(self, event=None):
        sel = self.device_var.get()
        if sel and sel != self.device_id:
            self.device_id = sel
            self.list_files()

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
            pull_cmd = self.adb_base()
            # When using run-as, we need to execute cat via shell because adb pull does not work with run-as
            if run_as_val and remote_path.startswith(f"/data/data/{run_as_val}"):
                # Use exec-out to stream file contents
                with open(local_path, "wb") as f:
                    cat_result = subprocess.run(
                        self.adb_base() + [
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

    def load_file(self):
        """Prompt user to select a local file and upload it to the current path on the device."""
        local_path = filedialog.askopenfilename(title="Select file to load")
        if not local_path:
            return
        remote_path = os.path.join(self.current_path, os.path.basename(local_path))
        self.upload_file(local_path, remote_path)

    def delete_selected(self):
        """Delete the selected file or directory on the device after confirmation."""
        selected = self.file_list.selection()
        if not selected:
            messagebox.showinfo("Delete", "No item selected")
            return
        name, ftype, _ = self.file_list.item(selected[0])["values"]
        remote_path = os.path.join(self.current_path, name)
        if not messagebox.askyesno("Confirm Delete", f"Delete '{remote_path}' on device?"):
            return
        self.error_var.set("")
        run_as_val = self.run_as_var.get().strip()
        try:
            if run_as_val and remote_path.startswith(f"/data/data/{run_as_val}"):
                cmd = self.adb_base() + [
                    "shell",
                    "run-as",
                    run_as_val,
                    "rm",
                    "-rf",
                    remote_path,
                ]
            else:
                cmd = self.adb_base() + ["shell", "rm", "-rf", remote_path]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode != 0:
                self.error_var.set(res.stderr.strip())
                messagebox.showerror("Delete Error", self.error_var.get())
                return
            # refresh view
            self.list_files()
        except Exception as e:
            self.error_var.set(str(e))
            messagebox.showerror("Delete Error", str(e))

    def upload_file(self, local_path, remote_path):
        """Upload a file from local_path to remote_path on device, handling run-as if needed."""
        self.error_var.set("")
        try:
            run_as_val = self.run_as_var.get().strip()
            if run_as_val and remote_path.startswith(f"/data/data/{run_as_val}"):
                # Use run-as with shell redirection to write the file
                with open(local_path, "rb") as f:
                    push_proc = subprocess.run(
                        self.adb_base() + [
                            "shell",
                            "run-as",
                            run_as_val,
                            "sh",
                            "-c",
                            f'cat > "{remote_path}"',
                        ],
                        stdin=f,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    if push_proc.returncode != 0:
                        self.error_var.set(push_proc.stderr.decode().strip())
                        messagebox.showerror("Upload Error", self.error_var.get())
                        return
            else:
                push_proc = subprocess.run(
                    self.adb_base() + ["push", local_path, remote_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if push_proc.returncode != 0:
                    self.error_var.set(push_proc.stderr.strip())
                    messagebox.showerror("Upload Error", self.error_var.get())
                    return
            # Optionally refresh view
            self.list_files()
        except Exception as e:
            self.error_var.set(str(e))
            messagebox.showerror("Upload Error", str(e))

    def create_widgets(self):
        frame = ttk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True)
        # Device selector frame (top)
        device_frame = ttk.Frame(frame)
        device_frame.pack(fill=tk.X, padx=5, pady=(2, 0))
        # ttk.Label(device_frame, text="Device:").pack(side=tk.LEFT)
        self.device_var = tk.StringVar(value=self.device_id)
        self.device_combo = ttk.Combobox(device_frame, textvariable=self.device_var, values=self.devices, state="readonly", width=30)
        self.device_combo.pack(side=tk.LEFT)
        refresh_dev_btn = ttk.Button(device_frame, text="⟳", width=3, command=self.refresh_devices, padding=(0, 0))
        refresh_dev_btn.pack(side=tk.LEFT, padx=5)
        self.device_combo.bind("<<ComboboxSelected>>", self.on_device_change)

        ttk.Separator(frame, orient="horizontal").pack(fill=tk.X, pady=(0,2))
        # Toolbar with file commands
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X)
        up_btn = ttk.Button(toolbar, text="Up", command=self.go_up, padding=(0, 0))
        up_btn.pack(side=tk.LEFT)
        refresh_btn = ttk.Button(toolbar, text="Refresh", command=self.list_files, padding=(0, 0))
        refresh_btn.pack(side=tk.LEFT)
        load_btn = ttk.Button(toolbar, text="Load", command=self.load_file, padding=(0, 0))
        load_btn.pack(side=tk.LEFT)
        delete_btn = ttk.Button(toolbar, text="Delete", command=self.delete_selected, padding=(0, 0))
        delete_btn.pack(side=tk.LEFT)
        self.path_label = ttk.Label(toolbar, text=self.current_path)
        self.path_label.pack(side=tk.LEFT, padx=10)

        # define monospace font
        mono = tkfont.nametofont("TkFixedFont")
        mono.configure(size=10)

        # Treeview for files
        columns = ("Name", "Type", "Permissions")
        self.file_list = ttk.Treeview(frame, columns=columns, show="headings", style="Mono.Treeview")
        style = ttk.Style()
        style.configure("Mono.Treeview", font=mono)
        style.configure("Mono.Treeview.Heading", font=mono)
        for col in columns:
            self.file_list.heading(col, text=col)
        # fixed width for 'Type' column
        self.file_list.column("Type", width=80, stretch=False)
        self.file_list.column("Permissions", width=120, stretch=False)
        self.file_list.pack(fill=tk.BOTH, expand=True)
        self.file_list.bind("<Double-1>", self.on_item_double_click)

        # Run-as field (under file list)
        runas_frame = ttk.Frame(self.root)
        runas_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        runas_label = ttk.Label(runas_frame, text="run-as package:")
        runas_label.pack(side=tk.LEFT)
        runas_entry = ttk.Entry(runas_frame, textvariable=self.run_as_var, width=25)
        runas_entry.pack(side=tk.LEFT, padx=(5, 0))

        # Error label at bottom
        error_frame = ttk.Frame(self.root, height=28)
        error_frame.pack_propagate(False)
        error_frame.pack(side=tk.BOTTOM, fill=tk.X)
        error_label = ttk.Label(error_frame, textvariable=self.error_var, foreground="red", anchor="w")
        error_label.pack(fill=tk.BOTH, padx=5, pady=2, expand=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = ADBFileManager(root)
    root.mainloop()
