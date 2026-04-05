# Quick Start Guide

## 📦 Repository Structure

```
sreenivasa-seva-automation/
├── config.json              # Edit this to customize
├── requirements.txt         # Dependencies
├── scripts/
│   ├── download_images.py  # Download god images (run first)
│   └── create_reel.py      # Generate videos (run after download)
├── images/                 # Downloaded images go here (auto-created)
├── audio/                  # Put your audio files here
├── output/                 # Generated videos appear here
└── venv/                   # Python virtual environment
```

---

## 🚀 3-Step Workflow

### **Step 1: Configure**

Edit `config.json`:

```json
{
  "download": {
    "gods": ["shiva", "vishnu"],      // Which gods to download
    "images_per_god": 20,              // How many images per god
    "source": "wikimedia"             // wikimedia (free) or pexels/unsplash/pixabay (need API keys)
  },
  "images_folder": "images",
  "audio_file": "audio/song.mp3",
  "attach_audio": true,
  "total_duration": 30.0,
  ...
}
```

---

### **Step 2: Download Images**

```bash
# Install dependencies (once)
pip install -r requirements.txt

# Download images based on config
python scripts/download_images.py
```

**What happens:**
- Downloads images from Wikimedia Commons (free, no API key needed)
- Saves to `images/<god_name>/` folders
- Example: `images/shiva/Shiva_001.jpg`, `images/vishnu/Vishnu_001.jpg`

---

### **Step 3: Generate Videos**

```bash
# Generate video from downloaded images
python scripts/create_reel.py
```

**What happens:**
- Uses images from `images/` folder
- Adds audio from `audio/song.mp3` (if `attach_audio: true`)
- Creates video at `output/final_reel_with_audio.mp4`

---

## ⚙️ Configuration Options

### Download Settings (`config.json` → `download`)

| Option | Description | Default |
|--------|-------------|---------|
| `gods` | List of gods to download images for | `["shiva"]` |
| `images_per_god` | Number of images to download per god | `20` |
| `source` | Image source: `wikimedia`, `pexels`, `unsplash`, `pixabay`, `all` | `wikimedia` |

### Video Settings (`config.json`)

| Option | Description |
|--------|-------------|
| `images_folder` | Where downloaded images are stored (`images/`) |
| `audio_file` | Path to audio file (`audio/song.mp3`) |
| `output_file` | Output video filename |
| `attach_audio` | `true` to include audio, `false` for silent video |
| `total_duration` | Video length in seconds (used when `attach_audio: false`) |
| `transition.duration` | Crossfade length between images (seconds) |
| `effects.zoom_enabled` | Enable zoom effect on images |
| `effects.zoom_scale` | Zoom amount (e.g., 0.05 = 5% zoom) |
| `hooks` | Text overlay options (randomly picked for first image) |

---

## 📥 Image Sources

### 1. Wikimedia Commons (**Recommended**)
- ✅ **No API key required**
- ✅ Completely free, public domain
- ✅ Safe for YouTube/Instagram monetization
- ✅ No rate limits
- Just set `"source": "wikimedia"`

### 2. Pexels / Unsplash / Pixabay
- ⚠️ Requires free API keys (optional)
- ⚡ More images, different variety
- 🔑 Get keys:
  - Pexels: https://www.pexels.com/api/
  - Unsplash: https://unsplash.com/developers
  - Pixabay: https://pixabay.com/api/docs/

Add keys to `config.json`:
```json
{
  "pexels_api_key": "your_key_here",
  "unsplash_access_key": "your_key_here",
  "pixabay_api_key": "your_key_here"
}
```

---

## 🎯 Supported Gods

Out of the box keywords for:
- `shiva`, `vishnu`, `ganesha`, `lakshmi`
- `saraswati`, `durga`, `kali`, `krishna`
- `ram`, `hanuman`, `sai`, `temple`

**Custom gods:** Just add any keyword to the `gods` list in config! The script will search for it.

---

## 📝 Example Configurations

### Example 1: Quick Shiva Reel
```json
{
  "download": {
    "gods": ["shiva"],
    "images_per_god": 30,
    "source": "wikimedia"
  },
  "attach_audio": true,
  "total_duration": 60
}
```
→ Downloads 30 Shiva images → Creates 60-second video with audio

### Example 2: Silent Video, Fixed Duration
```json
{
  "download": {
    "gods": ["krishna", "radha"],
    "images_per_god": 15,
    "source": "all"
  },
  "attach_audio": false,
  "total_duration": 45
}
```
→ Downloads 30 images total → Creates 45-second silent video

---

## 🐛 Troubleshooting

**"No images found"**
- Try different keywords (edit `GOD_KEYWORDS` in `download_images.py`)
- Use `source: "all"` with API keys for more results
- Some gods have fewer images on Wikimedia

**403 errors on Wikimedia**
- Normal rate limiting, script will retry
- Reduce `images_per_god` or wait a minute

**"ModuleNotFoundError: No module named 'PIL'"**
```bash
pip install -r requirements.txt
```

**FFmpeg not found**
- Install FFmpeg and add to PATH
- Test: `ffmpeg -version`

---

## 🎉 That's It!

1. Edit `config.json` with your god names
2. `python scripts/download_images.py`
3. `python scripts/create_reel.py`
4. Find your video in `output/` folder

All images are copyright-free for commercial use! ✅
