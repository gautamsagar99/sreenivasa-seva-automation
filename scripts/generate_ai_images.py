#!/usr/bin/env python3
"""
Simple AI Image Generator
Generate N images from prompts in config.json
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

try:
    from huggingface_hub import InferenceClient
    from PIL import Image
except ImportError as e:
    print(f"[ERROR] Missing dependency: {e}")
    print("Install with: pip install huggingface-hub pillow python-dotenv")
    sys.exit(1)

# ============================================
# Configuration
# ============================================

load_dotenv()

def load_config():
    """Load configuration from config.json"""
    config_path = Path(__file__).parent.parent / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"config.json not found at {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Set defaults for AI generation
    config.setdefault("ai_generation", {
        "enabled": True,
        "models": {
            "flux_schnell": "black-forest-labs/FLUX.1-schnell",
            "flux_dev": "black-forest-labs/FLUX.1-dev",
            "sd35": "stabilityai/stable-diffusion-3.5-large"
        },
        "default_model": "flux_schnell",
        "image_size": [1024, 1024],
        "num_inference_steps": 20,
        "guidance_scale": 3.5,
        "prompts": []
    })

    return config

try:
    CONFIG = load_config()
except Exception as e:
    print(f"[CONFIG ERROR] {e}", file=sys.stderr)
    sys.exit(1)

AI_CONFIG = CONFIG["ai_generation"]
IMAGES_FOLDER = Path(__file__).parent.parent / CONFIG.get("images_folder", "images")

HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
MODELS = AI_CONFIG["models"]
DEFAULT_MODEL_KEY = AI_CONFIG["default_model"]
IMAGE_SIZE = tuple(AI_CONFIG.get("image_size", [1024, 1024]))
NUM_STEPS = AI_CONFIG.get("num_inference_steps", 20)
GUIDANCE_SCALE = AI_CONFIG.get("guidance_scale", 3.5)
PROMPTS = AI_CONFIG.get("prompts", [])

# ============================================
# Utility Functions
# ============================================

def ensure_folder(path: Path) -> None:
    """Create folder if it doesn't exist"""
    path.mkdir(parents=True, exist_ok=True)

def sanitize_filename(text: str, max_len: int = 80) -> str:
    """Convert text to safe filename"""
    import re
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    return text.strip('_')[:max_len]

# ============================================
# AI Image Generation
# ============================================

def generate_image(prompt: str, model_key: str = None) -> Optional[Path]:
    """Generate a single image using Hugging Face Inference API"""

    if not HF_TOKEN:
        raise ValueError("HF_TOKEN not found. Set it in .env file or environment variable")

    if model_key is None:
        model_key = DEFAULT_MODEL_KEY

    if model_key not in MODELS:
        raise ValueError(f"Unknown model '{model_key}'. Available: {list(MODELS.keys())}")

    model_id = MODELS[model_key]

    try:
        client = InferenceClient(api_key=HF_TOKEN)

        print(f"  Generating: {prompt[:60]}{'...' if len(prompt) > 60 else ''}")

        start_time = time.time()

        image = client.text_to_image(
            prompt=prompt,
            model=model_id,
            num_inference_steps=NUM_STEPS,
            guidance_scale=GUIDANCE_SCALE,
            width=IMAGE_SIZE[0],
            height=IMAGE_SIZE[1]
        )

        elapsed = time.time() - start_time

        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        prompt_prefix = sanitize_filename(prompt[:30])
        filename = f"ai_{prompt_prefix}_{timestamp}.png"
        save_path = IMAGES_FOLDER / filename

        ensure_folder(save_path.parent)

        # Ensure RGB mode before saving
        if image.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'RGBA':
                background.paste(image, mask=image.split()[-1])
            else:
                background.paste(image)
            image = background

        image.save(save_path, "PNG", optimize=True)
        print(f"  ✓ Saved: {save_path.name} ({elapsed:.1f}s)")

        return save_path

    except Exception as e:
        print(f"  ✗ Failed: {str(e)[:100]}")
        return None

# ============================================
# Main
# ============================================

def main():
    start_time = time.time()

    print("\n" + "="*60)
    print("AI Image Generator")
    print("="*60)

    # Check HF token
    if not HF_TOKEN:
        print("[ERROR] HF_TOKEN not set!")
        print("Please create a .env file with:")
        print("  HF_TOKEN=hf_your_token_here")
        print("\nGet your token from: https://huggingface.co/settings/tokens")
        return 1

    # Check prompts
    if not PROMPTS:
        print("[ERROR] No prompts found in config.json!")
        print("Add prompts under 'ai_generation' -> 'prompts' as a list.")
        return 1

    print(f"[INFO] Using model: {DEFAULT_MODEL_KEY}")
    print(f"[INFO] Images will be saved to: {IMAGES_FOLDER}")
    print(f"[INFO] Total prompts available: {len(PROMPTS)}")
    print("="*60)

    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description="Generate AI images from prompts")
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=len(PROMPTS),
        help="Number of images to generate (default: all prompts)"
    )
    parser.add_argument(
        "--model", "-m",
        default=DEFAULT_MODEL_KEY,
        choices=list(MODELS.keys()),
        help=f"Model to use (default: {DEFAULT_MODEL_KEY})"
    )
    parser.add_argument(
        "--start-index", "-s",
        type=int,
        default=0,
        help="Start index in prompts list (default: 0)"
    )

    args = parser.parse_args()

    # Determine which prompts to use
    if args.count > len(PROMPTS) - args.start_index:
        count = len(PROMPTS) - args.start_index
        print(f"[WARN] Not enough prompts. Only {count} images can be generated.")
    else:
        count = args.count

    if count <= 0:
        print("[ERROR] No prompts to generate from.")
        return 1

    ensure_folder(IMAGES_FOLDER)

    total_generated = 0
    total_failed = 0

    # Generate images
    for i in range(count):
        prompt_idx = (args.start_index + i) % len(PROMPTS)
        prompt = PROMPTS[prompt_idx]

        print(f"\n[{i+1}/{count}] Generating image...")
        result = generate_image(prompt, args.model)

        if result:
            total_generated += 1
        else:
            total_failed += 1

        # Rate limiting: pause between requests
        if i < count - 1:
            time.sleep(1)

    elapsed = time.time() - start_time

    print(f"\n{'='*60}")
    print("AI GENERATION COMPLETE!")
    print(f"  Total generated: {total_generated}")
    print(f"  Total failed: {total_failed}")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Images saved to: {IMAGES_FOLDER}")
    print("="*60)

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Generation cancelled")
        sys.exit(130)
    except Exception as e:
        print(f"\n[FATAL] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
