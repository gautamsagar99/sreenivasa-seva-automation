#!/usr/bin/env python3
"""
YouTube Hook Generator using Ollama
Generates 30-100 engaging YouTube video hooks for upload automation.

Usage:
  python scripts/generate_hooks.py --count 50 --subject shiva
"""

import json
import sys
import time
import random
import argparse
from pathlib import Path

try:
    import ollama
except ImportError:
    print("[ERROR] ollama package not installed. Run: pip install ollama")
    sys.exit(1)


# ============================================
# Configuration & Constants
# ============================================

BASE_DIR = Path(__file__).parent.parent.resolve()
CONFIG_PATH = BASE_DIR / "config.json"

DEFAULT_MODEL = "mistral:7b-instruct"
DEFAULT_COUNT = 50
DEFAULT_SUBJECT = "shiva"

SYSTEM_PROMPT = """You are an expert YouTube content creator for a devotional channel.

Generate short, engaging YouTube video hooks that grab attention immediately.

REQUIREMENTS:
1. Each hook must be 5-8 words (concise and punchy)
2. Start with action words or intriguing questions
3. Include emotional triggers (blessings, divine, power, peace, miracles)
4. Mention {subject} or relevant spiritual terms
5. Make viewers curious and want to click
6. Avoid clickbait exaggeration - keep authentic devotional tone
7. Output ONLY the hook text, one per line, no numbering

EXAMPLES of good hooks:
- Divine blessings await you today
- Experience Shiva's cosmic energy
- Unlock ancient mantras now
- Feel the divine presence
- Transform your life with OM
- Shiva's third eye opens for you
- Receive blessings from Mahadeva
- 5 minutes that will change everything
- This meditation will blow your mind
- Ancient secrets revealed today

Generate hooks that are spiritual yet modern, authentic yet catchy."""


# ============================================
# Functions
# ============================================

