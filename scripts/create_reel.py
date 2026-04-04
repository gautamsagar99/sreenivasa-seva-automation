import os
import random
from moviepy import ImageClip, concatenate_videoclips, AudioFileClip, TextClip, CompositeVideoClip, vfx
import cv2
import numpy as np
from PIL import Image

IMAGE_FOLDER = "../images"
AUDIO_FILE = "../audio/song.mp3"
OUTPUT_FILE = "../output/final_reel.mp4"

hooks = [
    "Close your eyes and pray",
    "Govinda is with you",
    "Your blessings are coming"
]

IMAGE_DURATION = 3
TEXT_DURATION = 2

def create_animated_video():
    if not os.path.exists(IMAGE_FOLDER):
        raise FileNotFoundError(f"Image folder not found: {IMAGE_FOLDER}")

    images = sorted([img for img in os.listdir(IMAGE_FOLDER) if img.lower().endswith((".png", ".jpg", ".jpeg"))])
    if not images:
        raise FileNotFoundError(f"No PNG images found in {IMAGE_FOLDER}")

    clips = []

    for idx, img in enumerate(images):
        path = os.path.join(IMAGE_FOLDER, img)

        # Load and crop image to 1080x1920 aspect ratio
        pil_img = Image.open(path)
        w, h = pil_img.size
        target_ratio = 1080 / 1920
        current_ratio = w / h

        if current_ratio > target_ratio:
            # Image is too wide, crop horizontally
            new_w = int(h * target_ratio)
            left = (w - new_w) // 2
            pil_img = pil_img.crop((left, 0, left + new_w, h))
        else:
            # Image is too tall, crop vertically
            new_h = int(w / target_ratio)
            top = (h - new_h) // 2
            pil_img = pil_img.crop((0, top, w, top + new_h))

        # Resize to final dimensions
        pil_img = pil_img.resize((1080, 1920), Image.Resampling.LANCZOS)
        pil_img.save(path)

        clip = ImageClip(path, duration=IMAGE_DURATION)

        # Add zoom effect (scale from 1.0 to 1.1 over duration)
        def zoom_effect(get_frame, t):
            frame = get_frame(t)
            scale = 1.0 + 0.1 * (t / IMAGE_DURATION)
            h, w = frame.shape[:2]
            center_y, center_x = h // 2, w // 2
            new_h, new_w = int(h * scale), int(w * scale)
            y1 = max(0, center_y - new_h // 2)
            x1 = max(0, center_x - new_w // 2)
            y2 = min(h, y1 + new_h)
            x2 = min(w, x1 + new_w)
            return frame[y1:y2, x1:x2]

        # Apply zoom effect using vfx
        clip = clip.with_effects([vfx.Resize(lambda t: 1 + 0.05 * (t / IMAGE_DURATION))])

        if idx == 0:
            text = random.choice(hooks)

            txt_clip = TextClip(
                text=text,
                font="C:/Windows/Fonts/arial.ttf",
                font_size=60,
                color="white"
            ).with_position(("center", 100)).with_duration(TEXT_DURATION)

            clip = CompositeVideoClip([clip, txt_clip]).with_duration(IMAGE_DURATION)
        else:
            clip = clip.with_duration(IMAGE_DURATION)

        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")
    return video

def add_audio(video):
    if not os.path.exists(AUDIO_FILE):
        raise FileNotFoundError(f"Audio file not found: {AUDIO_FILE}")

    audio = AudioFileClip(AUDIO_FILE)
    # Trim audio to match video duration using slicing
    if audio.duration > video.duration:
        audio = audio[:video.duration]
    return video.with_audio(audio)

def main():
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

        print("Creating animated video...")
        video = create_animated_video()

        print("Adding audio...")
        video = add_audio(video)

        print(f"Writing video file: {OUTPUT_FILE}")
        video.write_videofile(OUTPUT_FILE, fps=24)

        print("Video created successfully!")
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    main()