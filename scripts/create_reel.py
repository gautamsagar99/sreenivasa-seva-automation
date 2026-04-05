#!/usr/bin/env python3
"""
Video Reel Generator - Create video reels from images with optional audio
Production-grade script with configurable transitions and effects
"""

import os
import json
import subprocess
import sys
import time
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ============================================
# Configuration & Constants
# ============================================

def load_config():
    """Load and validate configuration"""
    config_path = Path(__file__).parent.parent / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        config = json.load(f)

    # Validate required fields
    required = ["images_folder", "audio_file", "output_file", "attach_audio"]
    for field in required:
        if field not in config:
            raise ValueError(f"Missing required config field: {field}")

    # Set defaults for optional fields
    config.setdefault("total_duration", 30.0)
    config.setdefault("hooks", [])
    config.setdefault("effects", {})

    # Transition config
    config.setdefault("transition", {
        "enabled": True,
        "duration": 0.5,
        "type": "fade"
    })

    return config

# Load config early
try:
    CONFIG = load_config()
except Exception as e:
    print(f"[CONFIG ERROR] {e}", file=sys.stderr)
    sys.exit(1)

# Paths
BASE_DIR = Path(__file__).parent.parent.resolve()
IMAGE_FOLDER = BASE_DIR / CONFIG["images_folder"]
AUDIO_FILE = BASE_DIR / CONFIG["audio_file"]
OUTPUT_FILE = BASE_DIR / CONFIG["output_file"]
TEMP_DIR = BASE_DIR / "temp_reel_gen"

# Settings
ATTACH_AUDIO = CONFIG["attach_audio"]
TOTAL_DURATION = CONFIG["total_duration"]
HOOKS = CONFIG["hooks"]
EFFECTS = CONFIG["effects"]
TRANSITION = CONFIG["transition"]

# Derived settings
FPS = 24
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FONT_PATH = "C:/Windows/Fonts/arial.ttf" if sys.platform == "win32" else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# ============================================
# Utility Functions
# ============================================

def run_ffmpeg(cmd, description="FFmpeg"):
    """Run FFmpeg command with error handling"""
    ffmpeg_path = subprocess.run(["where", "ffmpeg"] if sys.platform == "win32" else ["which", "ffmpeg"],
                                 capture_output=True, text=True).stdout.strip() or "ffmpeg"

    if not ffmpeg_path:
        raise RuntimeError("FFmpeg not found. Please install FFmpeg and add it to PATH")

    cmd[0] = ffmpeg_path
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"{description} failed:\n{result.stderr}")

    return result

