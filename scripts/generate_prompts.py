#!/usr/bin/env python3
"""
AI Prompt Generator using Ollama (mistral:7b-instruct)
Generates optimized FLUX prompts and saves to config.json

Usage:
  1. In config.json, set:
     "prompt_generation": {
       "count": 10
     }
  2. Ensure ollama is running: ollama serve
  3. Ensure model is pulled: ollama pull mistral:7b-instruct
  4. Run: python scripts/generate_prompts.py
"""

import json
import sys
import time
import random
from pathlib import Path

try:
    import ollama
except ImportError:
    print("[ERROR] ollama package not installed. Run: pip install ollama")
    sys.exit(1)

from dotenv import load_dotenv

load_dotenv()

# ============================================
# Configuration
# ============================================

def load_config():
    config_path = Path(__file__).parent.parent / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"config.json not found at {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Default prompt generation config
    config.setdefault("prompt_generation", {
        "count": 10,
        "subjects": ["shiva", "vishnu", "ganesha", "krishna", "ram", "hanuman", "lakshmi", "durga", "sai"],
        "model": "mistral:7b-instruct",
        "max_new_tokens": 200,
        "temperature": 0.85
    })

    return config, config_path

try:
    CONFIG, CONFIG_PATH = load_config()
except Exception as e:
    print(f"[CONFIG ERROR] {e}", file=sys.stderr)
    sys.exit(1)

GEN_CONFIG = CONFIG["prompt_generation"]
COUNT = GEN_CONFIG.get("count", 10)
SUBJECTS = GEN_CONFIG.get("subjects", [])
MODEL = GEN_CONFIG.get("model", "mistral:7b-instruct")
MAX_TOKENS = GEN_CONFIG.get("max_new_tokens", 200)
TEMPERATURE = GEN_CONFIG.get("temperature", 0.85)

# ============================================
# System Prompt
# ============================================

SYSTEM_PROMPT_BASE = """You are an expert prompt engineer for FLUX image generation models. Generate highly detailed, optimized image prompts for Hindu deities.

Each prompt MUST follow this structure:
[Subject description with pose/action/attributes], [Artistic style], [Lighting], [Environment], [quality tags]

RULES:
1. Start with vivid description of deity (pose, action, attributes, expressions, clothing, accessories)
2. Include one specific artistic style (traditional Thanjavur, Warli, digital painting, cinematic, oil, watercolor, etc.)
3. Add dramatic lighting (golden hour, chiaroscuro, god rays, volumetric, backlit)
4. Mention environment/setting (temple, cosmic, forest, celestial, river, palace)
5. ALWAYS end with at least 3 quality boosters: highly detailed, intricate, masterpiece, best quality, 4K, 8K, ultra HD, sharp focus
6. Keep between 80-150 words
7. Do NOT include "Prompt:" or any prefixes - output ONLY the prompt text

EXAMPLES:
"Lord Shiva as Nataraja, cosmic dancer with flowing hair and glowing trident in dynamic mid-dance pose, traditional Thanjavur painting style, volumetric god rays illuminating temple sanctum, gold leaf accents, cosmic energy swirling, highly detailed, intricate, masterpiece, best quality, 8K"

"Baby Krishna stealing butter in Vrindavan hut, mischievous smile, blue skin, yellow dhoti, traditional Pattachitra style, warm golden hour light through window, clay pots, butter stains, cows outside, soft shadows, highly detailed, intricate, ultra HD, sharp focus, 4K" """

# Variations to add randomness to each request
STYLE_HINTS = [
    "Use a unique composition this time.",
    "Try a different artistic perspective.",
    "Be more creative with the environment.",
    "Focus on emotional expression.",
    "Emphasize divine aura and glow.",
    "Use dynamic composition.",
    "Try a different lighting setup.",
    "Focus on intricate details.",
    "Be more cinematic.",
    "Use vibrant colors."
]

# ============================================
# Ollama Functions
# ============================================

