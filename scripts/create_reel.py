import os
import random
from moviepy import ImageClip, concatenate_videoclips, AudioFileClip, TextClip, CompositeVideoClip

# Paths
IMAGE_FOLDER = "../images"
AUDIO_FILE = "../audio/song.mp3"
OUTPUT_FILE = "../output/final_reel.mp4"

hooks = [
    "Close your eyes and pray 🙏",
    "Govinda is with you ✨",
    "Your blessings are coming"
]

def create_video():
    images = sorted([img for img in os.listdir(IMAGE_FOLDER) if img.endswith(".png")])

    clips = []

    for img in images:
        path = os.path.join(IMAGE_FOLDER, img)

        clip = ImageClip(path, duration=3)

        # Resize properly (no distortion)
        clip = clip.resized(height=1920)
        clip = clip.cropped(x_center=clip.w / 2, width=1080)

        clips.append(clip)

    video = concatenate_videoclips(clips)

    return video

def add_audio(video):
    audio = AudioFileClip(AUDIO_FILE).subclipped(0, video.duration)
    return video.with_audio(audio)

def add_text(video):
    text = random.choice(hooks)

    txt_clip = TextClip(text=text, font_size=60, color='white')
    txt_clip = txt_clip.with_position(('center', 100)).with_duration(video.duration)

    return CompositeVideoClip([video, txt_clip])

def main():
    video = create_video()
    video = add_audio(video)
    video = add_text(video)

    video.write_videofile(OUTPUT_FILE, fps=24)

if __name__ == "__main__":
    main()