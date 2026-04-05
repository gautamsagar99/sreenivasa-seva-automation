# 🎬 Sreenivasa Seva Automation - Complete Guide

Generate AI-powered devotional videos for Hindu deities with a single command.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Workflows](#workflows)
5. [One-Command Pipeline](#one-command-pipeline)
6. [Advanced Settings](#advanced-settings)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

### What This Does

1. **Generate optimized prompts** using Ollama (local AI)
2. **Create images** using Hugging Face FLUX (state-of-the-art image generation)
3. **Assemble video** with transitions, effects, and audio

### Pipeline

```
config.json
     ↓
generate_prompts.py (Ollama AI) → ai_generation.prompts
     ↓
generate_ai_images.py (FLUX) → images/*.png
     ↓
create_reel.py (OpenCV) → output/final_reel_with_audio.mp4
```

---

## 📦 Installation

### 1. System Requirements

- **Python 3.10+** (tested with 3.10)
- **Git** (for cloning)
- **FFmpeg** (for video encoding)
  - **Windows**: Download from https://ffmpeg.org/download.html, extract, add to PATH
  - **macOS**: `brew install ffmpeg`
  - **Linux**: `sudo apt install ffmpeg`
- **Ollama** (for prompt generation)
  - Download from https://ollama.ai
  - Install and keep running in background

### 2. Clone & Setup

```bash
# Clone repository
cd D:\PROJECTS\2026\sreenivasa-seva-automation

# Create virtual environment
python -m venv venv

# Activate it
# Windows PowerShell:
venv\Scripts\Activate.ps1
# OR Windows CMD:
venv\Scripts\activate.bat
# OR macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Install Ollama Model

```bash
# Pull the recommended model (4GB)
ollama pull mistral:7b-instruct

# Verify it's installed:
ollama list
# Should show: mistral:7b-instruct
```

### 4. Get Hugging Face Token

1. Visit https://huggingface.co/settings/tokens
2. Click "New token"
3. Select role: `user` (or higher)
4. Copy the token

### 5. Setup Environment Variables

Create `.env` file in project root:

```env
# Hugging Face API token (required for image generation)
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> **Security Note:** `.env` is in `.gitignore` - never commit it!

---

## ⚙️ Configuration

Edit `config.json` to customize behavior:

### Essential Settings

```json
{
  "prompt_generation": {
    "count": 5,              // Number of prompts to generate
    "subjects": ["shiva"],   // Deities: shiva, vishnu, ganesha, krishna, ram, hanuman, etc.
    "model": "mistral:7b-instruct",
    "temperature": 0.85      // Creativity (0.5-1.0)
  },

  "ai_generation": {
    "default_model": "flux_schnell",  // Recommended: flux_schnell (fast) or flux_dev (higher quality)
    "image_size": [1024, 1024],       // Output resolution
    "num_inference_steps": 20,        // Quality (20-30, higher = slower but better)
    "guidance_scale": 3.5,            // Prompt adherence (3.0-5.0)
    "prompts": []                     // Filled automatically by generate_prompts.py
  },

  "images_folder": "images",
  "audio_file": "audio/song.mp3",      // Your audio file path
  "output_file": "output/final_reel_with_audio.mp4",
  "attach_audio": true,
  "total_duration": 30.0,

  "transition": {
    "duration": 0.5,
    "type": "fade"
  },

  "effects": {
    "zoom_enabled": true,
    "zoom_scale": 0.05
  },

  "hooks": [
    "Close your eyes and pray",
    "Govinda is with you",
    "Your blessings are coming"
  ]
}
```

---

## 🎯 Choose Your Workflow

### Two Ways to Get Images

**Option 1: AI-Generated (High Quality)**
- Uses Ollama + FLUX to create unique devotional images
- Requires: Ollama, HF token
- Time: 2-10 minutes (depending on count)

**Option 2: Download from Web (Fast)**
- Downloads from Wikimedia/API
- Requires: Optional API keys for Pexels/Unsplash
- Time: 30-60 seconds

### Automatic Detection

`run_all.py` automatically selects workflow based on `config.json`:

```json
{
  "download": {
    "enabled": false,               // true = use download workflow
    "gods": ["shiva"],
    "images_per_god": 20
  },
  "ai_generation": {
    "enabled": true,                // true = use AI workflow
    "default_model": "flux_schnell",
    "prompts": []
  }
}
```

**If both are enabled**, you'll be prompted to choose.

---

## 🚀 Quick Start (One Command)

```bash
python scripts/run_all.py
```

That's it! The script will:
1. ✓ Check prerequisites (Ollama, HF token, FFmpeg, folders)
2. ✓ Run the appropriate workflow (AI or Download)
3. ✓ Generate video automatically
4. ✓ Show summary with output location

**No manual step-by-step needed!**

---

## 📝 Manual Commands (Optional)

If you prefer to run each step manually:

### AI Workflow
```bash
python scripts/generate_prompts.py      # Generate prompts with Ollama
python scripts/generate_ai_images.py    # Generate images with FLUX
python scripts/create_reel.py           # Create video
```

### Download Workflow
```bash
python scripts/download_images.py       # Download from web
python scripts/create_reel.py           # Create video
```

---

## 🔧 Advanced Settings

### Prompt Generation (`prompt_generation`)

| Setting | Description | Recommended |
|---------|-------------|-------------|
| `count` | Number of prompts to generate | 5-20 |
| `subjects` | Deity names | Any from list below |
| `model` | Ollama model | `mistral:7b-instruct` |
| `temperature` | Creativity (higher = more varied) | 0.8-0.95 |
| `max_new_tokens` | Max length of prompt | 150-250 |

### Image Generation (`ai_generation`)

| Setting | Description | Default |
|---------|-------------|---------|
| `default_model` | FLUX model | `flux_schnell` (fast, good) |
| `image_size` | Resolution [width, height] | [1024, 1024] |
| `num_inference_steps` | Quality vs speed trade-off | 20 (30 for best) |
| `guidance_scale` | How closely to follow prompt | 3.5 |
| `prompts` | Your prompt list | Auto-filled |

**Available FLUX models:**
- `flux_schnell` - Fastest (2-3 sec/image), good quality
- `flux_dev` - Slower (10-15 sec/image), best quality
- `sd35` - Stable Diffusion 3.5 (alternative)

### Video Settings

| Setting | Description |
|---------|-------------|
| `images_folder` | Source images directory |
| `audio_file` | Audio file to attach |
| `attach_audio` | `true` = include audio, `false` = silent |
| `total_duration` | Final video length (when attach_audio=false) |
| `transition.duration` | Crossfade between images |
| `transition.type` | `fade`, `wipe`, `slide` |
| `effects.zoom_enabled` | Ken Burns zoom effect |
| `effects.zoom_scale` | Zoom amount (0.05 = 5%) |
| `hooks` | Text overlays (random selected) |

---

## 🎯 Supported Deities

Built-in deity keywords for AI prompts:

**Main:** Shiva, Vishnu, Ganesha, Krishna, Rama, Hanuman, Lakshmi, Durga, Sai

**Additional (for download_images.py):**
Saraswati, Kali, Parvati, Radha, Sita, and more - just add any name!

---

## 📝 Complete Checklist

### Before First Run

- [ ] Python 3.10+ installed (`python --version`)
- [ ] FFmpeg installed (`ffmpeg -version`)
- [ ] Ollama installed and running (`ollama serve`)
- [ ] Model pulled (`ollama pull mistral:7b-instruct`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Hugging Face token obtained
- [ ] `.env` file created with HF_TOKEN
- [ ] `config.json` configured

### Run Order

**Recommended:**
```bash
python scripts/run_all.py  # One command does everything
```

**Or manual:**
1. For AI: `generate_prompts.py` → `generate_ai_images.py` → `create_reel.py`
2. For Download: `download_images.py` → `create_reel.py`

Output always in `output/` folder

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'ollama'"

```bash
pip install ollama
```

### "HF_TOKEN not set"

Create `.env` file with your token:
```bash
echo "HF_TOKEN=hf_your_token_here" > .env
```

### "Ollama is not running"

Start it:
```bash
ollama serve
# Keep this terminal open or run as background service
```

### "Model 'mistral:7b-instruct' not found"

Pull the model:
```bash
ollama pull mistral:7b-instruct
```

### "FFmpeg not found"

Install FFmpeg and add to PATH:
- Windows: Download, extract to `C:\ffmpeg\`, add `C:\ffmpeg\bin` to System PATH
- Test: `ffmpeg -version`

### No prompts generated / Empty config

Check `config.json` has:
```json
"prompt_generation": {
  "count": 5
}
```

### Images not appearing in video

- Ensure `images_folder` in config.json matches your images directory
- Check `ai_generation.prompts` is populated (run generate_prompts.py first)
- Verify images exist in `images/` folder

### Slow image generation

- Reduce `image_size` to [512, 512] for faster generation
- Reduce `num_inference_steps` to 10-15
- Use `flux_schnell` (default) instead of `flux_dev`

---

## 📊 Performance Estimates

| Step | Time (5 prompts) | Time (20 prompts) |
|------|------------------|-------------------|
| generate_prompts.py | 1-2 min | 4-8 min |
| generate_ai_images.py | 30-60 sec | 2-4 min |
| create_reel.py | 10-30 sec | 30-60 sec |
| **Total** | **~2-3 min** | **~7-12 min** |

**Image generation time depends on:**
- Model choice (flux_schnell = fastest)
- Image size (1024x1024 = slower than 512x512)
- Inference steps (20 vs 30)

---

## 🔄 Alternative: Pure Download Workflow

If you don't want to use AI image generation:

1. Edit `config.json`: disable AI, enable download
   ```json
   {
     "download": {
       "enabled": true,
       "gods": ["shiva", "vishnu"],
       "images_per_god": 20,
       "source": "wikimedia"
     },
     "ai_generation": {
       "enabled": false
     }
   }
   ```

2. Run:
   ```bash
   python scripts/download_images.py
   python scripts/create_reel.py
   ```

---

## 💡 Tips & Best Practices

### For Best Video Quality

1. Generate 10-20 AI prompts (higher count = more variety)
2. Use `flux_schnell` for speed, `flux_dev` for maximum quality
3. Set `num_inference_steps: 25-30` for crisp images (slower)
4. Use 1080p audio file for professional output
5. Enable `effects.zoom_enabled: true` for dynamic feel

### For Faster Generation

```json
{
  "prompt_generation": { "count": 5 },
  "ai_generation": {
    "image_size": [512, 512],
    "num_inference_steps": 15
  }
}
```

### Custom Audio

Place your audio file in `audio/` folder and update:
```json
"audio_file": "audio/your_custom_song.mp3"
```

Supported: MP3, WAV, M4A, AAC

---

## 📂 Project Structure

```
sreenivasa-seva-automation/
├── config.json              # Main configuration
├── requirements.txt         # Python dependencies
├── .env                     # Your HF token (gitignored)
├── .env.example             # Template
├── QUICKSTART.md           # This file
├── scripts/
│   ├── generate_prompts.py     # AI prompt generator (Ollama)
│   ├── generate_ai_images.py   # Image generator (FLUX)
│   ├── download_images.py      # Web image downloader (optional)
│   ├── create_reel.py          # Video creator
│   └── run_all.py              # Master orchestrator ⭐
├── images/                  # Generated/downloaded images (auto-created)
├── audio/                   # Audio files
│   └── song.mp3            # Default audio
├── output/                  # Final videos (auto-created)
└── venv/                   # Virtual environment (gitignored)
```

---

## 🎉 Quick Start (30 seconds)

```bash
# After installation (once):
ollama pull mistral:7b-instruct
echo "HF_TOKEN=hf_your_token" > .env

# Every new video:
python scripts/run_all.py
```

That's it! 🎊

---

## 📞 Support

Issues? Check:
1. `scripts/` - Each script has error handling
2. `.env` - HF_TOKEN present and valid
3. `ollama list` - Model exists
4. `ffmpeg -version` - FFmpeg in PATH

All logs shown in terminal for debugging.

---

**Made with ❤️ for Sreenivasa Seva**