def generate_with_ollama(deity: str, attempt: int = 0) -> str:
    """Generate a single prompt using Ollama."""

    # Add random variation hint to make each generation unique
    hint = random.choice(STYLE_HINTS)
    full_prompt = f"{SYSTEM_PROMPT_BASE}\n\nAdditional instruction: {hint}\n\nGenerate ONE prompt for {deity.title()}:"

    try:
        start = time.time()
        response = ollama.generate(
            model=MODEL,
            prompt=full_prompt,
            options={
                "num_predict": MAX_TOKENS,
                "temperature": TEMPERATURE,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
                "seed": random.randint(1, 1000000)  # Random seed for variety
            }
        )
        elapsed = time.time() - start

        result = response['response'].strip()

        # Clean up common prefixes
        for prefix in ["Prompt:", "Here is a prompt:", "Generated:", "Image prompt:", "A prompt for", "The prompt is:"]:
            if result.lower().startswith(prefix.lower()):
                result = result[len(prefix):].strip()

        # Remove quotes
        result = result.strip('"').strip("'").strip()

        print(f"  ✓ Generated in {elapsed:.1f}s ({len(result)} chars)")
        return result if result else f"{deity.title()}, divine Hindu deity, highly detailed, masterpiece, best quality, 4K"

    except Exception as e:
        print(f"  ✗ Ollama error: {e}")
        return f"{deity.title()}, divine Hindu deity, highly detailed, masterpiece, best quality, 4K"

# ============================================
# Main
# ============================================

def main():
    if not SUBJECTS:
        print("[ERROR] No subjects specified in config.json -> prompt_generation.subjects")
        print(f"Using default subjects list with {len(GEN_CONFIG.get('subjects', []))} items")
        if not GEN_CONFIG.get('subjects'):
            print("ERROR: No subjects available. Please add subjects to config.json.")
            return 1
        subjects = GEN_CONFIG['subjects']
    else:
        subjects = SUBJECTS

    print("="*60)
    print("AI Prompt Generator (Ollama)")
    print("="*60)
    print(f"Model: {MODEL}")
    print(f"Count: {COUNT}")
    print(f"Subjects: {', '.join(subjects)}")
    print("="*60)

    # Check if ollama is running
    try:
        ollama.list()
    except Exception as e:
        print("[ERROR] Ollama is not running or not accessible!")
        print("Start it with: ollama serve")
        print(f"Error: {e}")
        return 1

    # Check if model exists
    models = [m['model'] for m in ollama.list()['models']]
    if MODEL not in models:
        print(f"[ERROR] Model '{MODEL}' not found in Ollama!")
        print(f"Pull it with: ollama pull {MODEL}")
        print(f"Available models: {', '.join(models)}")
        return 1

    # Check existing prompts
    existing_prompts = CONFIG.get("ai_generation", {}).get("prompts", [])
    if existing_prompts:
        print(f"\n[WARN] Found {len(existing_prompts)} existing prompts in config.")
        resp = input("Overwrite? (y/N): ").strip().lower()
        if resp != 'y':
            print("Aborted.")
            return 0

    # Generate
    print("\nGenerating prompts...\n")
    random.seed()

    prompts = []
    generated_set = set()
    max_attempts = 3  # Retry limit for duplicates

    for i in range(COUNT):
        subject = subjects[i % len(subjects)]

        # Try to get a unique prompt
        for attempt in range(max_attempts):
            print(f"[{i+1:3d}/{COUNT}] {subject.title():12s} (attempt {attempt+1}) ", end="", flush=True)
            prompt = generate_with_ollama(subject)

            # Check for duplicate
            if prompt not in generated_set:
                generated_set.add(prompt)
                prompts.append(prompt)
                break
            else:
                print(f"\n  ⚠ Duplicate detected, retrying... ", end="")
                if attempt < max_attempts - 1:
                    time.sleep(0.3)
                else:
                    print(f"\n  ⚠ Max attempts reached, using duplicate")
                    prompts.append(prompt)
                    break

        # Small pause between calls
        if i < COUNT - 1:
            time.sleep(0.5)

    # Save to config
    if "ai_generation" not in CONFIG:
        CONFIG["ai_generation"] = {}

    CONFIG["ai_generation"]["prompts"] = prompts
    CONFIG["prompt_generation"]["used_model"] = MODEL
    CONFIG["prompt_generation"]["generated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    # Backup old prompts
    if existing_prompts:
        CONFIG["ai_generation"]["prompts_backup"] = existing_prompts
        print(f"\n✓ Backed up {len(existing_prompts)} old prompts")

    # Write config
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(CONFIG, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[ERROR] Failed to write config: {e}")
        return 1

    print(f"\n{'='*60}")
    print(f"✓ Successfully saved {len(prompts)} prompts to config.json")
    print("="*60)

    print("\nSample prompts:")
    for i, p in enumerate(prompts[:min(3, len(prompts))], 1):
        print(f"\n{i}. {p[:200]}{'...' if len(p) > 200 else ''}")

    if len(prompts) > 3:
        print(f"\n   ... and {len(prompts)-3} more")

    print("\nNext step: python scripts/generate_ai_images.py")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Prompt generation cancelled")
        sys.exit(130)
    except Exception as e:
        print(f"\n[FATAL] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
