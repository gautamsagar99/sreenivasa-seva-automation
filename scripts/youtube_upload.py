#!/usr/bin/env python3
"""
YouTube Upload Automation Script

Uploads generated videos to YouTube with scheduling and hook rotation.
"""

import sys
import json
import os
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Google API imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
except ImportError as e:
    print(f"[ERROR] Missing Google API dependencies: {e}", file=sys.stderr)
    print("[INFO] Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

# Constants
BASE_DIR = Path(__file__).parent.parent.resolve()
CONFIG_PATH = BASE_DIR / "config.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_PATH = BASE_DIR / "token.json"


def load_config() -> Dict[str, Any]:
    """Load and parse config.json."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        print("[CONFIG] Loaded config.json")
        return config
    except Exception as e:
        print(f"[ERROR] Failed to load config: {e}", file=sys.stderr)
        sys.exit(1)


def save_config(config: Dict[str, Any]) -> None:
    """Save config back to file atomically."""
    try:
        temp_path = CONFIG_PATH.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        temp_path.replace(CONFIG_PATH)
        print("[CONFIG] Saved updated config")
    except Exception as e:
        print(f"[ERROR] Failed to save config: {e}", file=sys.stderr)
        raise


def is_youtube_enabled(config: Dict[str, Any]) -> bool:
    """Check if YouTube upload is enabled."""
    return config.get("youtube", {}).get("enabled", False)


def check_schedule(config: Dict[str, Any]) -> bool:
    """
    Check if upload should proceed based on schedule.
    Returns True if:
      - No schedule set (upload immediately)
      - Current time >= scheduled time
    """
    youtube_config = config.get("youtube", {})
    schedule_str = youtube_config.get("upload_schedule")

    if not schedule_str:
        print("[SCHEDULE] No schedule set, will upload immediately")
        return True

    try:
        schedule_time = datetime.strptime(schedule_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()

        if now < schedule_time:
            print(f"[WAIT] Scheduled for {schedule_str}, current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            return False
        else:
            print(f"[SCHEDULE] Time reached, proceeding with upload")
            return True
    except ValueError as e:
        print(f"[ERROR] Invalid schedule format: {e}", file=sys.stderr)
        print("[INFO] Use format: YYYY-MM-DD HH:MM:SS", file=sys.stderr)
        sys.exit(1)


def get_video_path(config: Dict[str, Any]) -> Path:
    """Get absolute path to video file."""
    output_file = config.get("output_file", "output/final_reel_with_audio.mp4")
    video_path = BASE_DIR / output_file

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found at: {video_path}")

    print(f"[VIDEO] Found: {video_path} ({video_path.stat().st_size // (1024*1024)} MB)")
    return video_path


def authenticate_youtube(credentials_file: str) -> Any:
    """
    Authenticate with YouTube API using OAuth2.
    Returns YouTube service object.
    """
    creds = None
    credentials_path = BASE_DIR / credentials_file

    if not credentials_path.exists():
        print(f"[ERROR] Credentials file not found: {credentials_path}", file=sys.stderr)
        print("[INFO] Create OAuth2 credentials in Google Cloud Console", file=sys.stderr)
        print("[INFO] Download as 'credentials.json' and place in project root", file=sys.stderr)
        sys.exit(1)

    # Load existing token if available
    if TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
            print("[AUTH] Loaded existing token")
        except Exception as e:
            print(f"[WARN] Failed to load token: {e}, will re-authenticate")

    # Refresh or obtain new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("[AUTH] Refreshing token...")
            creds.refresh(Request())
        else:
            print("[AUTH] Starting OAuth2 flow...")
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for future use
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())
        print(f"[AUTH] Token saved to {TOKEN_PATH}")

    # Build YouTube service
    youtube = build("youtube", "v3", credentials=creds)
    print("[AUTH] Authenticated successfully")
    return youtube


def get_channel_info(youtube: Any) -> Optional[Dict[str, str]]:
    """
    Get information about the authenticated user's channel.
    Returns dict with title, id, subscribers or None if not found.
    """
    try:
        request = youtube.channels().list(
            part="snippet,statistics",
            mine=True
        )
        response = request.execute()

        if response.get('items'):
            channel = response['items'][0]
            return {
                'title': channel['snippet'].get('title', 'Unknown'),
                'id': channel['id'],
                'subscribers': channel['statistics'].get('subscriberCount', '0')
            }
    except HttpError as e:
        print(f"[WARN] Could not fetch channel info: {e}", file=sys.stderr)
    return None


def get_next_hook(config: Dict[str, Any]) -> str:
    """
    Get next hook from rotation and advance index.
    Returns hook string or None if no hooks available.
    """
    youtube_config = config.get("youtube", {})
    hooks_rotation = youtube_config.get("hooks_rotation", {})
    hooks = hooks_rotation.get("hooks", [])

    if not hooks:
        return None

    current_index = hooks_rotation.get("current_index", 0)
    hook = hooks[current_index % len(hooks)]

    # Advance index for next upload
    hooks_rotation["current_index"] = (current_index + 1) % len(hooks)
    config["youtube"]["hooks_rotation"] = hooks_rotation

    print(f"[HOOK] Using hook #{current_index + 1}/{len(hooks)}: {hook[:50]}...")
    return hook


def build_metadata(config: Dict[str, Any], hook: str) -> Dict[str, Any]:
    """
    Build YouTube video metadata (title, description, tags).
    """
    youtube_config = config.get("youtube", {})
    title_prefix = youtube_config.get("title_prefix", "")
    description_template = youtube_config.get("description_template", "{hook}")
    tags = youtube_config.get("tags", [])

    # Determine god from config for personalization
    subject = "this divine content"
    if "download" in config and config["download"].get("gods"):
        subject = config["download"]["gods"][0]
    elif "ai_generation" in config and config["ai_generation"].get("prompts"):
        # Try to extract god from first prompt
        first_prompt = config["ai_generation"]["prompts"][0] if config["ai_generation"]["prompts"] else ""
        if "shiva" in first_prompt.lower():
            subject = "Lord Shiva"
        elif "vishnu" in first_prompt.lower():
            subject = "Lord Vishnu"
        # Add more gods as needed

    # Build title
    title = f"{title_prefix}{hook}" if title_prefix else hook

    # Build description
    description = description_template.format(hook=hook, god=subject)

    print(f"[METADATA] Title: {title}")
    print(f"[METADATA] Description: {description[:80]}...")
    print(f"[METADATA] Tags: {', '.join(tags[:5])}" + (f" +{len(tags)-5} more" if len(tags) > 5 else ""))

    return {
        "title": title,
        "description": description,
        "tags": tags,
        "categoryId": youtube_config.get("category", "22"),
        "privacyStatus": youtube_config.get("privacy_status", "private")
    }


def upload_video(youtube: Any, video_path: Path, metadata: Dict[str, Any]) -> str:
    """
    Upload video to YouTube with resumable upload.
    Returns video ID.
    """
    print("[UPLOAD] Starting upload...")

    body = {
        "snippet": {
            "title": metadata["title"],
            "description": metadata["description"],
            "tags": metadata["tags"],
            "categoryId": metadata["categoryId"]
        },
        "status": {
            "privacyStatus": metadata["privacyStatus"]
        }
    }

    # Add playlist if specified
    if "playlist_id" in metadata and metadata["playlist_id"]:
        # Note: Adding to playlist requires separate API call after upload
        print(f"[INFO] Will add to playlist after upload (not implemented in v1)")

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=-1  # Default chunk size
    )

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media
    )

    response = None
    last_progress = 0

    try:
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                if progress % 10 == 0 and progress != last_progress:
                    print(f"[UPLOAD] Progress: {progress}%")
                    last_progress = progress

        video_id = response["id"]
        video_url = f"https://youtu.be/{video_id}"
        print(f"[UPLOAD] Complete! Video ID: {video_id}")
        print(f"[UPLOAD] URL: {video_url}")
        return video_id

    except HttpError as e:
        if e.resp.status in [403, 404, 400]:
            print(f"[ERROR] YouTube API error: {e}", file=sys.stderr)
        raise
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Upload cancelled by user")
        sys.exit(130)


def add_to_playlist(youtube: Any, video_id: str, playlist_id: str) -> None:
    """Optional: Add uploaded video to a playlist."""
    try:
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }
        ).execute()
        print(f"[PLAYLIST] Added video to playlist {playlist_id}")
    except HttpError as e:
        print(f"[WARN] Failed to add to playlist: {e}")


def record_upload_history(config: Dict[str, Any], video_id: str, title: str, video_path: Path) -> None:
    """Add upload record to history."""
    youtube_config = config.get("youtube", {})
    history = youtube_config.get("upload_history", [])

    record = {
        "video_id": video_id,
        "title": title,
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file": str(video_path.relative_to(BASE_DIR))
    }

    history.append(record)
    youtube_config["upload_history"] = history
    config["youtube"] = youtube_config

    print(f"[HISTORY] Recorded upload #{len(history)}")


def clear_schedule_after_upload(config: Dict[str, Any]) -> None:
    """Optionally clear schedule after successful upload."""
    youtube_config = config.get("youtube", {})
    if youtube_config.get("upload_schedule"):
        youtube_config["upload_schedule"] = None
        print("[SCHEDULE] Cleared upload schedule (set to null)")
        config["youtube"] = youtube_config


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Upload videos to YouTube")
    parser.add_argument("--dry-run", action="store_true", help="Preview upload without actually uploading")
    parser.add_argument("--show-channel", action="store_true", help="Just show channel info and exit")
    args = parser.parse_args()

    try:
        print("\n" + "="*60)
        print("[YOUTUBE UPLOAD] Starting upload process")
        print("="*60)

        # Load config
        config = load_config()

        # Check if enabled
        if not is_youtube_enabled(config):
            print("[SKIP] YouTube upload is disabled in config (youtube.enabled = false)")
            sys.exit(0)

        # Check schedule
        if not check_schedule(config):
            print("[SKIP] Not scheduled yet")
            sys.exit(0)

        # Get video file (validate exists)
        video_path = get_video_path(config)

        # Authenticate
        youtube_config = config["youtube"]
        credentials_file = youtube_config.get("credentials_file", "credentials.json")
        youtube = authenticate_youtube(credentials_file)

        # Show channel info
        channel_info = get_channel_info(youtube)
        if channel_info:
            print(f"\n[CHANNEL] Authenticated as: {channel_info['title']}")
            print(f"[CHANNEL] Channel ID: {channel_info['id']}")
            print(f"[CHANNEL] Subscribers: {channel_info['subscribers']}")
        else:
            print("[WARN] Could not retrieve channel information", file=sys.stderr)

        if args.show_channel:
            print("\n[INFO] Dry run complete (channel check only)")
            sys.exit(0)

        # Get next hook
        hook = get_next_hook(config)
        if not hook:
            print("[WARN] No hooks available in rotation. Using fallback title.", file=sys.stderr)
            hook = "Devotional Video - Lord Shiva Meditation"

        # Build metadata
        metadata = build_metadata(config, hook)

        # Show upload summary
        print("\n" + "="*60)
        print("[DRY RUN] Upload Summary" if args.dry_run else "[UPLOAD] Preparing to upload")
        print("="*60)
        print(f"Title: {metadata['title']}")
        print(f"Description: {metadata['description'][:100]}...")
        print(f"Tags: {', '.join(metadata['tags'][:5])}" + (f" +{len(metadata['tags'])-5} more" if len(metadata['tags']) > 5 else ""))
        print(f"Privacy: {metadata['privacyStatus']}")
        print(f"Category: {metadata['categoryId']}")
        print(f"Video: {video_path}")
        print(f"Size: {video_path.stat().st_size // (1024*1024)} MB")
        print("="*60)

        if args.dry_run:
            print("\n[DRY RUN] Skipping actual upload (--dry-run flag)")
            sys.exit(0)

        # Confirm before upload (optional)
        confirm = input("\nProceed with upload? (y/N): ").strip().lower()
        if confirm != 'y':
            print("[SKIP] Upload cancelled by user")
            sys.exit(0)

        # Upload video
        video_id = upload_video(youtube, video_path, metadata)

        # Record history
        record_upload_history(config, video_id, metadata["title"], video_path)

        # Clear schedule if desired (optional)
        # clear_schedule_after_upload(config)  # Uncomment to auto-clear

        # Save config updates
        save_config(config)

        print("\n" + "="*60)
        print("[SUCCESS] Upload completed successfully!")
        print(f"[URL] https://youtu.be/{video_id}")
        print("="*60 + "\n")

        sys.exit(0)

    except KeyboardInterrupt:
        print("\n[INTERRUPT] Process cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n[FATAL] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