def load_config() -> dict:
    """Load config.json."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load config: {e}", file=sys.stderr)
        sys.exit(1)


def save_config(config: dict) -> None:
    """Save config atomically."""
    try:
        temp_path = CONFIG_PATH.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        temp_path.replace(CONFIG_PATH)
        print("[CONFIG] Saved")
    except Exception as e:
        print(f"[ERROR] Failed to save config: {e}", file=sys.stderr)
        raise


def check_ollama() -> bool:
    """Check if Ollama is running."""
    try:
        ollama.list()
        return True
    except Exception as e:
        print(f"[ERROR] Ollama not accessible: {e}", file=sys.stderr)
        print("[INFO] Start with: ollama serve", file=sys.stderr)
        return False


def ensure_model(model: str) -> bool:
    """Ensure the model is pulled in Ollama."""
    models = [m['model'] for m in ollama.list()['models']]
    if model not in models:
        print(f"[ERROR] Model '{model}' not found!", file=sys.stderr)
        print(f"[INFO] Pull it with: ollama pull {model}", file=sys.stderr)
        print(f"[INFO] Available: {', '.join(models)}", file=sys.stderr)
        return False
    return True


def generate_hook(subject: str, model: str) -> str:
    """Generate a single hook using Ollama."""
    prompt = SYSTEM_PROMPT.format(subject=subject.title())

    try:
        response = ollama.generate(
            model=model,
            prompt=prompt,
            options={
                "num_predict": 100,  # Short responses
                "temperature": 0.85,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
                "seed": random.randint(1, 999999)
            }
        )

        raw = response['response'].strip()

        # Extract lines (remove numbering, bullets)
        lines = []
        for line in raw.split('\n'):
            line = line.strip()
            # Remove numbering like "1.", "2)", etc.
            line = line.lstrip('0123456789).- ')
            if line and len(line.split()) >= 3:  # Minimum 3 words
                lines.append(line)

        if lines:
            return random.choice(lines)  # Pick random if multiple returned
        else:
            # Fallback
            return random.choice([
                f"Divine {subject.title()} blessings for you",
                f"Experience {subject.title()}'s power",
                f"{subject.title()} awaits your devotion",
                "Spiritual awakening begins now",
                "Blessings are coming your way"
            ])

    except Exception as e:
        print(f"[WARN] Generation error: {e}, using fallback")
        return f"{subject.title()} divine blessings await"


def generate_hooks(count: int, subject: str, model: str) -> list:
    """Generate N unique hooks."""
    hooks = []
    generated_set = set()
    max_attempts = 3

    print(f"\n Generating {count} YouTube hooks for '{subject}'")
    print(f" Model: {model}")
    print("="*60)

    for i in range(count):
        subject_mod = random.choice([subject, "the divine", "Mahadeva", "the Supreme", "spiritual力量"])
        # Actually use subject for most
        if random.random() > 0.3:
            subject_mod = subject

        for attempt in range(max_attempts):
            print(f"[{i+1:3d}/{count}] Generating... ", end="", flush=True)
            hook = generate_hook(subject_mod, model)
            hook = hook.strip('"').strip("'")

            # Check uniqueness (fuzzy: first 50 chars)
            hook_key = hook[:50].lower()
            if hook_key not in generated_set:
                generated_set.add(hook_key)
                hooks.append(hook)
                print(f"[OK] {hook}")
                break
            else:
                print(f"[RETRY] Duplicate, retrying... ", end="")
                if attempt >= max_attempts - 1:
                    hooks.append(hook)
                    print(f"[OK] {hook} (duplicate kept)")
                time.sleep(0.2)

        time.sleep(0.3)  # Rate limiting

    return hooks


def update_config_hooks(hooks: list, config: dict) -> None:
    """Update config.json with new hooks rotation."""
    youtube_config = config.get("youtube", {})

    youtube_config["hooks_rotation"] = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_hooks": len(hooks),
        "current_index": youtube_config.get("hooks_rotation", {}).get("current_index", 0),
        "hooks": hooks
    }

    config["youtube"] = youtube_config
    save_config(config)
    print(f"\n[CONFIG] Updated youtube.hooks_rotation with {len(hooks)} hooks")
    print(f"[CONFIG] current_index: {youtube_config['hooks_rotation']['current_index']}")


def main():
    parser = argparse.ArgumentParser(description="Generate YouTube hooks using Ollama")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="Number of hooks to generate (30-100)")
    parser.add_argument("--subject", type=str, default=DEFAULT_SUBJECT, help="Subject for hooks (e.g., shiva, vishnu)")
    parser.add_argument("--model", type=str, default=None, help="Ollama model (default from config or mistral:7b-instruct)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing hooks without prompting")
    args = parser.parse_args()

    # Validate count
    if args.count < 30:
        print("[ERROR] Minimum count is 30", file=sys.stderr)
        sys.exit(1)
    if args.count > 100:
        print("[WARN] More than 100 hooks may be excessive", file=sys.stderr)

    # Load config
    config = load_config()

    # Determine model: CLI arg > config > default
    model = args.model
    if not model:
        model = config.get("prompt_generation", {}).get("used_model", DEFAULT_MODEL)

    # Check Ollama
    if not check_ollama():
        sys.exit(1)
    if not ensure_model(model):
        sys.exit(1)

    # Check existing hooks
    existing_hooks = config.get("youtube", {}).get("hooks_rotation", {}).get("hooks", [])
    if existing_hooks and not args.overwrite:
        print(f"\n[WARN] Found {len(existing_hooks)} existing hooks in config.")
        resp = input("Overwrite with new hooks? (y/N): ").strip().lower()
        if resp != 'y':
            print("Aborted.")
            sys.exit(0)

    # Generate
    hooks = generate_hooks(args.count, args.subject, model)

    # Deduplicate just in case
    unique_hooks = []
    seen = set()
    for h in hooks:
        key = h[:50].lower()
        if key not in seen:
            seen.add(key)
            unique_hooks.append(h)

    if len(unique_hooks) < args.count:
        print(f"[INFO] Reduced to {len(unique_hooks)} unique hooks from {args.count}")

    # Show samples
    print("\n" + "="*60)
    print(" Sample Hooks:")
    print("="*60)
    for i, h in enumerate(unique_hooks[:10], 1):
        print(f" {i:2d}. {h}")
    if len(unique_hooks) > 10:
        print(f" ... and {len(unique_hooks)-10} more")

    # Update config
    update_config_hooks(unique_hooks, config)

    print("\n" + "="*60)
    print(f"[OK] Successfully generated {len(unique_hooks)} YouTube hooks")
    print(f"[NEXT] python scripts/youtube_upload.py to upload videos")
    print("="*60 + "\n")

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Hook generation cancelled")
        sys.exit(130)
    except Exception as e:
        print(f"\n[FATAL] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
