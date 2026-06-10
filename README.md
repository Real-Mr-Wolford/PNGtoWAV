# ⚔️ D&D Steganography Suite

> **Hide secret messages inside audio & image files — then pull them back out.**  
> Perfect for slipping clues, riddles, or lore into seemingly innocent files for your players.

All hiding is done via **LSB (Least Significant Bit)** encoding — changes are invisible to the eye and inaudible to the ear.

---

## 🗺️ Feature Overview

| Tool | What it does |
|------|-------------|
| 🎵 **Audio Steganography** | Hide or extract text messages in WAV audio files |
| 🖼️ **Image Steganography** | Hide or extract text messages in PNG image files |
| 🔀 **Image ↔ Audio Converter** | Convert any image into a WAV file and back — the WAV sounds like noise but *is* the image |

---

## 🎵 Audio Steganography

### Hiding a message in a new WAV

1. Click **"🎵 Audio Steganography"** from the main menu
2. Type your secret message in the **"Secret message"** box
3. Click **"Generate WAV with Hidden Message"** and choose a save location
4. Send the WAV to your players — it plays as a 440 Hz tone

> 💡 The WAV will be at least 1 second long (44,100 samples) regardless of message length.

### Extracting a message from a WAV

1. Click **"Select WAV File"** and pick the file
2. Click **"Extract Hidden Message"**
3. The decoded message appears in the box below

> ⚠️ Only works on WAV files — MP3 and other compressed formats will **not** work.

---

## 🖼️ Image Steganography

### Choosing a base image

You need a base image to hide your message in. Two options:

- **Select PNG** — load your own PNG (a map, handout, texture, etc.)
- **Generate Noise** — creates a random coloured image at a size you specify (e.g. `400x400`). Great when you don't want to alter an existing image.

### Hiding a message in an image

1. Load or generate a base image (see above)
2. Type your secret message in the **"Secret message"** box
3. Click **"Hide Message in Image"** and save as a PNG
4. Share the PNG file directly with your players

> ⚠️ Always share the PNG as a **direct file attachment** — never screenshot it or re-save as JPEG. Lossy compression destroys the hidden bits.

> 💡 A 400×400 image can hold ~60,000 characters — far more than any message you'd realistically need.

### Extracting a message from an image

1. Click **"Select PNG to Decode"** and pick the file
2. Click **"Extract Hidden Message"**
3. The message appears in the output box

---

## 🔀 Image ↔ Audio Converter

This is different from steganography — it converts an entire image **into** a WAV file where every pixel channel becomes a sound sample. The result sounds like white noise but decodes back into a perfect copy of the original image.

### Image → WAV

1. Click **"Select Image"** and pick any PNG, JPG, BMP, or GIF
2. Click **"Convert Image → WAV"** and save the file
3. Hand the WAV to your players — to them it's just a noise file

### WAV → Image

1. Click **"Select WAV"** and pick the encoded WAV
2. Click **"Convert WAV → Image"** and choose a save location
3. The recovered PNG is saved to that path

> 💡 Large images produce large WAV files (~3× the pixel count in bytes). A 400×400 image produces ~960 KB.

> ⚠️ Only works on WAVs created by this tool. Do **not** convert to MP3 or re-encode the file.

---

## 🔬 How It Works

| Concept | Explanation |
|---------|-------------|
| **LSB Encoding** | The least significant bit of each audio sample (or image channel byte) is replaced with one bit of your message. The change is too small to hear or see. |
| **Terminator** | Messages end with the marker `###` so the decoder knows where to stop reading. |
| **Image → WAV** | Each R, G, B channel value (0–255) maps to a 16-bit PCM sample. Width & height are stored as a 2-sample header so the decoder can recover exact image dimensions. |
| **Capacity** | Audio: limited only by WAV length. Image: ~`W × H × 3 ÷ 8` characters (a 400×400 image holds ~60,000 chars). |

---

## 💡 D&D Tips

- **Layer both tools:** hide a text message inside a noise PNG, then convert that PNG into a WAV. Players must decode WAV → PNG, then PNG → message.
- **Use the noise generator** as a carrier — it looks like a random colour splash with nothing obviously hidden inside.
- **Name files evocatively:** `the_warlock_hum.wav` or `dungeon_static.wav` hints at their purpose without giving it away.
- **Always send files as attachments** in Discord or email — never upload as inline images. Discord silently re-compresses PNGs to JPEG.

---

## 🛠️ Troubleshooting

| Error | Cause & Fix |
|-------|-------------|
| `"No hidden message found"` | The file wasn't encoded with this tool, was re-compressed, or the terminator was overwritten. Make sure you have the original unmodified file. |
| `"JPEG detected — cannot decode"` | The file was re-saved as JPEG at some point. Lossy compression destroys the hidden bits — get the original PNG. |
| `"Invalid dimensions in header"` | The WAV wasn't created by the Image→WAV converter. Only use WAVs produced by this tool. |
| Garbled / partial output | The WAV was re-encoded or trimmed. The file must be byte-for-byte identical to what was saved. |
| WAV file is very large | Large images create large WAVs. Crop or resize the image before encoding. |

---

## 📦 Requirements

- Python 3.x
- [Pillow](https://pillow.readthedocs.io/) — `pip install Pillow`
- Tkinter (included with most Python installations)

```bash
pip install Pillow
python steg_suite.py
```

---

*Messages are hidden using LSB encoding — invisible to the naked eye and inaudible to the human ear.*
