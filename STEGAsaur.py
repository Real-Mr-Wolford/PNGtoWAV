import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import wave
import math
import struct
import random
from PIL import Image, ImageTk

TERMINATOR = "###"

# ─────────────────────────────────────────────
#  Shared LSB helpers
# ─────────────────────────────────────────────

def text_to_bits(text: str) -> str:
    return ''.join(format(ord(c), '08b') for c in text)

def bits_to_text(bits: str) -> str:
    chars = []
    for i in range(0, len(bits) - 7, 8):
        byte = bits[i:i+8]
        try:
            chars.append(chr(int(byte, 2)))
        except ValueError:
            break
        if ''.join(chars[-3:]) == TERMINATOR:
            break
    result = ''.join(chars)
    if result.endswith(TERMINATOR):
        return result[:-len(TERMINATOR)]
    return None


# ─────────────────────────────────────────────
#  Image ↔ Audio conversion helpers
# ─────────────────────────────────────────────

def image_to_wav(img: Image.Image, output_path: str, sample_rate: int = 44100):
    """
    Encode every pixel channel (R, G, B) of an image as a PCM audio sample.
    Each 0-255 channel value maps linearly to a 16-bit signed PCM sample.
    A 4-byte magic header is prepended so we can recover width/height on decode.

    Layout of the WAV data:
        [4 bytes: width as uint16 LE][4 bytes: height as uint16 LE]
        [width*height*3 samples: one per channel, R then G then B per pixel]
    """
    img = img.convert("RGB")
    w, h = img.size
    pixels = list(img.getdata())
    channels = [ch for px in pixels for ch in px]

    raw = bytearray()
    # Header: width and height as two uint16 LE values encoded as PCM samples
    for dim in (w, h):
        raw.extend(struct.pack('<h', dim))   # store raw as signed; decode with unpack

    for val in channels:
        # Map 0-255  →  -32768..32767  (exact inverse: (pcm + 32768) / 65535 * 255)
        pcm = int((val / 255.0) * 65535) - 32768
        raw.extend(struct.pack('<h', pcm))

    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(raw))


def wav_to_image(wav_path: str) -> Image.Image:
    """
    Decode a WAV file produced by image_to_wav() back into a PIL Image.
    Raises ValueError if the file doesn't look like an encoded image WAV.
    """
    with wave.open(wav_path, 'rb') as wf:
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
            raise ValueError("WAV must be mono 16-bit (as produced by this tool).")
        raw = bytearray(wf.readframes(wf.getnframes()))

    # Read header: first 4 bytes = two int16 values = width, height
    if len(raw) < 4:
        raise ValueError("File too short to contain a valid header.")

    w = struct.unpack('<h', raw[0:2])[0]
    h = struct.unpack('<h', raw[2:4])[0]

    if w <= 0 or h <= 0 or w > 8000 or h > 8000:
        raise ValueError(f"Invalid dimensions in header: {w}×{h}.\n"
                         "This WAV was not encoded by this tool.")

    expected_samples = w * h * 3
    payload = raw[4:]
    if len(payload) < expected_samples * 2:
        raise ValueError(f"WAV payload too short. Expected {expected_samples} samples "
                         f"for a {w}×{h} image, got {len(payload)//2}.")

    channels = []
    for i in range(expected_samples):
        pcm = struct.unpack('<h', payload[i*2 : i*2+2])[0]
        val = int(((pcm + 32768) / 65535.0) * 255)
        val = max(0, min(255, val))   # clamp rounding edge cases
        channels.append(val)

    pixels = [
        (channels[i*3], channels[i*3+1], channels[i*3+2])
        for i in range(w * h)
    ]
    img = Image.new("RGB", (w, h))
    img.putdata(pixels)
    return img


# ─────────────────────────────────────────────
#  App shell
# ─────────────────────────────────────────────

