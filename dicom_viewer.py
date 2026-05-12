import os
import customtkinter as ctk
import pydicom
import numpy as np
from PIL import Image

PINK = "#ff99cc"
PINK_HOVER = "#ff66b2"
CARD_BG = "#2b2b2b"

class DicomViewer(ctk.CTkToplevel):
    def __init__(self, paths, parent=None):
        super().__init__(parent)

        self.title("Medical File Preview")
        self.geometry("860x720")
        self.minsize(760, 620)
        self.configure(fg_color="#1f1f1f")

        self.parent = parent
        self.paths = list(paths)
        self.frames = []
        self.names = []
        self.index = 0

        if parent is not None:
            self.transient(parent)

        self.grab_set()
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(300, lambda: self.attributes("-topmost", False))

        self.load_files()
        self.build_ui()

        if self.frames:
            self.show_image()
        else:
            self.info_label.configure(text="No valid medical images to display")

    def load_files(self):
        for p in self.paths:
            try:
                if p.lower().endswith(".dcm"):
                    ds = pydicom.dcmread(p)
                    arr = ds.pixel_array.astype(np.float32)
                    arr -= arr.min()
                    if arr.max() > 0:
                        arr = arr / arr.max()
                    arr = (arr * 255).astype(np.uint8)
                    img = Image.fromarray(arr).convert("L") if arr.ndim == 2 else Image.fromarray(arr)
                else:
                    img = Image.open(p).convert("RGB")

                self.frames.append(img)
                self.names.append(os.path.basename(p))
            except Exception as e:
                print("FILE PREVIEW ERROR:", os.path.basename(p), e)

    def build_ui(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(18, 10))

        ctk.CTkLabel(top, text="Medical File Preview", font=("Arial", 26, "bold")).pack(side="left")

        ctk.CTkButton(
            top, text="Close", command=self.destroy, width=100,
            fg_color=PINK, hover_color=PINK_HOVER
        ).pack(side="right")

        card = ctk.CTkFrame(self, corner_radius=18, fg_color=CARD_BG)
        card.pack(fill="both", expand=True, padx=20, pady=10)

        self.image_label = ctk.CTkLabel(card, text="")
        self.image_label.pack(pady=20, expand=True)

        self.info_label = ctk.CTkLabel(card, text="", font=("Arial", 15), text_color="#dcdcdc")
        self.info_label.pack(pady=(0, 12))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 20))

        ctk.CTkButton(
            btn_frame, text="Previous", command=self.prev_image, width=130,
            fg_color=PINK, hover_color=PINK_HOVER
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame, text="Next", command=self.next_image, width=130,
            fg_color=PINK, hover_color=PINK_HOVER
        ).pack(side="left", padx=10)

    def show_image(self):
        if not self.frames:
            return
        img = self.frames[self.index].copy()
        img.thumbnail((760, 520))
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        self.image_label.configure(image=ctk_img, text="")
        self.image_label.image = ctk_img
        self.info_label.configure(text=f"{self.names[self.index]}   |   {self.index + 1}/{len(self.frames)}")

    def prev_image(self):
        if not self.frames:
            return
        self.index = (self.index - 1) % len(self.frames)
        self.show_image()

    def next_image(self):
        if not self.frames:
            return
        self.index = (self.index + 1) % len(self.frames)
        self.show_image()
