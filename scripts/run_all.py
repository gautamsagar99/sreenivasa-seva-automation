#!/usr/bin/env python3
"""
Master Orchestrator - Run the complete pipeline with one command

Automatically detects workflow based on config.json:
- If download.enabled = true → download_images → create_reel
- If ai_generation.enabled = true → generate_prompts → generate_ai_images → create_reel

Usage:
  python scripts/run_all.py

Configuration:
  Edit config.json to set:
  - download.enabled: true/false (use downloaded images)
  - ai_generation.enabled: true/false (use AI-generated images)
  - prompt_generation.count (for AI workflow)
"""

import sys
import time
import json
import subprocess
from pathlib import Path

def print_header(text):
    print("\n" + "="*60)
    print(text)
    print("="*60)

def print_success(text):
    print(f"✓ {text}")

def print_warn(text):
    print(f"⚠ {text}")

def print_error(text):
    print(f"✗ {text}")

def run_step(script_name: str, description: str, args: list = None) -> bool:
    """Run a script and return success status"""
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"{'='*60}")

    script_path = Path(__file__).parent / script_name

    if not script_path.exists():
        print_error(f"Script not found: {script_path}")
        return False

    # Build command
    cmd = [sys.executable, str(script_path)] + (args or [])

    print(f"Running: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(cmd, check=False)

        if result.returncode == 0:
            print_success(f"Completed: {description}")
            return True
        else:
            print_error(f"Failed: {description} (exit code {result.returncode})")
            return False

    except Exception as e:
        print_error(f"Error running {script_name}: {e}")
        return False

def check_prerequisites(config):
    """Check if required tools are installed"""
    print_header("CHECKING PREREQUISITES")

    issues = []
    workflow = config.get("workflow", "ai")

    # Check Ollama (only for AI workflow)
    if workflow == "ai":
        try:
            import ollama
            models = [m['model'] for m in ollama.list()['models']]
            if 'mistral:7b-instruct' not in models:
                issues.append("Ollama model 'mistral:7b-instruct' not found. Run: ollama pull mistral:7b-instruct")
            else:
                print_success("Ollama is running and model is available")
        except ImportError:
            issues.append("Ollama package not installed. Run: pip install ollama")
        except Exception:
            issues.append("Ollama is not running. Start it with: ollama serve")

        # Check Hugging Face token
        from dotenv import load_dotenv
        load_dotenv()
        import os
        hf_token = os.getenv("HF_TOKEN", "").strip()
        if not hf_token:
            issues.append("HF_TOKEN not set in .env file. Create .env with: HF_TOKEN=hf_your_token")
        else:
            print_success("Hugging Face token found")

    # Check config.json exists
    config_path = Path(__file__).parent.parent / "config.json"
    if not config_path.exists():
        issues.append(f"config.json not found at {config_path}")
    else:
        print_success("config.json exists")

    # Check folders
    base_dir = Path(__file__).parent.parent
    folders = ["images", "audio", "output"]
    for folder in folders:
        (base_dir / folder).mkdir(exist_ok=True)
        print_success(f"Folder ready: {folder}/")

    if issues:
        print("\n" + "="*60)
        print("PREREQUISITE ISSUES:")
        print("="*60)
        for issue in issues:
            print(f"  • {issue}")
        print("\nPlease resolve these issues before continuing.")
        return False

    print_success("\nAll prerequisites met!")
    return True

def load_config():
    """Load and determine workflow"""
    config_path = Path(__file__).parent.parent / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Determine workflow
    download_enabled = config.get("download", {}).get("enabled", False)
    ai_enabled = config.get("ai_generation", {}).get("enabled", True)

    if download_enabled and ai_enabled:
        print_warn("Both download.enabled and ai_generation.enabled are true!")
        print("Choose workflow:")
        print("  1. Download images from web")
        print("  2. Generate AI images")
        choice = input("Enter 1 or 2 [default: 2]: ").strip()
        workflow = "download" if choice == "1" else "ai"
    elif download_enabled:
        workflow = "download"
    else:
        workflow = "ai"

    config["_workflow"] = workflow
    return config

def main():
    print_header("FULL PIPELINE ORCHESTRATOR")

    # Load config and determine workflow
    try:
        config = load_config()
        workflow = config["_workflow"]

        if workflow == "download":
            print("\nSelected workflow: DOWNLOAD IMAGES FROM WEB")
            print("Steps:")
            print("  1. Download images (from Wikimedia/API)")
            print("  2. Create video")
        else:
            print("\nSelected workflow: AI IMAGE GENERATION")
            print("Steps:")
            print("  1. Generate prompts (Ollama)")
            print("  2. Generate images (FLUX)")
            print("  3. Create video")

        prompt_count = config.get("prompt_generation", {}).get("count", 5)
        image_model = config.get("ai_generation", {}).get("default_model", "flux_schnell")
        download_gods = config.get("download", {}).get("gods", [])
        download_count = config.get("download", {}).get("images_per_god", 20)

        print(f"\nConfiguration:")
        if workflow == "ai":
            print(f"  • Prompts to generate: {prompt_count}")
            print(f"  • Image model: {image_model}")
        else:
            print(f"  • Gods to download: {', '.join(download_gods)}")
            print(f"  • Images per god: {download_count}")
            print(f"  • Source: {config.get('download', {}).get('source', 'wikimedia')}")

    except Exception as e:
        print_warn(f"Could not load config: {e}")
        return 1

    # Confirm
    print(f"\n{'='*60}")
    response = input("Proceed? (y/N): ").strip().lower()
    if response != 'y':
        print("Aborted.")
        return 0

    # Check prerequisites
    if not check_prerequisites(config):
        return 1

    total_start = time.time()
    success = True

    # Run workflow based on config
    if workflow == "download":
        # Download workflow
        print_header("WORKFLOW: DOWNLOAD + CREATE VIDEO")

        if not run_step("download_images.py", "Downloading images from web"):
            print_error("Pipeline failed at download step")
            success = False

        if success:
            if not run_step("create_reel.py", "Creating final video"):
                print_error("Pipeline failed at video creation")
                success = False

    else:
        # AI generation workflow
        print_header("WORKFLOW: AI GENERATION + CREATE VIDEO")

        if not run_step("generate_prompts.py", "Generating AI prompts"):
            print_error("Pipeline failed at prompt generation")
            success = False

        if success:
            if not run_step("generate_ai_images.py", "Generating AI images"):
                print_error("Pipeline failed at image generation")
                success = False

        if success:
            if not run_step("create_reel.py", "Creating final video"):
                print_error("Pipeline failed at video creation")
                success = False

    total_elapsed = time.time() - total_start

    if success:
        print_header("PIPELINE COMPLETE! ✅")
        print_success(f"Total time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
        print("\nOutput files:")
        print("  • Images: images/")
        print("  • Video: output/final_reel_with_audio.mp4 (or output/final_reel.mp4)")
        print("\nNext steps:")
        print("  1. Check images in images/ folder")
        print("  2. Review video in output/ folder")
        print("  3. Edit config.json to customize next run")
    else:
        print_header("PIPELINE FAILED ❌")
        print_error("One or more steps failed. Check the logs above.")

    print("="*60)
    return 0 if success else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Pipeline cancelled")
        sys.exit(130)
    except Exception as e:
        print(f"\n[FATAL] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