def seconds_to_hms(seconds):
    """Convert seconds to HH:MM:SS.ms or MM:SS.ms format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:06.2f}"
    else:
        return f"{minutes:02d}:{secs:05.2f}"

# ============================================
# Image Processing
# ============================================

def preprocess_images():
    """Load, crop, resize images and add text overlay to first image"""
    if not IMAGE_FOLDER.exists():
        raise FileNotFoundError(f"Image folder not found: {IMAGE_FOLDER}")

    image_files = sorted([
        f for f in IMAGE_FOLDER.iterdir()
        if f.is_file() and f.suffix.lower() in [".png", ".jpg", ".jpeg"]
    ])

    if not image_files:
        raise FileNotFoundError(f"No images found in {IMAGE_FOLDER}")

    print(f"[INFO] Found {len(image_files)} images")

    processed = []
    target_ratio = VIDEO_WIDTH / VIDEO_HEIGHT

    for idx, img_path in enumerate(image_files):
        img = Image.open(img_path)

        # Crop to target aspect ratio
        w, h = img.size
        current_ratio = w / h

        if current_ratio > target_ratio:
            # Too wide - crop sides
            new_w = int(h * target_ratio)
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        else:
            # Too tall - crop top/bottom
            new_h = int(w / target_ratio)
            top = (h - new_h) // 2
            img = img.crop((0, top, w, top + new_h))

        # Resize to target resolution
        img = img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS)

        # Add text overlay to first image only (if hooks available)
        if idx == 0 and HOOKS:
            import random
            text = random.choice(HOOKS)
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype(FONT_PATH, 60)
            except:
                font = ImageFont.load_default()
            text_width = draw.textlength(text, font=font)
            draw.text(
                ((VIDEO_WIDTH - text_width) // 2, 100),
                text,
                font=font,
                fill="white",
                stroke_width=2,
                stroke_fill="black"
            )

        processed.append(img)

    return processed

# ============================================
# Duration Calculation
# ============================================

def calculate_durations(num_images, use_audio=False, audio_duration=None):
    """
    Calculate per-image durations with transition overlap handling.

    Returns a list where each element is the duration (in seconds) for that image.
    Note: The durations already account for transitions - each image's segment
    includes any fade in/out times at its boundaries.
    """
    if use_audio and audio_duration is not None:
        # With audio: split total audio duration equally among images
        return [audio_duration / num_images] * num_images
    else:
        # Without audio: split total_duration equally among images
        return [TOTAL_DURATION / num_images] * num_images

# ============================================
# Video Segment Creation
# ============================================

def create_segments(images, durations):
    """Create individual video segments for each image with effects"""
    TEMP_DIR.mkdir(exist_ok=True)
    segment_files = []

    print("[INFO] Creating video segments...")

    for i, (img, duration) in enumerate(zip(images, durations)):
        img_path = TEMP_DIR / f"img_{i:04d}.jpg"
        seg_path = TEMP_DIR / f"seg_{i:04d}.mp4"

        # Save image
        img.save(img_path, "JPEG", quality=95)

        # Calculate frames
        num_frames = max(1, int(round(duration * FPS)))

        # Build filters
        filter_parts = []

        # Zoom effect if enabled
        if EFFECTS.get("zoom_enabled", False):
            zoom_scale = EFFECTS.get("zoom_scale", 0.05)
            scale_factor = 1.0 + zoom_scale
            filter_parts.append(f"scale=iw*{scale_factor}:ih*{scale_factor}:flags=lanczos")

        # Per-segment fade in/out if transitions enabled
        # Note: First segment fades in, last fades out, both fade in+out
        if TRANSITION.get("enabled", False):
            fade_duration = TRANSITION.get("duration", 0.5)
            # Only apply fade to avoid overlap issues
            if i == 0:
                # First image: fade in only
                filter_parts.append(f"fade=t=in:st=0:d={fade_duration}")
            elif i == len(images) - 1:
                # Last image: fade out only
                filter_parts.append(f"fade=t=out:st={duration-fade_duration:.2f}:d={fade_duration}")
            else:
                # Middle images: fade in and out
                filter_parts.append(f"fade=t=in:st=0:d={fade_duration},fade=t=out:st={duration-fade_duration:.2f}:d={fade_duration}")

        # Build command
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(img_path),
            "-r", str(FPS),
            "-frames:v", str(num_frames),
        ]

        if filter_parts:
            cmd.extend(["-vf", ",".join(filter_parts)])

        cmd.extend([
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-an",
            str(seg_path)
        ])

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create segment {i}: {e}")

        segment_files.append(seg_path)
        img_path.unlink()  # Remove temp image

    return segment_files

def concatenate_segments(segment_files, durations, output_path):
    """Concatenate segments with proper transition timing"""
    if len(segment_files) == 1:
        # Single segment, just copy
        shutil.copy2(segment_files[0], output_path)
        return

    # Create concat list for initial join
    list_path = TEMP_DIR / "list.txt"
    with open(list_path, "w") as f:
        for seg in segment_files:
            f.write(f"file '{seg}'\n")

    # For smooth transitions, we rely on the per-segment fade in/out
    # Simple concat works because we already applied fades to each segment
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_path),
        "-c", "copy",
        str(output_path)
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to concatenate segments: {e}")

# ============================================
# Audio Handling
# ============================================

def get_audio_duration(audio_path):
    """Get audio duration using ffmpeg"""
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    cmd = [
        "ffmpeg", "-i", str(audio_path),
        "-hide_banner", "-f", "null", "-"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    import re
    match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})", result.stderr)
    if not match:
        raise RuntimeError(f"Could not parse audio duration from FFmpeg output")

    h, m, s = map(float, match.groups())
    return h * 3600 + m * 60 + s

def add_audio_to_video(video_path, audio_path, output_path):
    """Merge audio with video"""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        str(output_path)
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to add audio: {e}")

# ============================================
# Main Workflow
# ============================================

def main():
    start_time = time.time()

    try:
        print("="*50)
        print("Video Reel Generator")
        print("="*50)

        # Create output directory
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Step 1: Preprocess images
        print("\n[1/4] Preprocessing images...")
        images = preprocess_images()
        num_images = len(images)
        print(f"   [OK] Loaded and processed {num_images} images")

        # Step 2: Calculate durations
        print("\n[2/4] Calculating durations...")
        audio_duration = None

        if ATTACH_AUDIO:
            if not AUDIO_FILE.exists():
                raise FileNotFoundError(f"Audio file not found: {AUDIO_FILE}")
            print("   Getting audio duration...")
            audio_duration = get_audio_duration(AUDIO_FILE)
            print(f"   Audio duration: {seconds_to_hms(audio_duration)}")

        durations = calculate_durations(num_images, ATTACH_AUDIO, audio_duration)

        if ATTACH_AUDIO:
            per_image = audio_duration / num_images
            print(f"   Audio duration: {seconds_to_hms(audio_duration)} -> {num_images} images * {seconds_to_hms(per_image)} each")
        else:
            per_image = TOTAL_DURATION / num_images
            print(f"   Total duration: {seconds_to_hms(TOTAL_DURATION)} -> {num_images} images * {seconds_to_hms(per_image)} each")

        # Step 3: Create video
        print("\n[3/4] Creating video...")
        segments = create_segments(images, durations)

        if ATTACH_AUDIO:
            concatenate_segments(segments, durations, TEMP_VIDEO := TEMP_DIR / "temp_video.mp4")
            print("   [OK] Video created (without audio)")

            # Step 4: Add audio
            print("\n[4/4] Adding audio...")
            add_audio_to_video(TEMP_VIDEO, AUDIO_FILE, OUTPUT_FILE)
            TEMP_VIDEO.unlink(missing_ok=True)
        else:
            concatenate_segments(segments, durations, OUTPUT_FILE)
            print("   [OK] Video created")

        # Cleanup segments
        for seg in segments:
            seg.unlink(missing_ok=True)

        total_time = time.time() - start_time

        print("\n" + "="*50)
        print("[SUCCESS] Video generation complete!")
        print(f"   Output: {OUTPUT_FILE}")
        print(f"   File size: {OUTPUT_FILE.stat().st_size / (1024*1024):.1f} MB")
        if ATTACH_AUDIO and audio_duration:
            print(f"   Duration: {seconds_to_hms(audio_duration)}")
        else:
            total_dur = sum(durations)
            print(f"   Duration: {seconds_to_hms(total_dur)}")
        print(f"   Processing time: {total_time:.1f}s")
        print("="*50)

    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup temp directory
        if TEMP_DIR.exists():
            import shutil
            try:
                shutil.rmtree(TEMP_DIR)
            except:
                pass

if __name__ == "__main__":
    main()
