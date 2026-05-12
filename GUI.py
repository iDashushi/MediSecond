import os
import tempfile
import logging
from datetime import datetime

import customtkinter as ctk
import pydicom
import numpy as np
from PIL import Image
from tkinter import filedialog, messagebox, simpledialog

from network import Net
from file_utils import encode, decode
from dicom_viewer import DicomViewer

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

PINK = "#ff99cc"
PINK_HOVER = "#ff66b2"
BG = "#1f1f1f"
CARD = "#2b2b2b"
CARD_LIGHT = "#333333"
CARD_HOVER = "#3f3f3f"
TEXT_MUTED = "#bdbdbd"

logger = logging.getLogger("medisecond.client.gui")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MediSecond")
        self.geometry("1150x740")
        self.minsize(1050, 660)
        self.configure(fg_color=BG)

        self.net = Net()
        self.user = None
        self.role = None
        self.current_groups = []
        self.selected_group_id = None
        self.selected_preview_files = []
        self.preview_images = []

        self.placeholder_text = "Write a comment to the patient..."

        self.login_screen()

    def pink_button(self, parent, text, command=None, width=140, height=40):
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            width=width,
            height=height,
            fg_color=PINK,
            hover_color=PINK_HOVER,
            text_color="white",
            corner_radius=12,
            font=("Arial", 13, "bold")
        )

    def soft_button(self, parent, text, command=None, width=140, height=40):
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            width=width,
            height=height,
            fg_color="#3a3a3a",
            hover_color="#4a4a4a",
            text_color="white",
            corner_radius=12,
            font=("Arial", 13)
        )

    def pink_radio(self, parent, text, variable, value):
        return ctk.CTkRadioButton(
            parent,
            text=text,
            variable=variable,
            value=value,
            fg_color=PINK,
            hover_color=PINK_HOVER,
            border_color="#aaaaaa",
            text_color="white",
            font=("Arial", 13)
        )

    def section_title(self, parent, title, subtitle=None):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            frame,
            text=title,
            font=("Arial", 20, "bold")
        ).pack(anchor="w")

        if subtitle:
            ctk.CTkLabel(
                frame,
                text=subtitle,
                font=("Arial", 12),
                text_color=TEXT_MUTED
            ).pack(anchor="w", pady=(2, 0))

    def add_empty_state(self, parent, text):
        ctk.CTkLabel(
            parent,
            text=text,
            font=("Arial", 15),
            text_color=TEXT_MUTED
        ).pack(padx=16, pady=30)

    def format_date(self, value):
        if not value:
            return ""

        try:
            return datetime.strptime(
                str(value),
                "%Y-%m-%d %H:%M:%S"
            ).strftime("%d/%m/%Y %H:%M")
        except Exception:
            return str(value)

    def add_card_hover(self, card, normal_color=CARD_LIGHT, hover_color=CARD_HOVER):
        card.bind("<Enter>", lambda event: card.configure(fg_color=hover_color))
        card.bind("<Leave>", lambda event: card.configure(fg_color=normal_color))

    def clear(self):
        for widget in self.winfo_children():
            widget.destroy()

    def show_error(self, title, msg):
        logger.error("%s: %s", title, msg)
        messagebox.showerror(title, msg)

    def logout(self):
        if not messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            return

        logger.info("User logged out: %s", self.user)

        self.user = None
        self.role = None
        self.current_groups = []
        self.selected_group_id = None
        self.selected_preview_files = []
        self.preview_images = []

        self.login_screen()

    def login_screen(self):
        self.clear()

        outer = ctk.CTkFrame(
            self,
            corner_radius=22,
            width=720,
            height=470,
            fg_color=CARD
        )
        outer.pack(expand=True, padx=90, pady=80)
        outer.pack_propagate(False)

        ctk.CTkLabel(
            outer,
            text="MediSecond",
            font=("Arial", 34, "bold")
        ).pack(pady=(34, 6))

        ctk.CTkLabel(
            outer,
            text="Secure medical file sharing for second opinions",
            font=("Arial", 13),
            text_color=TEXT_MUTED
        ).pack(pady=(0, 22))

        self.username_entry = ctk.CTkEntry(
            outer,
            placeholder_text="Username",
            width=360,
            height=44,
            corner_radius=10
        )
        self.username_entry.pack(pady=9)

        self.password_entry = ctk.CTkEntry(
            outer,
            placeholder_text="Password",
            show="*",
            width=360,
            height=44,
            corner_radius=10
        )
        self.password_entry.pack(pady=9)

        self.role_var = ctk.StringVar(value="patient")

        role_frame = ctk.CTkFrame(outer, fg_color="transparent")
        role_frame.pack(pady=15)

        self.pink_radio(role_frame, "Patient", self.role_var, "patient").pack(side="left", padx=24)
        self.pink_radio(role_frame, "Doctor", self.role_var, "doctor").pack(side="left", padx=24)

        btn_frame = ctk.CTkFrame(outer, fg_color="transparent")
        btn_frame.pack(pady=(20, 30))

        self.pink_button(btn_frame, "Login", self.login, width=155).pack(side="left", padx=10)
        self.soft_button(btn_frame, "Register", self.register, width=155).pack(side="left", padx=10)
        self.soft_button(btn_frame, "Exit", self.destroy, width=155).pack(side="left", padx=10)

    def register(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        role = self.role_var.get()

        if not username or not password:
            messagebox.showerror("Error", "Enter username and password")
            return

        try:
            res = self.net.send({
                "action": "register",
                "user": username,
                "pass": password,
                "role": role
            })
        except Exception as e:
            self.show_error("Connection Error", f"Could not reach server:\n{e}")
            return

        if res.get("ok"):
            logger.info("Registration successful for %s", username)
            messagebox.showinfo("Success", "Registered successfully")
        else:
            messagebox.showerror("Error", res.get("error", "Registration failed"))

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            messagebox.showerror("Error", "Enter username and password")
            return

        try:
            res = self.net.send({
                "action": "login",
                "user": username,
                "pass": password
            })
        except Exception as e:
            self.show_error("Connection Error", f"Could not reach server:\n{e}")
            return

        if not res.get("ok"):
            messagebox.showerror("Error", res.get("error", "Login failed"))
            return

        self.user = username
        self.role = res.get("role")

        logger.info("Logged in as %s (%s)", self.user, self.role)

        if self.role == "doctor":
            self.doctor_home()
        else:
            self.patient_home()

    def patient_home(self):
        self.clear()

        top = ctk.CTkFrame(self, height=78, fg_color=CARD, corner_radius=16)
        top.pack(fill="x", padx=16, pady=16)

        ctk.CTkLabel(
            top,
            text="Patient Dashboard",
            font=("Arial", 25, "bold")
        ).pack(side="left", padx=18, pady=16)

        ctk.CTkLabel(
            top,
            text=f"Logged in as {self.user}",
            font=("Arial", 13),
            text_color=TEXT_MUTED
        ).pack(side="left", padx=10)

        self.pink_button(top, "Logout", self.logout, width=105).pack(side="right", padx=16, pady=16)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        left = ctk.CTkFrame(content, fg_color=CARD, corner_radius=18)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=6)

        right = ctk.CTkFrame(content, fg_color=CARD, corner_radius=18)
        right.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=6)

        self.section_title(left, "Upload History", "Medical cases you already sent")
        self.patient_files_frame = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.patient_files_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.section_title(right, "Doctor Comments", "Responses received from doctors")
        self.patient_comments_frame = ctk.CTkScrollableFrame(right, fg_color="transparent")
        self.patient_comments_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        bottom = ctk.CTkFrame(self, fg_color=CARD, corner_radius=16)
        bottom.pack(fill="x", padx=16, pady=(0, 16))

        self.pink_button(
            bottom,
            "Upload New Files",
            self.open_preview_window,
            width=170
        ).pack(side="left", padx=14, pady=12)

        self.soft_button(
            bottom,
            "Refresh",
            self.refresh_patient,
            width=120
        ).pack(side="right", padx=14, pady=12)

        self.refresh_patient()

    def patient_group_card(self, parent, group_id, doctor, created_at, file_count):
        card = ctk.CTkFrame(parent, fg_color=CARD_LIGHT, corner_radius=14)
        card.pack(fill="x", padx=4, pady=7)
        self.add_card_hover(card)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(12, 4))

        ctk.CTkLabel(row, text=f"Case #{group_id}", font=("Arial", 17, "bold")).pack(side="left")

        ctk.CTkLabel(
            row,
            text=f"{file_count} files",
            font=("Arial", 12, "bold"),
            text_color=PINK
        ).pack(side="right")

        ctk.CTkLabel(
            card,
            text=f"Sent to Dr. {doctor}",
            font=("Arial", 13),
            text_color="#eeeeee"
        ).pack(anchor="w", padx=14, pady=(0, 2))

        ctk.CTkLabel(
            card,
            text=f"Date: {self.format_date(created_at)}",
            font=("Arial", 12),
            text_color=TEXT_MUTED
        ).pack(anchor="w", padx=14, pady=(0, 12))

    def patient_comment_card(self, parent, group_id, created_at, doctor, comment):
        card = ctk.CTkFrame(parent, fg_color=CARD_LIGHT, corner_radius=14)
        card.pack(fill="x", padx=4, pady=7)
        self.add_card_hover(card)

        ctk.CTkLabel(
            card,
            text=f"Dr. {doctor} replied to Case #{group_id}",
            font=("Arial", 15, "bold")
        ).pack(anchor="w", padx=14, pady=(12, 4))

        ctk.CTkLabel(
            card,
            text=comment,
            font=("Arial", 13),
            wraplength=430,
            justify="left",
            text_color="#eeeeee"
        ).pack(anchor="w", padx=14, pady=(0, 6))

        ctk.CTkLabel(
            card,
            text=f"Date: {self.format_date(created_at)}",
            font=("Arial", 12),
            text_color=TEXT_MUTED
        ).pack(anchor="w", padx=14, pady=(0, 12))

    def refresh_patient(self):
        for widget in self.patient_files_frame.winfo_children():
            widget.destroy()

        for widget in self.patient_comments_frame.winfo_children():
            widget.destroy()

        try:
            res_groups = self.net.send({
                "action": "patient_groups",
                "owner": self.user
            })
        except Exception as e:
            self.show_error("Connection Error", f"Could not reach server:\n{e}")
            return

        groups = res_groups.get("groups", [])

        if not groups:
            self.add_empty_state(
                self.patient_files_frame,
                "No uploads yet. Click “Upload New Files” to send your first case."
            )
        else:
            for group_id, owner, doctor, created_at, file_count in groups:
                self.patient_group_card(
                    self.patient_files_frame,
                    group_id,
                    doctor,
                    created_at,
                    file_count
                )

        try:
            res_comments = self.net.send({
                "action": "patient_comments",
                "owner": self.user
            })
        except Exception as e:
            self.show_error("Connection Error", f"Could not reach server:\n{e}")
            return

        comments = res_comments.get("comments", [])

        if not comments:
            self.add_empty_state(self.patient_comments_frame, "No doctor comments yet.")
        else:
            for group_id, created_at, doctor, comment in comments:
                self.patient_comment_card(
                    self.patient_comments_frame,
                    group_id,
                    created_at,
                    doctor,
                    comment
                )

    def open_preview_window(self):
        paths = filedialog.askopenfilenames(
            title="Choose medical files",
            filetypes=[
                ("Medical / Image files", "*.DCM *.dcm *.png *.jpg *.jpeg"),
                ("All files", "*.*")
            ]
        )

        if not paths:
            return

        self.selected_preview_files = list(paths)

        preview = ctk.CTkToplevel(self)
        preview.title("Preview Before Sending")
        preview.geometry("1000x700")
        preview.minsize(920, 640)
        preview.configure(fg_color=BG)
        preview.transient(self)
        preview.grab_set()
        preview.lift()
        preview.focus_force()
        preview.attributes("-topmost", True)
        preview.after(300, lambda: preview.attributes("-topmost", False))

        top = ctk.CTkFrame(preview, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(16, 8))

        ctk.CTkLabel(
            top,
            text="Preview Before Sending",
            font=("Arial", 25, "bold")
        ).pack(side="left")

        bottom = ctk.CTkFrame(preview, height=92, fg_color=CARD, corner_radius=14)
        bottom.pack(side="bottom", fill="x", padx=18, pady=(12, 16))
        bottom.pack_propagate(False)

        buttons_frame = ctk.CTkFrame(bottom, fg_color="transparent")
        buttons_frame.pack(side="right", padx=16, pady=20)

        content = ctk.CTkFrame(preview, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=18, pady=(0, 0))

        left = ctk.CTkFrame(content, width=300, fg_color=CARD, corner_radius=16)
        left.pack(side="left", fill="y", padx=(0, 10), pady=8)
        left.pack_propagate(False)

        right = ctk.CTkFrame(content, fg_color=CARD, corner_radius=16)
        right.pack(side="left", fill="both", expand=True, pady=8)

        ctk.CTkLabel(
            left,
            text="Selected Files",
            font=("Arial", 18, "bold")
        ).pack(anchor="w", padx=14, pady=(14, 8))

        files_frame = ctk.CTkScrollableFrame(left, fg_color="transparent")
        files_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        preview_files = []

        for p in self.selected_preview_files:
            name = os.path.basename(p)

            item = ctk.CTkFrame(files_frame, fg_color=CARD_LIGHT, corner_radius=10)
            item.pack(fill="x", pady=5)

            ctk.CTkLabel(
                item,
                text=name,
                font=("Arial", 12),
                wraplength=230,
                justify="left"
            ).pack(anchor="w", padx=10, pady=8)

            if p.lower().endswith((".dcm", ".png", ".jpg", ".jpeg")):
                preview_files.append(p)

        ctk.CTkLabel(
            right,
            text="Image Preview",
            font=("Arial", 18, "bold")
        ).pack(pady=(14, 8))

        image_label = ctk.CTkLabel(right, text="No valid images selected")
        image_label.pack(pady=10, expand=True)

        info_label = ctk.CTkLabel(right, text="", text_color=TEXT_MUTED)
        info_label.pack(pady=(0, 8))

        preview_images = []
        preview_names = []
        current_index = {"value": 0}

        for p in preview_files:
            try:
                if p.lower().endswith(".dcm"):
                    ds = pydicom.dcmread(p)
                    arr = ds.pixel_array.astype(np.float32)
                    arr -= arr.min()

                    if arr.max() > 0:
                        arr = arr / arr.max()

                    arr = (arr * 255).astype(np.uint8)

                    if arr.ndim == 2:
                        img = Image.fromarray(arr).convert("L")
                    else:
                        img = Image.fromarray(arr)
                else:
                    img = Image.open(p).convert("RGB")

                img.thumbnail((570, 410))

                ctk_img = ctk.CTkImage(
                    light_image=img,
                    dark_image=img,
                    size=img.size
                )

                preview_images.append(ctk_img)
                preview_names.append(os.path.basename(p))

            except Exception as e:
                logger.warning("Preview failed for %s: %s", p, e)

        self.preview_images = preview_images

        def show_current_image():
            if not preview_images:
                image_label.configure(image=None, text="No valid images selected")
                info_label.configure(text="")
                return

            idx = current_index["value"]

            image_label.configure(image=preview_images[idx], text="")
            image_label.image = preview_images[idx]

            info_label.configure(
                text=f"{preview_names[idx]}   |   {idx + 1}/{len(preview_images)}"
            )

        def prev_image():
            if preview_images:
                current_index["value"] = (current_index["value"] - 1) % len(preview_images)
                show_current_image()

        def next_image():
            if preview_images:
                current_index["value"] = (current_index["value"] + 1) % len(preview_images)
                show_current_image()

        def mouse_scroll(event):
            if not preview_images:
                return

            if event.delta > 0:
                prev_image()
            else:
                next_image()

        def key_press(event):
            if event.keysym in ("Right", "Down"):
                next_image()
            elif event.keysym in ("Left", "Up"):
                prev_image()

        preview.bind("<MouseWheel>", mouse_scroll)
        preview.bind("<Left>", key_press)
        preview.bind("<Right>", key_press)
        preview.bind("<Up>", key_press)
        preview.bind("<Down>", key_press)
        preview.focus_set()

        nav_frame = ctk.CTkFrame(right, fg_color="transparent")
        nav_frame.pack(pady=(10, 25))

        self.soft_button(nav_frame, "Previous", prev_image, width=140, height=42).pack(side="left", padx=8)
        self.soft_button(nav_frame, "Next", next_image, width=140, height=42).pack(side="left", padx=8)

        show_current_image()

        def send_after_preview():
            try:
                doctors_res = self.net.send({"action": "list_doctors"})
                doctors = doctors_res.get("doctors", [])
            except Exception as e:
                messagebox.showerror(
                    "Connection Error",
                    f"Could not reach server:\n{e}",
                    parent=preview
                )
                return

            msg = "Enter doctor username:"

            if doctors:
                msg += "\nAvailable doctors: " + ", ".join(doctors)

            doctor_name = simpledialog.askstring(
                "Doctor Username",
                msg,
                parent=preview
            )

            if not doctor_name:
                return

            doctor_name = doctor_name.strip()

            payload_files = [
                {
                    "filename": os.path.basename(p),
                    "data": encode(p)
                }
                for p in self.selected_preview_files
            ]

            try:
                preview.configure(cursor="watch")
                preview.update()

                res = self.net.send({
                    "action": "upload_group",
                    "owner": self.user,
                    "doctor": doctor_name,
                    "files": payload_files
                })

            except Exception as e:
                preview.configure(cursor="")
                messagebox.showerror("Upload Error", str(e), parent=preview)
                return

            preview.configure(cursor="")

            if res.get("ok"):
                group_id = res.get("group_id")

                logger.info(
                    "Patient %s sent group %s to %s",
                    self.user,
                    group_id,
                    doctor_name
                )

                preview.destroy()

                messagebox.showinfo(
                    "Success",
                    f"Case #{group_id} was sent successfully"
                )

                self.refresh_patient()

            else:
                messagebox.showerror(
                    "Error",
                    res.get("error", "Group send failed"),
                    parent=preview
                )

        self.soft_button(buttons_frame,"Cancel",preview.destroy,width=150,height=46).pack(side="left", padx=8)
        self.pink_button(buttons_frame,"Send to Doctor",send_after_preview,width=180,height=46).pack(side="left", padx=8)

    def doctor_home(self):
        self.clear()

        top = ctk.CTkFrame(self, height=78, fg_color=CARD, corner_radius=16)
        top.pack(fill="x", padx=16, pady=16)

        ctk.CTkLabel(top,text="Doctor Dashboard",font=("Arial", 25, "bold")).pack(side="left", padx=18, pady=16)
        ctk.CTkLabel(top,text=f"Logged in as Dr. {self.user}",font=("Arial", 13),text_color=TEXT_MUTED).pack(side="left", padx=10)

        self.pink_button(top, "Logout", self.logout, width=105).pack(side="right", padx=16, pady=16)

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        left = ctk.CTkFrame(main, fg_color=CARD, corner_radius=18)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=6)

        right = ctk.CTkFrame(main, width=345, fg_color=CARD, corner_radius=18)
        right.pack(side="left", fill="y", padx=(8, 0), pady=6)
        right.pack_propagate(False)

        self.section_title(left, "Received Cases", "Files sent to you by patients")

        self.doctor_cases_frame = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.doctor_cases_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.section_title(right, "Case Details", "Open files or send a response")
        self.selected_info = ctk.CTkLabel(right,text="No case selected",wraplength=285,justify="left",font=("Arial", 13),text_color=TEXT_MUTED)
        self.selected_info.pack(anchor="w", padx=16, pady=(0, 14))

        self.comment_entry = ctk.CTkTextbox(right,width=300,height=130,corner_radius=12,font=("Arial", 13))
        self.comment_entry.pack(padx=16, pady=(0, 12))

        self.comment_entry.insert("1.0", self.placeholder_text)
        self.comment_entry.configure(text_color="#888888")

        def clear_placeholder(event=None):
            current = self.comment_entry.get("1.0", "end").strip()

            if current == self.placeholder_text:
                self.comment_entry.delete("1.0", "end")
                self.comment_entry.configure(text_color="white")

        self.comment_entry.bind("<FocusIn>", clear_placeholder)

        self.pink_button(
            right,
            "Open Case Files",
            self.open_selected_file,
            width=210
        ).pack(padx=16, pady=7)

        self.soft_button(
            right,
            "Send Comment",
            self.send_comment,
            width=210
        ).pack(padx=16, pady=7)

        self.soft_button(right,"Refresh",self.refresh_doctor,width=210).pack(padx=16, pady=7)

        self.refresh_doctor()

    def doctor_case_card(self, parent, row):
        group_id, owner, doctor, created_at, file_count = row

        selected = self.selected_group_id == group_id
        fg = "#454045" if selected else CARD_LIGHT

        card = ctk.CTkFrame(parent, fg_color=fg, corner_radius=14)
        card.pack(fill="x", padx=4, pady=7)

        if not selected:
            self.add_card_hover(card)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 4))

        ctk.CTkLabel(header, text=f"Case #{group_id}", font=("Arial", 17, "bold")).pack(side="left")

        ctk.CTkLabel(
            header,
            text=f"{file_count} files",
            font=("Arial", 12, "bold"),
            text_color=PINK
        ).pack(side="right")

        ctk.CTkLabel(
            card,
            text=f"Patient: {owner}",
            font=("Arial", 13),
            text_color="#eeeeee"
        ).pack(anchor="w", padx=14)

        ctk.CTkLabel(
            card,
            text=f"Received: {self.format_date(created_at)}",
            font=("Arial", 12),
            text_color=TEXT_MUTED
        ).pack(anchor="w", padx=14, pady=(2, 10))

        self.soft_button(
            card,
            "Select Case",
            lambda gid=group_id: self.select_group_by_id(gid),
            width=120,
            height=32
        ).pack(anchor="e", padx=14, pady=(0, 12))

    def refresh_doctor(self):
        for widget in self.doctor_cases_frame.winfo_children():
            widget.destroy()

        self.current_groups = []
        self.selected_group_id = None
        self.selected_info.configure(text="No case selected")

        try:
            res = self.net.send({
                "action": "doctor_groups",
                "doctor": self.user
            })
        except Exception as e:
            self.show_error("Connection Error", f"Could not reach server:\n{e}")
            return

        self.current_groups = res.get("groups", [])

        if not self.current_groups:
            self.add_empty_state(self.doctor_cases_frame, "No cases were sent to you yet.")
            return

        for row in self.current_groups:
            self.doctor_case_card(self.doctor_cases_frame, row)

    def select_group_by_id(self, group_id):
        self.selected_group_id = group_id

        selected_row = next(
            (row for row in self.current_groups if row[0] == group_id),
            None
        )

        if selected_row:
            group_id, owner, doctor, created_at, file_count = selected_row

            self.selected_info.configure(
                text=f"Selected Case #{group_id}\n"
                     f"Patient: {owner}\n"
                     f"Files: {file_count}\n"
                     f"Received: {self.format_date(created_at)}"
            )

        for widget in self.doctor_cases_frame.winfo_children():
            widget.destroy()

        for row in self.current_groups:
            self.doctor_case_card(self.doctor_cases_frame, row)

    def open_selected_file(self):
        if not self.selected_group_id:
            messagebox.showerror("Error", "Select a case first")
            return

        try:
            res = self.net.send({
                "action": "group_files",
                "group_id": self.selected_group_id
            })
        except Exception as e:
            self.show_error("Connection Error", f"Could not reach server:\n{e}")
            return

        group_files = res.get("files", [])

        if not group_files:
            messagebox.showerror("Error", "No files in this case")
            return

        temp_paths = []

        for file_id, filename, owner, doctor, filepath in group_files:
            try:
                file_res = self.net.send({
                    "action": "download",
                    "file_id": file_id
                })

                if not file_res.get("ok"):
                    continue

                file_info = file_res["file"]
                safe_name = os.path.basename(filename)

                temp_path = os.path.join(
                    tempfile.gettempdir(),
                    f"case_{self.selected_group_id}_{safe_name}"
                )

                decode(file_info["data"], temp_path)
                temp_paths.append(temp_path)

            except Exception as e:
                logger.warning("Could not download file %s: %s", filename, e)

        if not temp_paths:
            messagebox.showerror("Error", "Could not open files")
            return

        logger.info("Doctor %s opened case %s", self.user, self.selected_group_id)
        DicomViewer(temp_paths, parent=self)

    def send_comment(self):
        if not self.selected_group_id:
            messagebox.showerror("Error", "Select a case first")
            return

        text = self.comment_entry.get("1.0", "end").strip()

        if not text or text == self.placeholder_text:
            messagebox.showerror("Error", "Enter a comment")
            return

        try:
            res = self.net.send({
                "action": "comment_group",
                "group_id": self.selected_group_id,
                "doctor": self.user,
                "comment": text
            })
        except Exception as e:
            self.show_error("Connection Error", f"Could not reach server:\n{e}")
            return

        if res.get("ok"):
            logger.info("Doctor %s commented on case %s", self.user, self.selected_group_id)

            self.comment_entry.delete("1.0", "end")
            self.comment_entry.insert("1.0", self.placeholder_text)
            self.comment_entry.configure(text_color="#888888")

            messagebox.showinfo("Success", "Comment sent to patient")
        else:
            messagebox.showerror("Error", res.get("error", "Comment failed"))