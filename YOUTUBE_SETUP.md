# YouTube Upload Automation - Setup Guide

## Overview

This guide helps you set up automated YouTube uploads for your generated devotional videos.

**New Files:**
- `scripts/youtube_upload.py` - Main upload script
- `scripts/generate_hooks.py` - Hook generator using Ollama
- `config.json` - Extended with `youtube` section

---

## Step 1: Google Cloud Setup (One-time)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable YouTube Data API v3:
   - APIs & Services → Library → Search "YouTube Data API v3" → Enable
4. Create OAuth 2.0 credentials:
   - APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: **Desktop app**
   - Name: "YouTube Upload Script"
   - Download JSON → Save as `credentials.json` in project root
5. (Optional) Configure OAuth consent screen if prompted

---

## Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs Google API client libraries and Ollama.

---

## Step 3: Generate YouTube Hooks

Create engaging titles/descriptions using your local LLM:

```bash
python scripts/generate_hooks.py --count 50 --subject shiva
```

- Generates 50 catchy hooks (5-8 words each)
- Saves to `config.json → youtube.hooks_rotation.hooks`
- Uses Ollama model from config (default: mistral:7b-instruct)

**Note:** Ensure Ollama is running:
```bash
ollama serve  # In another terminal
ollama pull mistral:7b-instruct  # If not already pulled
```

---

## Step 4: Configure YouTube Settings

Edit `config.json` → `youtube` section:

```json
{
  "youtube": {
    "enabled": true,
    "credentials_file": "credentials.json",
    "upload_schedule": "2026-04-06 10:00:00",  // Optional, format: YYYY-MM-DD HH:MM:SS
    "metadata_source": "hooks",
    "title_prefix": "Lord Shiva - ",
    "description_template": "Enjoy this devotional video featuring Lord Shiva. {hook} Subscribe for daily spiritual content.",
    "tags": ["shiva", "meditation", "devotional", "hindu", "spiritual", "yoga"],
    "category": "22",
    "privacy_status": "private",  // or "public", "unlisted"
    "playlist_id": null,  // Optional: YouTube playlist ID
    "hooks_rotation": { /* auto-populated */ },
    "upload_history": []  /* auto-updated */
  }
}
```

---

## Step 5: First Authentication

Run the upload script once to authenticate:

```bash
python scripts/youtube_upload.py
```

- A browser window opens for OAuth consent
- After approval, `token.json` is created (auto-refresh tokens)
- Future runs won't require browser

---

## Step 6: Upload Videos

### Option A - Immediate Upload (no schedule)
Set `upload_schedule` to `null` or omit:

```json
"upload_schedule": null
```

Then run:
```bash
python scripts/youtube_upload.py
```

### Option B - Scheduled Upload
Set a future timestamp:

```json
"upload_schedule": "2026-04-06 08:30:00"
```

Then run:
```bash
python scripts/youtube_upload.py
```

- Before scheduled time: script exits with `[WAIT]` message
- After scheduled time: uploads immediately
- Re-run the script after the scheduled time to trigger upload

**Note:** For automated scheduled uploads, use system cron/Task Scheduler:

```bash
# Run every 5 minutes to check schedule
python scripts/youtube_upload.py
```

---

## Step 7: Verify Upload

After successful upload, you'll see:

```
[SUCCESS] Uploaded to YouTube: https://youtu.be/VIDEO_ID
```

Check:
- YouTube Studio → Content
- Video appears with metadata (title, description, tags)
- Config updated with `upload_history` entry

---

## How It Works

1. **Hook Rotation:** Each upload uses the next hook from rotation (sequential, not random). Index increments after each upload, stored in `config.json`.
2. **Schedule Check:** Script compares `upload_schedule` with current time. Proceeds only if time reached.
3. **Metadata Building:** Title = `title_prefix` + `hook`. Description = `description_template` with `{hook}` substituted.
4. **Resumable Upload:** Large files can resume if interrupted.
5. **Authentication:** OAuth2 tokens stored in `token.json` (keep secret!).

---

## Troubleshooting

### "credentials.json not found"
→ Download OAuth credentials from Google Cloud Console (Step 1)

### "token.json invalid or expired"
→ Delete `token.json` and re-run to re-authenticate

### "Ollama not running"
→ Start Ollama: `ollama serve` in separate terminal

### "Quota exceeded"
→ YouTube API has daily limits. Wait 24 hours or request quota increase.

### "Video not found"
→ Ensure you've run the video generation first: `python scripts/run_all.py`

---

## Advanced Usage

### Dry Run (Preview only)
Add `--dry-run` flag (needs implementation in v2, currently not available):
```bash
python scripts/youtube_upload.py --dry-run
```

### Extend Hook List
If hooks exhausted (rare), re-run `generate_hooks.py` to add more.

### Custom Subject
```bash
python scripts/generate_hooks.py --subject vishnu --count 80
```

---

## File Locations

```
project/
├── config.json               # Extended with youtube section
├── credentials.json          # OAuth credentials (DO NOT COMMIT)
├── token.json               # Auth tokens (DO NOT COMMIT)
├── requirements.txt         # Dependencies
├── scripts/
│   ├── youtube_upload.py   # Main upload script
│   ├── generate_hooks.py   # Hook generator
│   └── ...
└── output/
    └── final_reel_with_audio.mp4  # Video to upload
```

---

## Security Notes

- **Never** commit `credentials.json` or `token.json` to git
- Keep `token.json` secure - it grants API access
- `.gitignore` is updated to exclude these files
- Use `private` privacy status for testing, change to `public` when ready

---

## Support

For issues:
1. Check console output for `[ERROR]` prefixes
2. Verify Google Cloud API is enabled
3. Ensure Ollama is running for hook generation
4. Re-authenticate if token.json is corrupted