class SteganographySuite:
    def __init__(self, root):
        self.root = root
        self.root.title("🗺️  D&D Steganography Suite")
        self.root.geometry("640x600")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")

        self.container = tk.Frame(self.root, bg="#1a1a2e")
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (MainMenu, AudioUtility, ImageUtility, ImageAudioUtility):
            frame = F(parent=self.container, controller=self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(MainMenu)

    def show_frame(self, page_class):
        self.frames[page_class].tkraise()


# ─────────────────────────────────────────────
#  Styling helpers
# ─────────────────────────────────────────────

BG       = "#1a1a2e"
PANEL    = "#16213e"
ACCENT   = "#e94560"
GOLD     = "#f5a623"
TEAL     = "#000000"
FG       = "#e0e0e0"
FG_DIM   = "#000000"
BTN_BG   = "#0f3460"
BTN_ACT  = "#e94560"
FONT     = ("Segoe UI", 10)
FONT_B   = ("Segoe UI", 10, "bold")
FONT_H   = ("Segoe UI", 16, "bold")
FONT_SH  = ("Segoe UI", 12)

def styled_btn(parent, text, command, color=BTN_BG, fg=FG, width=28):
    return tk.Button(
        parent, text=text, command=command,
        bg=color, fg=fg, activebackground=BTN_ACT, activeforeground="white",
        font=FONT_B, width=width, relief="flat", cursor="hand2",
        padx=6, pady=6
    )

def section_label(parent, text, bg=PANEL):
    tk.Label(parent, text=text, font=FONT_B, bg=bg,
             fg=GOLD).pack(anchor="w", padx=16, pady=(10, 2))

def divider(parent):
    tk.Frame(parent, height=1, bg=ACCENT).pack(fill="x", padx=12, pady=8)

def output_box(parent, height=4):
    box = tk.Text(parent, height=height, width=56, bg="#0d0d1a", fg="#132a06",
                  insertbackground=FG, font=("Courier New", 9),
                  relief="flat", padx=6, pady=6, state="disabled")
    box.pack(padx=16, pady=(0, 8))
    return box

def set_output(box, text):
    box.config(state="normal")
    box.delete("1.0", tk.END)
    box.insert(tk.END, text)
    box.config(state="disabled")


# ─────────────────────────────────────────────
#  Main Menu
# ─────────────────────────────────────────────

class MainMenu(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG)

        tk.Label(self, text="⚔️  D&D Steganography Suite",
                 font=("Segoe UI", 18, "bold"), bg=BG, fg=GOLD).pack(pady=(40, 4))
        tk.Label(self, text="Hide secret messages inside audio & images",
                 font=FONT_SH, bg=BG, fg=FG_DIM).pack(pady=(0, 30))

        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack()

        styled_btn(btn_frame, "🎵  Audio Steganography  (WAV)",
                   lambda: controller.show_frame(AudioUtility),
                   color=BTN_BG).pack(pady=8)

        styled_btn(btn_frame, "🖼️  Image Steganography  (PNG)",
                   lambda: controller.show_frame(ImageUtility),
                   color=BTN_BG).pack(pady=8)

        styled_btn(btn_frame, "🔀  Image ↔ Audio Converter",
                   lambda: controller.show_frame(ImageAudioUtility),
                   color="#0a4a5a").pack(pady=8)

        tk.Label(self, text="Messages are hidden using LSB encoding — invisible to the naked eye.",
                 font=("Segoe UI", 8), bg=BG, fg=FG_DIM).pack(side="bottom", pady=12)


# ─────────────────────────────────────────────
#  Audio Utility  (unchanged)
# ─────────────────────────────────────────────

class AudioUtility(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG)

        tk.Button(self, text="← Back", command=lambda: controller.show_frame(MainMenu),
                  bg=BG, fg=FG_DIM, relief="flat", font=FONT, cursor="hand2").pack(anchor="w", padx=10, pady=8)

        tk.Label(self, text="🎵 Audio Steganography", font=FONT_H, bg=BG, fg=GOLD).pack(pady=(0, 10))

        enc = tk.Frame(self, bg=PANEL, relief="flat", bd=0)
        enc.pack(fill="x", padx=16, pady=4)

        section_label(enc, "ENCODE — Hide a message in a new WAV")

        tk.Label(enc, text="Secret message:", font=FONT, bg=PANEL, fg=FG).pack(anchor="w", padx=16)
        self.msg_entry = tk.Entry(enc, width=54, bg="#0d0d1a", fg=FG,
                                  insertbackground=FG, relief="flat", font=FONT)
        self.msg_entry.pack(padx=16, pady=(0, 8), ipady=4)

        styled_btn(enc, "Generate WAV with Hidden Message", self.generate_and_encode,
                   color=ACCENT, width=36).pack(pady=(0, 10))

        dec = tk.Frame(self, bg=PANEL, relief="flat", bd=0)
        dec.pack(fill="x", padx=16, pady=4)

        section_label(dec, "DECODE — Extract from an existing WAV")

        self.wav_path = tk.StringVar(value="No file selected.")
        styled_btn(dec, "Select WAV File", self.select_file, width=20).pack(padx=16, anchor="w")
        tk.Label(dec, textvariable=self.wav_path, font=("Segoe UI", 8),
                 bg=PANEL, fg=FG_DIM).pack(anchor="w", padx=16)

        styled_btn(dec, "Extract Hidden Message", self.reveal_message,
                   color=GOLD, fg="#1a1a2e", width=24).pack(padx=16, pady=6, anchor="w")

        section_label(dec, "Decoded message:")
        self.output = output_box(dec)

    def select_file(self):
        path = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
        if path:
            self.wav_path.set(path)

    def generate_and_encode(self):
        message = self.msg_entry.get().strip()
        if not message:
            messagebox.showerror("Missing input", "Enter a message to hide.")
            return

        output_path = filedialog.asksaveasfilename(
            defaultextension=".wav", filetypes=[("WAV files", "*.wav")])
        if not output_path:
            return

        payload     = message + TERMINATOR
        bin_message = text_to_bits(payload)
        bits_needed = len(bin_message)
        sample_rate = 44100
        frequency   = 440.0
        num_samples = max(bits_needed, sample_rate)

        raw = bytearray()
        for i in range(num_samples):
            t     = i / sample_rate
            value = int(32767.0 * math.sin(2.0 * math.pi * frequency * t))
            raw.extend(struct.pack('<h', value))

        for i, bit in enumerate(bin_message):
            raw[i * 2] = (raw[i * 2] & 0xFE) | int(bit)

        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(bytes(raw))

        messagebox.showinfo("Done!", f"WAV saved to:\n{output_path}")

    def reveal_message(self):
        path = self.wav_path.get()
        if path == "No file selected.":
            messagebox.showerror("No file", "Select a WAV file first.")
            return

        with wave.open(path, 'rb') as wf:
            raw = bytearray(wf.readframes(wf.getnframes()))

        bits   = ''.join(str(raw[i * 2] & 1) for i in range(len(raw) // 2))
        result = bits_to_text(bits)
        set_output(self.output,
                   result if result is not None else "No hidden message found.")


# ─────────────────────────────────────────────
#  Image Utility  (Pillow backend)
# ─────────────────────────────────────────────

class ImageUtility(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG)
        self._pil_base: Image.Image | None = None

        tk.Button(self, text="← Back", command=lambda: controller.show_frame(MainMenu),
                  bg=BG, fg=FG_DIM, relief="flat", font=FONT, cursor="hand2").pack(anchor="w", padx=10, pady=8)

        tk.Label(self, text="🖼️  Image Steganography", font=FONT_H, bg=BG, fg=GOLD).pack(pady=(0, 6))

        enc = tk.Frame(self, bg=PANEL)
        enc.pack(fill="x", padx=16, pady=4)

        section_label(enc, "ENCODE — Hide a message in an image")

        src_row = tk.Frame(enc, bg=PANEL)
        src_row.pack(padx=12, pady=(0, 6), anchor="w")
        styled_btn(src_row, "Select PNG", self.select_src_image, width=14).pack(side="left", padx=(0, 8))
        styled_btn(src_row, "Generate Noise", self.generate_noise_image, width=14).pack(side="left")

        self.src_status = tk.Label(enc, text="No image loaded.", font=("Segoe UI", 8),
                                   bg=PANEL, fg=FG_DIM)
        self.src_status.pack(anchor="w", padx=16, pady=(0, 4))

        tk.Label(enc, text="Secret message:", font=FONT, bg=PANEL, fg=FG).pack(anchor="w", padx=16)
        self.img_msg = tk.Entry(enc, width=54, bg="#0d0d1a", fg=FG,
                                insertbackground=FG, relief="flat", font=FONT)
        self.img_msg.pack(padx=16, pady=(0, 8), ipady=4)

        styled_btn(enc, "Hide Message in Image", self.encode_image,
                   color=ACCENT, width=30).pack(pady=(0, 10))

        dec = tk.Frame(self, bg=PANEL)
        dec.pack(fill="x", padx=16, pady=4)

        section_label(dec, "DECODE — Extract from an encoded PNG")

        self.dec_path = tk.StringVar(value="No file selected.")
        styled_btn(dec, "Select PNG to Decode", self.select_decode_image, width=22).pack(padx=16, anchor="w")
        tk.Label(dec, textvariable=self.dec_path, font=("Segoe UI", 8),
                 bg=PANEL, fg=FG_DIM).pack(anchor="w", padx=16)

        styled_btn(dec, "Extract Hidden Message", self.decode_image,
                   color=GOLD, fg="#1a1a2e", width=24).pack(padx=16, pady=6, anchor="w")

        section_label(dec, "Decoded message:")
        self.img_output = output_box(dec)

    def select_src_image(self):
        path = filedialog.askopenfilename(filetypes=[("PNG files", "*.png")])
        if not path:
            return
        try:
            self._pil_base = Image.open(path).convert("RGB")
            w, h = self._pil_base.size
            self.src_status.config(
                text=f"Loaded: {path.split('/')[-1]}  ({w}×{h} — capacity ~{w*h*3//8} chars)",
                fg="#a8ff78")
        except Exception as e:
            messagebox.showerror("Load error", str(e))

    def generate_noise_image(self):
        size_str = simpledialog.askstring(
            "Noise Image Size", "Enter dimensions as WxH (e.g. 400x400):",
            initialvalue="400x400")
        if not size_str:
            return
        try:
            w_str, h_str = size_str.lower().split('x')
            w, h = int(w_str), int(h_str)
            if w <= 0 or h <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Bad input", "Use format: 400x400")
            return

        pixels = [random.randint(0, 255) for _ in range(w * h * 3)]
        self._pil_base = Image.frombytes("RGB", (w, h), bytes(pixels))
        self.src_status.config(
            text=f"Generated noise  ({w}×{h} — capacity ~{w*h*3//8} chars)",
            fg="#a8ff78")

    def encode_image(self):
        if self._pil_base is None:
            messagebox.showerror("No image", "Load or generate a base image first.")
            return
        message = self.img_msg.get().strip()
        if not message:
            messagebox.showerror("No message", "Enter a message to hide.")
            return

        payload     = message + TERMINATOR
        bin_message = text_to_bits(payload)
        pixels      = list(self._pil_base.getdata())
        capacity    = len(pixels) * 3

        if len(bin_message) > capacity:
            messagebox.showerror("Too small",
                f"Image can hold ~{capacity//8} chars but message needs {len(bin_message)//8}.")
            return

        output_path = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if not output_path:
            return
        if not output_path.lower().endswith(".png"):
            output_path += ".png"

        channels = [ch for px in pixels for ch in px]
        for i, bit in enumerate(bin_message):
            channels[i] = (channels[i] & 0xFE) | int(bit)

        new_pixels = [
            (channels[i*3], channels[i*3+1], channels[i*3+2])
            for i in range(len(pixels))
        ]
        out = Image.new("RGB", self._pil_base.size)
        out.putdata(new_pixels)
        out.save(output_path, format="PNG")

        messagebox.showinfo("Done!",
            f"Encoded PNG saved to:\n{output_path}\n\n"
            f"Message length: {len(message)} chars  |  Bits used: {len(bin_message)}/{capacity}\n\n"
            f"⚠️  Share this file directly — do NOT screenshot it or re-save as JPEG,\n"
            f"or the hidden message will be destroyed.")

    def decode_image(self):
        path = self.dec_path.get()
        if path == "No file selected.":
            messagebox.showerror("No file", "Select a PNG file to decode.")
            return
        try:
            img = Image.open(path)
        except Exception as e:
            messagebox.showerror("Load error", str(e))
            return

        if img.format == "JPEG":
            messagebox.showerror(
                "JPEG detected — cannot decode",
                "This file is actually a JPEG (even if named .png).\n\n"
                "JPEG lossy compression destroys LSB steganography — "
                "the hidden bits are gone.\n\n"
                "Make sure you send the encoded PNG as a file attachment, "
                "not a screenshot. Many platforms (Discord, iMessage, etc.) "
                "silently re-compress images to JPEG.")
            return

        img = img.convert("RGB")
        pixels   = list(img.getdata())
        channels = [ch for px in pixels for ch in px]
        bits     = ''.join(str(c & 1) for c in channels)

        result = bits_to_text(bits)
        set_output(self.img_output,
                   result if result is not None else "No hidden message found.")

    def select_decode_image(self):
        path = filedialog.askopenfilename(filetypes=[("PNG files", "*.png")])
        if path:
            self.dec_path.set(path)


# ─────────────────────────────────────────────
#  Image ↔ Audio Converter  (new)
# ─────────────────────────────────────────────

class ImageAudioUtility(tk.Frame):
    """
    Converts an image (PNG/JPG/etc.) into a WAV file and back.

    How it works:
      Each pixel channel value (0-255) is stored as one 16-bit PCM audio sample.
      A 2-sample header encodes the image width and height so the decoder knows
      the dimensions. The resulting WAV sounds like white noise but is a perfect
      lossless representation of the image — no steganography, the image IS the audio.

    Why this is useful for D&D:
      You can hand players a weird "ambient sound file" that is actually a map or
      handout. They run it through this tool to get the image back.
    """

    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG)

        tk.Button(self, text="← Back", command=lambda: controller.show_frame(MainMenu),
                  bg=BG, fg=FG_DIM, relief="flat", font=FONT, cursor="hand2").pack(anchor="w", padx=10, pady=8)

        tk.Label(self, text="🔀  Image ↔ Audio Converter", font=FONT_H, bg=BG, fg=TEAL).pack(pady=(0, 4))
        tk.Label(self,
                 text="Convert any image into a WAV file — and back.\n"
                      "The WAV sounds like noise but contains the full image.",
                 font=("Segoe UI", 9), bg=BG, fg=FG_DIM, justify="center").pack(pady=(0, 10))

        # ── Image → WAV panel ─────────────────────────
        enc = tk.Frame(self, bg=PANEL)
        enc.pack(fill="x", padx=16, pady=4)

        section_label(enc, "IMAGE → WAV  (encode)")

        self.enc_img_path = tk.StringVar(value="No image selected.")
        btn_row = tk.Frame(enc, bg=PANEL)
        btn_row.pack(padx=12, pady=(0, 4), anchor="w")
        styled_btn(btn_row, "Select Image", self.select_encode_image, width=16).pack(side="left", padx=(0, 8))
        tk.Label(btn_row, textvariable=self.enc_img_path, font=("Segoe UI", 8),
                 bg=PANEL, fg=FG_DIM).pack(side="left")

        self.enc_status = tk.Label(enc, text="", font=("Segoe UI", 8), bg=PANEL, fg=FG_DIM)
        self.enc_status.pack(anchor="w", padx=16, pady=(0, 4))

        styled_btn(enc, "Convert Image → WAV", self.encode_image_to_wav,
                   color=TEAL, fg="#0d0d1a", width=26).pack(pady=(0, 10))

        # ── WAV → Image panel ─────────────────────────
        dec = tk.Frame(self, bg=PANEL)
        dec.pack(fill="x", padx=16, pady=4)

        section_label(dec, "WAV → IMAGE  (decode)")

        self.dec_wav_path = tk.StringVar(value="No WAV selected.")
        btn_row2 = tk.Frame(dec, bg=PANEL)
        btn_row2.pack(padx=12, pady=(0, 4), anchor="w")
        styled_btn(btn_row2, "Select WAV", self.select_decode_wav, width=16).pack(side="left", padx=(0, 8))
        tk.Label(btn_row2, textvariable=self.dec_wav_path, font=("Segoe UI", 8),
                 bg=PANEL, fg=FG_DIM).pack(side="left")

        styled_btn(dec, "Convert WAV → Image", self.decode_wav_to_image,
                   color=GOLD, fg="#1a1a2e", width=26).pack(pady=(4, 4))

        self.dec_status = tk.Label(dec, text="", font=("Segoe UI", 9),
                                   bg=PANEL, fg="#a8ff78", wraplength=560, justify="left")
        self.dec_status.pack(anchor="w", padx=16, pady=(0, 8))

        # ── Info box ──────────────────────────────────
        info = tk.Frame(self, bg=BG)
        info.pack(fill="x", padx=16, pady=(6, 0))
        tk.Label(info,
                 text="ℹ️  Supports PNG, JPG, BMP, GIF input.  "
                      "Large images produce large WAV files (~3× pixel count in bytes).",
                 font=("Segoe UI", 8), bg=BG, fg=FG_DIM, wraplength=580, justify="left").pack(anchor="w")

    # ── Helpers ────────────────────────────────────

    def select_encode_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"),
                       ("All files", "*.*")])
        if not path:
            return
        try:
            img = Image.open(path).convert("RGB")
            w, h = img.size
            wav_size_kb = (w * h * 3 * 2 + 4) // 1024
            self.enc_img_path.set(path.split("/")[-1])
            self.enc_status.config(
                text=f"{w}×{h} px  →  WAV will be ~{wav_size_kb} KB",
                fg="#a8ff78")
            self._encode_pil = img
        except Exception as e:
            messagebox.showerror("Load error", str(e))
            self._encode_pil = None

    def encode_image_to_wav(self):
        if not hasattr(self, '_encode_pil') or self._encode_pil is None:
            messagebox.showerror("No image", "Select an image first.")
            return

        output_path = filedialog.asksaveasfilename(
            defaultextension=".wav", filetypes=[("WAV files", "*.wav")])
        if not output_path:
            return
        if not output_path.lower().endswith(".wav"):
            output_path += ".wav"

        try:
            image_to_wav(self._encode_pil, output_path)
            w, h = self._encode_pil.size
            messagebox.showinfo("Done!",
                f"Image encoded into WAV:\n{output_path}\n\n"
                f"Image size: {w}×{h}  |  Samples: {w*h*3 + 2}\n\n"
                f"Share this WAV with your players — they can decode it back\n"
                f"into the original image using this tool.")
        except Exception as e:
            messagebox.showerror("Encode error", str(e))

    def select_decode_wav(self):
        path = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
        if path:
            self.dec_wav_path.set(path.split("/")[-1])
            self._decode_wav_path = path
            self.dec_status.config(text="")

    def decode_wav_to_image(self):
        if not hasattr(self, '_decode_wav_path'):
            messagebox.showerror("No file", "Select a WAV file first.")
            return

        output_path = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if not output_path:
            return
        if not output_path.lower().endswith(".png"):
            output_path += ".png"

        try:
            img = wav_to_image(self._decode_wav_path)
            img.save(output_path, format="PNG")
            w, h = img.size
            self.dec_status.config(
                text=f"✅  Decoded {w}×{h} image saved to: {output_path}")
            messagebox.showinfo("Done!",
                f"Image recovered from WAV:\n{output_path}\n\nSize: {w}×{h} px")
        except ValueError as e:
            messagebox.showerror("Decode error", str(e))
        except Exception as e:
            messagebox.showerror("Unexpected error", str(e))


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app  = SteganographySuite(root)
    root.mainloop()
